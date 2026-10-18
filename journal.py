from datetime import UTC, datetime
from typing import Any, get_args

import exceptions as t
import trade_calculator as y
from models import (
    Account,
    AmendableColumns,
    Amendments,
    EntryExecution,
    JournalEntry,
    Parameter,
    Trade,
    TradeAsset,
    TradeChart,
    TradeDirection,
    TradeGrade,
    TradeManagement,
    TradeNotes,
    TradeResult,
    TradeSetup,
    TradingModel,
)
from repository import Repository
from validation import validate_trade_data

_DERIVED_FIELDS = ("dollar_amount", "result", "rr_multiple", "risk_percent", "duration")

# columns whose change alters P&L, R-multiple, risk or duration
_RECOMPUTE_DERIVED_ON = frozenset({
    "entry_price", "exit_price", "take_profit", "stop_loss",
    "position_size", "asset", "direction", "account_id",
})

# columns whose change alters the grade (only matters if already graded)
_REGRADE_ON = frozenset({"management_id", "entry_execution_id"})

_COLUMN_CASTERS = {
    "entry_price": float, "exit_price": float, "take_profit": float,
    "stop_loss": float, "position_size": float,
    "model_id": int, "account_id": int,
    "management_id": int, "entry_execution_id": int,
    "asset": TradeAsset, "direction": TradeDirection,
}

class Journal:

    def __init__(self, db: Repository):
        self.db: Repository = db

    #A) SINGLE WRITE METHOD
    def record_trade(self, trade: Trade) -> Trade:
        """RECORDS A TRADE IN THE JOURNAL"""
        #1: ASSEMBLE/DERIVE TRADE DATA CALLER DOESN'T HAVE.
        trade = self._compute_derived_fields(trade)
        #TRADE ISN'T GRADED AT THIS POINT BECAUSE TRADE PARAMETERS
        #MAY NOT HAVE BEEN SUBMITTED YET.
        #FINALIZE_GRADE() METHOD WILL HANDLE GRADING AND UPDATING OF OVERALL_TRADE_GRADE

        #2: VALIDATE THE TRADE DATA.
        valid_trade: Trade = validate_trade_data(trade)

        #3: PERSIST TO THE DATABASE & #4: TRANSLATE THE ERRORS.
        trade_id: int = self.db.save_trade(trade=valid_trade)
        trade.trade_id = trade_id

        #5: RETURN SOMETHING MEANINGFUL.
        return trade


#DOLLAR_AMOUNT, RESULT, RR_MULTIPLE, DURATION ARE DERIVED.
    def _compute_derived_fields(self, trade: Trade) -> Trade:
        """COMPUTES DERIVED FIELDS USING THE CALCULATOR MODULE."""

        setup: TradeSetup = self._convert_to_trade_setup(trade)

        results = y.calculate_profit_loss(setup)
        dollar_amount = results["DOLLAR_AMOUNT"]
        trade.dollar_amount = dollar_amount
        result = results["RESULT"]
        result = TradeResult.PROFIT if result == "PROFIT" else TradeResult.LOSS

        trade.result = result

        values = y.calculate_risk_reward_multiple(setup)
        rr_multiple = values["RR_MULTIPLE"]
        trade.rr_multiple = rr_multiple
        risk_percent = values["RISK_PERCENT"]
        trade.risk_percent = risk_percent
        duration = y.calculate_trade_duration(setup)
        trade.duration = duration

        return trade

    def _convert_to_trade_setup(self, trade: Trade) -> TradeSetup:

        balance = self.db.get_account_balance_as_of(
                        account_id=trade.account_id, as_of_date=trade.date,    # pyright: ignore[reportArgumentType]
                        as_of_time=trade.entry_time, exclude_trade_id=trade.trade_id)
        setup = TradeSetup(
            entry_price= trade.entry_price,
            exit_price= trade.exit_price,
            stop_loss= trade.stop_loss,
            take_profit= trade.take_profit,
            asset= trade.asset,
            direction= trade.direction,
            position_size= trade.position_size,
            account_balance= balance,
            entry_time= trade.entry_time,
            exit_time= trade.exit_time,
            date= trade.date
        )

        return setup

