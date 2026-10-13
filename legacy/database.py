import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any

import exceptions as t
from models import (
    Account,
    Amendments,
    EntryExecution,
    Parameter,
    Trade,
    TradeAsset,
    TradeChart,
    TradeDirection,
    TradeGrade,
    TradeManagement,
    TradeNotes,
    TradeResult,
    TradingModel,
)
from seed_data import (
    accounts,
    entry_execution,
    models,
    parameter_values,
    trade_management,
)


class Database:
    """CLASS TO MANAGE DATABASE OPERATIONS"""
    """HANDLES ALL THE SQL AND SQLITE3 MECHANICS."""

    SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
    DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")

    def __init__(self, db_path=DB_PATH) -> None:
        """OPENS THE CONNECTION AND CREATES THE CURSOR"""
        """CONNECTS TO THE DATABASE FILE"""

        self.db_path = db_path
        self.conn = sqlite3.connect(database=self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        self.initialize_database()

    #DATABASE ISSUE: IF YOU DELETE/ADD A COLUMN IN A TABLE, WHEN PROGRAM RUNS AGAIN,
    #IT DOESN'T CREATE NEW VERSION OF THE TABLE BECAUSE THE TABLE ALREADY EXISTS.
    #FIND A FIX.
    def initialize_database(self) -> None:
        """RUNS SCHEMA STATEMENTS FROM SCHEMA.SQL"""
        """MAKES SURE TABLES EXISTS"""

        cursor = self.conn.cursor()
        with open(self.SCHEMA_PATH) as f:
            cursor.executescript(f.read())

        cursor.execute("SELECT COUNT(*) FROM models")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO models (model_name, description) VALUES (?, ?)", models)

        cursor.execute("SELECT COUNT(*) FROM entry_execution")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO entry_execution (archetype, description, points, grade) VALUES (?, ?, ?, ?)",
                entry_execution
            )

        cursor.execute("SELECT COUNT(*) FROM trade_management")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO trade_management (archetype, description, points, grade) VALUES (?, ?, ?, ?)",
                trade_management
            )

        cursor.execute("SELECT COUNT(*) FROM parameters")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO parameters (parameter_name) VALUES (?)", parameter_values)

        cursor.execute("SELECT COUNT(*) FROM accounts")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO accounts (account_name, account_type, broker, starting_balance, is_active)" \
                "VALUES (?, ?, ?, ?, ?)",
                accounts
            )

        self.conn.commit()

    def commit(self):
        """DATABASE COMMITS"""
        self.conn.commit()

    def rollback(self):
        """DATABASE ROLLBACKS"""
        self.conn.rollback()

    def _ensure_trade_exists(self, trade_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM trades WHERE trade_id = ?)", (trade_id,))
        exists = cursor.fetchone()[0]
        if not exists:
            raise t.TradeNotFoundError(f"TRADE_ID {trade_id} IS INVALID.")

