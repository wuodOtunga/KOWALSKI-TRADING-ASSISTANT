"""Repository regression tests. Each test pins a bug that existed before the fixes.
Run with:  pytest test_repository.py -v
Uses an in-memory SQLite database, so nothing touches kowalski.db."""

from dataclasses import replace
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import exc

import exceptions as t
from models import (Account, Amendments, Trade, TradeAsset, TradeChart,
                    TradeDirection, TradeNotes, TradeResult)
from repository import Repository


@pytest.fixture
def repo():
    r = Repository("sqlite://", echo=False)   # fresh in-memory DB per test
    yield r
    r.close_db_connection()


@pytest.fixture
def account_id(repo):
    return repo.create_trading_account(
        Account(None, "test acct", "PERSONAL LIVE", "broker", 1000, True))


def make_trade(account_id: int) -> Trade:
    return Trade(
        trade_id=None, entry_price=100.0, exit_price=110.0, take_profit=110.0,
        stop_loss=95.0, position_size=1.0, entry_time=time(9, 0), exit_time=time(10, 0),
        date=date(2026, 1, 5), model_id=1, account_id=account_id, management_id=1,
        entry_execution_id=1, asset=TradeAsset.NQ, direction=TradeDirection.LONG,
        dollar_amount=1000.0, duration=timedelta(hours=1), result=TradeResult.PROFIT,
        rr_multiple=2.0, risk_percent=0.01)


# ---- trades -------------------------------------------------------------
def test_save_and_get_roundtrip(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    got = repo.get_by_id(trade_id)
    assert got.trade_id == trade_id
    assert got.entry_time == time(9, 0)
    assert got.duration == timedelta(hours=1)


def test_save_trade_reports_every_missing_fk(repo, account_id):
    bad = replace(make_trade(account_id), model_id=99, management_id=77)
    with pytest.raises(t.InvalidIdentifierError) as err:
        repo.save_trade(bad)
    assert "model_id= 99" in str(err.value)
    assert "management_id= 77" in str(err.value)


def test_get_all_trades_empty_is_empty_list(repo):
    assert repo.get_all_trades() == []


def test_update_trade_field(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    repo.update_trade_field(trade_id, 120.0, "exit_price")
    assert repo.get_by_id(trade_id).exit_price == 120.0


def test_update_trade_field_rejects_derived_column(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    with pytest.raises(t.InvalidColumnNameError):
        repo.update_trade_field(trade_id, 5.0, "dollar_amount")


# ---- notes --------------------------------------------------------------
def test_notes_add_then_upsert_update(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    repo.add_trade_notes(TradeNotes(trade_id, "calm", "none", "wait", "ok"))
    repo.update_trading_notes(TradeNotes(trade_id, "anxious", "none", "wait", "ok"))
    assert repo.get_trade_notes(trade_id).emotions == "anxious"


def test_notes_upsert_inserts_when_absent(repo, account_id):
    # was broken: _field_values(exclude=...) used to drop the PK on the insert path
    trade_id = repo.save_trade(make_trade(account_id))
    repo.update_trading_notes(TradeNotes(trade_id, "a", "b", "c", "d"))
    assert repo.get_trade_notes(trade_id).general_notes == "d"


def test_duplicate_notes_raise_constraint_violation(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    repo.add_trade_notes(TradeNotes(trade_id, "a", "b", "c", "d"))
    with pytest.raises(t.ConstraintViolationError):
        repo.add_trade_notes(TradeNotes(trade_id, "a", "b", "c", "d"))


# ---- parameters ---------------------------------------------------------
def test_duplicate_parameter_pair_is_constraint_violation(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    repo.add_trade_parameters(trade_id, 1)
    with pytest.raises(t.ConstraintViolationError):
        repo.add_trade_parameters(trade_id, 1)


def test_trade_with_no_parameters_returns_empty_list(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    assert repo.get_trade_parameters(trade_id) == []


# ---- delete / audit trail ----------------------------------------------
def test_delete_trade_cascades_children_but_keeps_amendments(repo, account_id):
    trade_id = repo.save_trade(make_trade(account_id))
    repo.add_trade_notes(TradeNotes(trade_id, "a", "b", "c", "d"))
    repo.add_chart(TradeChart(None, trade_id, "p", "f", datetime.now()))
    repo.add_trade_parameters(trade_id, 1)
    repo.add_trade_amendments(
        Amendments(None, trade_id, "exit_price", 110.0, 120.0, datetime.now()))

    repo.delete_trade(trade_id)

    assert repo.get_all_trades() == []
    with repo.engine.connect() as c:
        left = lambda tbl: c.exec_driver_sql(f"SELECT COUNT(*) FROM {tbl}").scalar()
        assert left("trade_notes") == 0
        assert left("charts") == 0
        assert left("trade_parameters") == 0
        assert left("trade_amendments") == 1      # audit trail survives


# ---- accounts -----------------------------------------------------------
def test_delete_account_without_trades(repo, account_id):
    repo.delete_account_from_db(account_id)
    assert repo.get_trading_accounts() == []


def test_delete_account_with_trades_is_refused(repo, account_id):
    repo.save_trade(make_trade(account_id))
    with pytest.raises(t.ConstraintViolationError):
        repo.delete_account_from_db(account_id)


def test_balance_includes_trade_pnl(repo, account_id):
    repo.save_trade(make_trade(account_id))      # dollar_amount = 1000.0
    assert repo.get_current_account_balance(account_id) == 2000.0


# ---- engine ---------------------------------------------------------------
def test_sqlite_foreign_keys_are_enforced(repo):
    with pytest.raises(exc.IntegrityError):
        with repo.engine.begin() as c:
            c.exec_driver_sql(
                "INSERT INTO charts (trade_id, filepath, filename) VALUES (999, 'a', 'b')")