#ASSEMBLE/DERIVE DATA AND VALIDATE DATA GETS HANDLED BY STREAMLIT.
#STREAMLIT OWNS THE COLLECTION OF CHARTS DATA LOGIC.
#ATTACH CHART RECEIVES A VALID, FULLY CONSTRUCTED CHARTS DATA.
    def attach_charts(self, chart: TradeChart) -> TradeChart:

        #TRADE_ID ISN'T BEING VERIFIED ANYWHERE
        #3: PERSIST TO DATABASE AND TRANSLATE FAILURES.
        chart_id = self.db.add_chart(chart)
        chart.chart_id = chart_id

        #4: RETURN SOMETHING MEANINGFUL.
        return chart

    def evaluate_trade(self, trade: Trade) -> dict:

        #3: GET POINTS DATA FROM RELEVANT TABLES USING IDENTIFIERS.
        #4: TRANSLATE THE ERRORS.
        try:
            entry_score = self.db.get_entry_execution_points(trade.entry_execution_id)
            management_score = self.db.get_trade_management_points(trade.management_id)
            trade_parameters = self.db.get_trade_parameters(trade.trade_id) # pyright: ignore[reportArgumentType]
        except t.InvalidIdentifierError as e:
            raise t.GradingError(f"STORED IDS FOR TRADE {trade.trade_id} ARE INVALID: {e}") from e

        parameters_score = len(trade_parameters)
        #5. RETURN SOMETHING MEANINGFUL.
        return {
            "entry_score" : entry_score,
            "management_score" : management_score,
            "parameters_score" : parameters_score,
        }

    def _calculate_grade(self, trade: Trade) -> TradeGrade:
        """PURE CALCULATION. READS POINTS, WRITES NOTHING."""

        scores = self.evaluate_trade(trade)
        execution_avg = (scores["entry_score"] + scores["management_score"]) / 2
        bonus = 1 if execution_avg >= 4 else 0  # noqa: PLR2004
        trade_points = scores["parameters_score"] + bonus

        for threshold, grade in ((6, TradeGrade.A), (5, TradeGrade.B),
                                (4, TradeGrade.C), (3, TradeGrade.D)):
            if trade_points >= threshold:
                return grade
        return TradeGrade.F

    def grade_trade(self, trade: Trade) -> Trade:
        """CALCULATE + PERSIST. USED BY finalize_grade."""

        trade.overall_trade_grade = self._calculate_grade(trade)
        self.db.update_trade_grade(
            trade_id=trade.trade_id, new_grade=trade.overall_trade_grade)  # type: ignore[arg-type]
        return trade


    def add_reflection_notes(self, trade_notes: TradeNotes) -> TradeNotes:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        self.db.add_trade_notes(notes=trade_notes)

        return trade_notes

    def get_trade(self, trade_id: int) -> Trade:

        return self.db.get_by_id(trade_id)

    def fetch_all_trades(self) -> list[Trade]:
        return self.db.get_all_trades()

    def get_journal_entry(self, trade_id: int) -> JournalEntry:
        with self.db.transaction():          # one consistent read
            trade = self.db.get_by_id(trade_id)   # still raises TradeNotFoundError

            try:
                trade_notes: TradeNotes | None = self.db.get_trade_notes(trade_id)
            except t.NotesNotFoundError:
                trade_notes = None

            charts = self.db.get_trade_charts(trade_id)            # [] if none
            parameter_ids = self.db.get_trade_parameters(trade_id)  # [] if none
            parameter_names = self.db.get_parameter_names(parameter_ids)

        return JournalEntry(
            trade=trade, charts=charts,
            trade_notes=trade_notes, parameter_names=parameter_names,
        )

#RECORD_JOURNAL_ENTRY METHOD ISN'T BEING CALLED BY STREAMLIT UI
#THERE IS A BUG IN THE ADD_CHART DB CALL SINCE METHOD ASSUMES ATOMIC TRANSACTION
#CHARTS UPLOAD IS DONE IN BATCHES AND SO WE CAN HAVE 3/4 SUCCESSES
#MEANING CHART UPLOADS, COMMITS ARE DONE PER CHART.