#Foreign-key error translation is too broad
#REFINE TO IDENTIFY WHICH ERROR HAPPENED.
#foreign-key violation, UNIQUE constraint violation
#CHECK constraint violatioN, NOT NULL violation
#PRIMARY KEY violation
#FIX: USE SQLITE ERROR CODES
    def save_trade(self, trade: Trade) -> int:
        """SAVE TRADE TO DATABASE"""
        """RETURNS LASTROWID REPRESENTING TRADEID"""

    #UPDATE THIS METHOD WITH THE NEW ENUM TYPES FROM MODELS.
        if trade.asset not in ["XAUUSD", "XAGUSD", "NQ", "ES"]:
            raise t.TradeValidationError(f"INVALID ASSET DETECTED {trade.asset}")
        if trade.direction not in ["long", "short"]:
            raise t.TradeValidationError(f"INVALID DIRECTION DETECTED {trade.direction}")
        self.check_foreign_keys(trade)

        cursor = self.conn.cursor()

        #I RAN INTO SQLITE3.OPERATIONALERROR: TABLE TRADES HAS NO COLUMN NAMED account_balance
        #ADDING NEW FIELDS IN THE TRADE DATACLASS, THEN ADDING INTO THE SAVE TRADE INSERT SQL STRING
        #BUT THEN FORGETTING TO UPDATE THE SCHEMA.SQL FILE.
        #ADD AN EXTRA EXCEPT CLAUSE FOR THIS SQLITE3 ERROR.
        #ALSO RAN INTO SQLITE3.PROGRAMMINGERROR: CONNECTION OBJECT CAN ONLY BE USED IN THE SAME THREAD
        #IT WAS CREATED. RESEARCH MORE ABOUT SQLITE3 THREAD MECHANICS
        #I RAN INTO SQLITE3.PROGRAMMINGERROR: PARAMETERS ARE OF UNSUPPORTED TYPES.
        #I PASSED TRADE_ID AS A PARAMETER INSTEAD OF A ONE ELEMENT TUPLE LIKE SO (TRADE_ID,)
        #DATABASE IS CURRENTLY LOCKED. FIND OUT WHAT CAUSES THIS AND A FIX.
        try:
            cursor.execute(
            "INSERT INTO trades" \
            "(entry_price, exit_price, take_profit, stop_loss, position_size, entry_time, exit_time,"
            "date, model_id, account_id, management_id, entry_execution_id, asset, direction, dollar_amount,"
            "duration, result, rr_multiple, risk_percent, overall_trade_grade) VALUES"
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (trade.entry_price, trade.exit_price, trade.take_profit, trade.stop_loss, trade.position_size,
             trade.entry_time.strftime("%I:%M %p"), trade.exit_time.strftime("%I:%M %p"),
             trade.date.isoformat(), trade.model_id, trade.account_id, trade.management_id,
             trade.entry_execution_id, trade.asset, trade.direction, trade.dollar_amount,
            trade.duration.total_seconds(), trade.result, trade.rr_multiple, # pyright: ignore[reportOptionalMemberAccess]
            trade.risk_percent, trade.overall_trade_grade))
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(
                f"CHECK FOR FOREIGN KEY VIOLATION OR COLUMN CONSTRAINT VIOLATION: {e}.") from e

        return cursor.lastrowid # pyright: ignore[reportReturnType]

    def get_by_id(self, trade_id: int) -> Trade:
        """GET TRADE DETAILS BY ID FROM DATABASE"""
        """RETURN TRADE ROW DETAILS FROM TRADES TABLE"""

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.TradeNotFoundError(f"TRADEID {trade_id} NOT FOUND.")

        row_dict: dict[Any, Any] = dict(row)
        trade: Trade = self._row_to_trade(row_dict)
        return trade

    def get_all_trade_rows(self) -> list[Trade]:

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades")
        rows = cursor.fetchall()
        if not rows:
            raise t.NotFoundError("TRADES TABLE IS EMPTY!")

        trades_list = []
        for row in rows:
            row_dict = dict(row)
            trade = self._row_to_trade(row_dict)
            trades_list.append(trade)

        return trades_list

    def update_trade_grade(self, trade_id: int, overall_trade_grade: TradeGrade) -> None:
        """UPDATES OVERALL_TRADE_GRADE TO DATABASE"""
        if not isinstance(overall_trade_grade, TradeGrade):
            raise t.GradingError(f"{overall_trade_grade} IS INVALID.")

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE trades SET overall_trade_grade = ? WHERE trade_id = ?", (overall_trade_grade, trade_id)
        )
        if cursor.rowcount == 0:
            raise t.TradeNotFoundError(f"TRADE_ID {trade_id} NOT FOUND.")