#NOTE TO FUTURE SELF/DEVELOPER
#RECORD_JOURNAL_ENTRY METHOD WAS DELETED ON 30/8/2026.
#WITH THE GIVEN STREAMLIT CODE PATH, THERE IS NO USE FOR THE JOURNAL METHOD.
#IN THE FUTURE IF NEED ARISES, YOU CAN REWRITE IT.

    def amend_trade_entry(self, amendment: Amendments) -> Amendments:

        column: str = amendment.column_name
        if column not in get_args(AmendableColumns):
            raise t.ConflictError(f"CAN'T AMEND COLUMN: {column}")

        try:
            amendment.new_value = _COLUMN_CASTERS[column](amendment.new_value)
        except (KeyError, ValueError, TypeError) as e:
            raise t.TradeValidationError("TRADE VALIDATION FAILED") from e

        with self.db.transaction():
            trade: Trade = self.db.get_by_id(amendment.trade_id)
            amendment.old_value = getattr(trade, column)
            setattr(trade, column, amendment.new_value)

            # everything that will be written, keyed by column name
            changes: dict[str, Any] = {column: amendment.new_value}

            if column in _RECOMPUTE_DERIVED_ON:
                self._compute_derived_fields(trade)
                changes.update({f: getattr(trade, f) for f in _DERIVED_FIELDS})

            if column in _REGRADE_ON and trade.overall_trade_grade is not None:
                trade.overall_trade_grade = self._calculate_grade(trade)
                changes["overall_trade_grade"] = trade.overall_trade_grade

            validate_trade_data(trade)
            self.db.update_trade_fields(trade.trade_id, changes)  # type: ignore[arg-type]

            amendment.amended_at = datetime.now(tz=UTC)
            amendment.amendment_id = self.db.add_trade_amendments(amendment)

            return amendment

    def finalize_grade(self, trade_id: int, parameter_names: list) -> Trade:

        if parameter_names:
            parameter_ids: list[int] = self.db.get_parameter_ids(parameter_names)
        else:
            parameter_ids = []

        try:
            with self.db.transaction():
                trade: Trade = self.db.get_by_id(trade_id)
                if trade.overall_trade_grade is None:
                    for parameter in parameter_ids:
                        self.db.add_trade_parameters(trade_id, parameter_id=parameter)
                    graded_trade: Trade = self.grade_trade(trade)
                else:
                    raise t.TradeAlreadyGradedError("GRADING ERROR: TRADE HAS ALREADY BEEN GRADED")
        #if grade hasn't been graded and we add the parameters but still run into
        #UniqueViolationError, then this isn't a conflict, it's a server error.
        #research this later.
        except t.UniqueViolationError as e:
            raise t.ParametersConflictError(
                f"DUPLICATE PARAMETERS VIOLATE JUNCTION TABLE JOINT PK CONSTRAINT: {e}") from e

        return graded_trade

    def register_trading_account(self, account: Account) -> Account:


        account_id = self.db.create_trading_account(account)
        account.account_id = account_id

        return account

    def fetch_all_trading_accounts(self) -> list[Account]:

        return self.db.get_trading_accounts()

    def delete_trading_account(self, account_id: int) -> None:
        try:
            self.db.delete_account_from_db(account_id)
        except t.ConstraintViolationError as e:
            raise t.ConflictError(f"AN ACCOUNT WITH TRADES CAN'T BE DELETED: {e}") from e

    def fetch_trade_notes(self, trade_id: int) -> TradeNotes | None:
        try:
            return self.db.get_trade_notes(trade_id)
        except t.NotesNotFoundError:
            return None

    def fetch_present_parameters(self, trade_id: int) -> list[str]:

        parameter_ids: list[int] = self.db.get_trade_parameters(trade_id)
        return self.db.get_parameter_names(parameter_ids) if parameter_ids else []

    def delete_trade_entry(self, trade_id: int) -> None:
        self.db.delete_trade(trade_id)

    def update_trading_notes(self, trade_notes: TradeNotes) -> None:

        #database method inserts the notes row if the trade_id didn't have notes.
        #this means that this is an INSERT, not an UPDATE if no notes already exist
        self.db.update_trading_notes(new_notes=trade_notes)

    def fetch_models_list(self) -> list[TradingModel]:
        return self.db.get_models_list()

    def fetch_entry_executions_list(self) -> list[EntryExecution]:
        return self.db.get_entry_executions_list()

    def fetch_trade_management_lists(self) -> list[TradeManagement]:
        return self.db.get_trade_managements_list()

    def fetch_parameters_list(self) -> list[Parameter]:
        return self.db.get_parameters_list()

    def fetch_trading_charts(self, trade_id) -> list[TradeChart]:
        return self.db.get_trade_charts(trade_id)