#A GENERAL UPDATE METHOD TO UPDATE MORE DYNAMIC TRADE FIELDS.
    def update_trade_field(self, trade_id: int, column: str, value) -> None:
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""

        #POSSIBLE SQL INJECTION VECTOR IS PROTECTED BY THE CALLER
        sql = f"UPDATE trades SET {column} = ? WHERE trade_id = ?"  # noqa: S608
        cursor = self.conn.cursor()
        cursor.execute(sql, (value, trade_id))
        if cursor.rowcount == 0:
            raise t.TradeNotFoundError(f"NO ROW MATCHES THE {trade_id}.")

    def delete_trade(self, trade_id: int) -> None:
        """DELETE TRADE ROW DETAILS FROM DATABASE"""

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
        if cursor.rowcount == 0:
            raise t.TradeNotFoundError(f"NO ROW MATCHES THE {trade_id}")

        self.conn.commit()

    def add_chart(self, chart: TradeChart) -> int:
        """ATTACH TRADE CHART TO DATABASE"""

        self._ensure_trade_exists(chart.trade_id)  #raise t.TradeNotFoundError

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO charts (trade_id, filepath, filename, upload_date) VALUES (?, ?, ?, ?)",
                (chart.trade_id, chart.filepath, chart.filename, chart.upload_date))
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(f"CHECK FOR COLUMN CONSTRAINT VIOLATION: {e}.") from e

        return cursor.lastrowid # pyright: ignore[reportReturnType]

    def add_trade_notes(self, trade_notes: TradeNotes) -> None:
        """ATTACH TRADE NOTES TO DATABASE"""
        """TRADE NOTES INCLUDE EMOTIONS, MISTAKES, LESSONS"""
        """ARGS: trade_id IDENTIFIER, TRADENOTE OBJECT"""

        #check for validity of the trade_id FK and rule out FK constraint violation error.
        self._ensure_trade_exists(trade_notes.trade_id) # pyright: ignore[reportArgumentType]

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO trade_notes (trade_id, emotions, mistakes, lessons, general_notes) VALUES" \
            "(?, ?, ?, ?, ?)",
            (trade_notes.trade_id, trade_notes.emotions, trade_notes.mistakes,
             trade_notes.lessons, trade_notes.general_notes))
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(f"CHECK FOR COLUMN CONSTRAINT VIOLATION: {e}.") from e

    def update_trading_notes(self, trade_notes: TradeNotes) -> None:
        """UPDATES FULL ROW ON TRADE NOTES DATABASE TABLE"""

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE trade_notes
            SET emotions = ?, mistakes = ?, lessons = ?, general_notes = ?
            WHERE trade_id = ?
            (?, ?, ?, ?, ?)
            """,
            (trade_notes.emotions, trade_notes.mistakes, trade_notes.lessons,
             trade_notes.general_notes, trade_notes.trade_id)
        )
        if cursor.rowcount == 0:
            raise t.TradeNotFoundError("TRADE_ID IS INVALID. NO TRADE MATCHES")

#FIX THE DATETIME CONVERSION TO ISO 8601 TEXT
    def add_trade_amendments(self, trade_id, amendment: Amendments) -> int:

        cursor = self.conn.cursor()
        try:
            cursor.execute(
            "INSERT INTO trade_amendments (trade_id, column_name, old_value, new_value, amended_at) VALUES " \
            "(?, ?, ?, ?, ?)",
            (trade_id, amendment.column_name, amendment.old_value, amendment.new_value, amendment.amended_at))
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(
                f"CHECK FOR FOREIGN KEY VIOLATION OR COLUMN CONSTRAINT VIOLATION: {e}.") from e

        return cursor.lastrowid # pyright: ignore[reportReturnType]

    def get_entry_execution_points(self, entry_execution_id: int) -> int:
        """GET ENTRY EXECUTION POINTS FROM DATABASE"""
        """ARGS: ENTRY_EXECUTION_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT points FROM entry_execution WHERE entry_execution_id = ?", (entry_execution_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise t.InvalidIdentifierError(f"ENTRY EXECUTION ID {entry_execution_id} NOT FOUND.")

        return row["points"]

    def get_trade_management_points(self, management_id: int) -> int:
        """GET MANAGEMENT POINTS FROM DATABASE"""
        """ARGS: MANAGEMENT_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""

        cursor = self.conn.cursor()
        cursor.execute("SELECT points FROM trade_management WHERE management_id = ?", (management_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.InvalidIdentifierError(f"MANAGEMENT ID {management_id} NOT FOUND.")

        return row["points"]

    def add_trade_parameters(self, trade_id: int, parameter_id: int) -> None:
        """POPULATES THE TRADE_PARAMETERS JUNCTION TABLE."""
        """ARGS: TRADE_ID, PARAMETER_ID: JOINT PRIMARY KEY"""

        cursor: sqlite3.Cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO trade_parameters (trade_id, parameter_id) VALUES (?, ?)",
                (trade_id, parameter_id)
            )
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(f"CAN'T LINK {trade_id} TO {parameter_id} : {e}") from e

    def get_trade_parameters(self, trade_id: int) -> list:
        """FIND HOW MANY PARAMETER POINTS THE TRADE HAS"""
        """ARGS: TRADE_ID ROW IDENTIFIER"""
        """RETURNS LIST OF PARAMETER IDS MATCHING THE TRADE_ID"""

        self._ensure_trade_exists(trade_id) #raises t.TradeNotFoundError

        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM trade_parameters WHERE trade_id = ?", (trade_id,))

        row = cursor.fetchall()
        parameter_ids = []
        for _, parameter_id in row:
            parameter_ids.append(parameter_id)

        return parameter_ids

    def create_trading_account(self, account: Account) -> int:
        """STORE TRADING ACCOUNT DETAILS TO DATABASE"""
        """ARGS: ACCOUNT OBJECT."""
        """RETURNS INT AS THE ACCOUNT ID FOR THAT ACCOUNT."""

        cursor = self.conn.cursor()
        try:
            cursor.execute(
            "INSERT INTO accounts (account_name, account_type, broker, starting_balance, is_active) VALUES" \
            "(?, ?, ?, ?, ?)",
            (account.account_name, account.account_type, account.broker,
             account.starting_balance, account.is_active))
        except sqlite3.IntegrityError as e:
            raise t.ConstraintViolationError(f"CHECK FOR COLUMN CONSTRAINT VIOLATION: {e}") from e

        return cursor.lastrowid # type: ignore  # noqa: PGH003

    def delete_account_from_db(self, account_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
        if cursor.rowcount == 0:
            raise t.InvalidIdentifierError(f"NO ROW MATCHES THE {account_id}")

        self.conn.commit()

    def check_foreign_keys(self, trade: Trade) -> None:
        """CHECKS FOR EXISTENCE OF ACCOUNT_ID, MANAGEMENT_ID,
        ENTRY_EXECUTION_ID, MODEL_ID"""

        cursor = self.conn.cursor()

        cursor.execute("SELECT EXISTS(SELECT 1 FROM accounts WHERE account_id = ?)", (trade.account_id,))
        exists = cursor.fetchone()[0]
        if not exists:
            raise t.InvalidIdentifierError(f"ACCOUNT WITH ID OF {trade.account_id} DOESN'T EXIST.")

        cursor.execute("SELECT EXISTS(SELECT 1 FROM models WHERE model_id = ?)", (trade.model_id,))
        exists = cursor.fetchone()[0]
        if not exists:
            raise t.InvalidIdentifierError(f"MODEL WITH {trade.model_id} DOESN'T EXISTS.")

        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM trade_management WHERE management_id = ?)", (trade.management_id,)
        )
        exists = cursor.fetchone()[0]
        if not exists:
            raise t.InvalidIdentifierError(f"{trade.management_id} DOESN'T MATCH ANY MANAGEMENT ARCHETYPE.")

        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM entry_execution WHERE entry_execution_id = ?)",
            (trade.entry_execution_id,)
        )
        exists = cursor.fetchone()[0]
        if not exists:
            raise t.InvalidIdentifierError(f"{trade.entry_execution_id} DOESN'T MATCH ANY ARCHETYPE.")

    def get_current_account_balance(self, account_id: int) -> float:
        """CALCULATES LIVE VALUE OF ACCOUNT BALANCE WHEN NEEDED!"""

        #check_foreign_keys() already validates that account_id is valid.

        cursor = self.conn.cursor()
        cursor.execute("SELECT starting_balance FROM accounts WHERE account_id = ?", (account_id,))
        row = cursor.fetchone()
        starting_balance = row["starting_balance"]

        cursor.execute(
            "SELECT COALESCE(SUM(DOLLAR_AMOUNT), 0) FROM trades WHERE account_id = ?", (account_id,)
        )
        total_pnl = cursor.fetchone()[0]

        return starting_balance + total_pnl

    def get_trading_accounts(self) -> list[Account]:

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        rows = cursor.fetchall()
        if not rows:
            raise t.NotFoundError("NO ACCOUNTS FOUND!")

        return [Account(**dict(row)) for row in rows]

    def get_trade_notes(self, trade_id: int) -> TradeNotes:

        self._ensure_trade_exists(trade_id)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trade_notes WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.NotesNotFoundError("THE TRADE HAS NO AVAILABLE NOTES")

        return TradeNotes(**dict(row))

    def get_trade_charts(self, trade_id: int) -> list[TradeChart]:

        self._ensure_trade_exists(trade_id=trade_id)  #raise t.TradeNotFoundError

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM charts WHERE trade_id = ?", (trade_id,))
        rows = cursor.fetchall()

        #i actually don't want to return an empty list for no charts found.
        #this might be ambiguous in the future, like why is the list empty???
        if not rows:
            raise t.ChartsNotFoundError("THE TRADE HAS NO CHARTS ATTACHED YET")

        return [TradeChart(**dict(row)) for row in rows]

    def get_parameter_ids(self, parameter_names: list) -> list:
        cursor = self.conn.cursor()
        parameter_ids = []
        for parameter in parameter_names:
            cursor.execute("SELECT parameter_id FROM parameters WHERE parameter_name = ?", (parameter,))
            row = cursor.fetchone()
            parameter_ids.append(row[0])

        return parameter_ids

    def get_parameter_names(self, parameter_ids: list) -> list:
        cursor = self.conn.cursor()
        parameter_names = []
        for parameter in parameter_ids:
            cursor.execute("SELECT parameter_name FROM parameters WHERE parameter_id = ?", (parameter,))
            row = cursor.fetchone()
            parameter_names.append(row[0])

        return parameter_names

    def get_models_list(self) -> list[TradingModel]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models")
        rows = cursor.fetchall()

        return [TradingModel(**dict(row)) for row in rows]

    def get_entry_executions_list(self) -> list[EntryExecution]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entry_execution")
        rows = cursor.fetchall()

        return [EntryExecution(**dict(row)) for row in rows]

    def get_trade_managements_list(self) -> list[TradeManagement]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trade_management")
        rows = cursor.fetchall()

        return [TradeManagement(**dict(row)) for row in rows]

    def get_parameters_list(self) -> list[Parameter]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM parameters")
        rows = cursor.fetchall()

        return [Parameter(**dict(row)) for row in rows]

    def get_global_stats_rows(self):
        pass

    def _row_to_trade(self, row_dict: dict):
        """BUILDS TRADE OBJECT FROM SQLITE ROW VALUES"""
        row_dict["trade_id"] = int(row_dict["trade_id"])
        row_dict["entry_price"] = float(row_dict["entry_price"])
        row_dict["exit_price"] = float(row_dict["exit_price"])
        row_dict["take_profit"] = float(row_dict["take_profit"])
        row_dict["position_size"] = float(row_dict["position_size"])
        row_dict["entry_time"] = datetime.strptime(row_dict["entry_time"], "%I:%M %p").time()
        row_dict["exit_time"] = datetime.strptime(row_dict["exit_time"], "%I:%M %p").time()
        row_dict["date"] = datetime.fromisoformat(row_dict["date"])
        row_dict["model_id"] = int(row_dict["model_id"])
        row_dict["account_id"] = int(row_dict["account_id"])
        row_dict["management_id"] = int(row_dict["management_id"])
        row_dict["entry_execution_id"] = int(row_dict["entry_execution_id"])
        row_dict["asset"] = TradeAsset(row_dict["asset"])
        row_dict["direction"] = TradeDirection(row_dict["direction"])
        row_dict["dollar_amount"] = float(row_dict["dollar_amount"])
        row_dict["duration"] = timedelta(seconds=row_dict["duration"])
        row_dict["result"] = TradeResult(row_dict["result"])
        row_dict["rr_multiple"] = float(row_dict["rr_multiple"])
        row_dict["risk_percent"] = float(row_dict["risk_percent"])

        if row_dict["overall_trade_grade"] is not None:
            row_dict["overall_trade_grade"] = TradeGrade(row_dict["overall_trade_grade"])

        return Trade(**row_dict)

#RESEARCH THE MECHANICS OF CLOSE() METHOD
#OPEN FILE LOCKS/STREAMLIT PROCESS FOR EVERY RERUN
#REAL THREAD CONCURRENCY IN SQLITE3 MECHANICS.
    def close_db_connection(self):
        self.conn.close()




