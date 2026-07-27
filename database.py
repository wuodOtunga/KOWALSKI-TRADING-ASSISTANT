import os
import sqlite3

import exceptions as t
from models import Accounts, Trade, TradeCharts, TradeNotes


class Database:
    """CLASS TO MANAGE DATABASE OPERATIONS"""
    """HANDLES ALL THE SQL AND SQLITE3 MECHANICS."""

    SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
    DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")

    def __init__(self, db_path=DB_PATH) -> None:
        """OPENS THE CONNECTION AND CREATES THE CURSOR"""
        """CONNECTS TO THE DATABASE FILE"""

        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        self.initialize_database()

    def initialize_database(self) -> None:
        """RUNS SCHEMA STATEMENTS FROM SCHEMA.SQL"""
        """MAKES SURE TABLES EXISTS"""

        cursor = self.conn.cursor()
        with open(self.SCHEMA_PATH) as f:
            cursor.executescript(f.read())
        self.conn.commit()

    def save_trade(self, trade: Trade) -> int:
        """SAVE TRADE TO DATABASE"""
        """RETURNS LASTROWID REPRESENTING TRADEID"""

        if trade.asset not in ["XAUUSD", "XAGUSD", "NQ", "ES"]:
            raise t.Invalid_Asset_Error
        if trade.direction not in ["long", "short"]:
            raise t.Invalid_Direction_Error

        cursor = self.conn.cursor()

        try:
            cursor.execute("INSERT INTO trades (entry_price, exit_price, take_profit, stop_loss, position_size," \
            "date, model_id, account_id, management_id, entry_execution_id, asset, direction, dollar_amount, profit_loss, rr_ratio,\
            overall_trade_grade, parameter_ids) VALUES"
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (trade.entry_price, trade.exit_price, trade.take_profit, trade.stop_loss, trade.position_size, trade.date, trade.model_id,
            trade.account_id, trade.management_id, trade.entry_execution_id, trade.asset, trade.direction, trade.dollar_amount,
            trade.profit_loss, trade.rr_ratio, trade.overall_trade_grade, trade.parameter_ids))
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise t.ConstraintViolationError(f"FOREIGN KEY VIOLATION DETECTED. {e}") from e
                
        self.conn.commit()
        return cursor.lastrowid
    
    def get_by_id(self, trade_id: int) -> Trade:
        """GET TRADE DETAILS BY ID FROM DATABASE"""
        """RETURN TRADE ROW DETAILS FROM TRADES TABLE"""
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.TradeNotFoundError(f"TRADEID {trade_id} NOT FOUND.")
        
        return Trade(**dict(row))
    
    def update_trade_grade(self, trade_id: int, overall_trade_grade: str) -> None:
        """UPDATES OVERALL_TRADE_GRADE TO DATABASE"""
        if overall_trade_grade not in ["A+", "B", "C", "D", "F"]:
            raise t.Invalid_Grade_Error(f"{overall_trade_grade} IS INVALID.")
        
        cursor = self.conn.cursor()
        cursor.execute("UPDATE trades SET overall_trade_grade = ? WHERE trade_id = ?", (overall_trade_grade, trade_id))
        if cursor.rowcount == 0:
            self.conn.rollback()
            raise t.TradeNotFoundError
        
        self.conn.commit()

#A GENERAL UPDATE METHOD TO UPDATE MORE DYNAMIC TRADE FIELDS. 
    def update_trade_field(self, trade_id: int, column: str, value) -> None:
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""
        """ALLOWED_COLUMNS OFFERS PROTECTON AGAINST SQL INJECTION."""

        ALLOWED_COLUMNS = ["entry_price", "exit_price", "take_profit", "stop_loss", "position_size", "asset", "direction"]

        if column not in ALLOWED_COLUMNS:
            raise t.Invalid_Column_Name_Error(f"CAN'T UPDATE COLUMN NAME {column}.")
        
        sql = f"UPDATE trades SET {column} = ? WHERE trade_id = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (value, trade_id))
        if cursor.rowcount == 0:
            self.conn.rollback()
            raise t.TradeNotFoundError(f"NO ROW MATCHES THE {trade_id}.")
        
        self.conn.commit()

    def delete_trade(self, trade_id: int) -> None:
        """DELETE TRADE ROW DETAILS FROM DATABASE"""

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
        if cursor.rowcount == 0:
            self.conn.rollback()
            raise t.TradeNotFoundError(f"NO ROW MATCHES THE {trade_id}")
        
        self.conn.commit()

    def add_chart(self, trade_id: int, charts: TradeCharts) -> int:
        """ATTACH TRADE CHART TO DATABASE"""

        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO charts (trade_id, filepath, timeframe) VALUES (?, ?, ?)",
                            (trade_id, charts.filepath, charts.timeframe))
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise t.ConstraintViolationError(f"INVALID TRADE_ID: {trade_id}, {e}") from e
        
        self.conn.commit()
        return cursor.lastrowid
        
    def add_trade_notes(self, trade_id: int, trade_notes: TradeNotes) -> int:
        """ATTACH TRADE NOTES TO DATABASE"""
        """TRADE NOTES INCLUDE EMOTIONS, MISTAKES, THOUGHTS"""
        """ARGS: trade_id IDENTIFIER, TRADENOTE OBJECT"""

        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO trade_notes (trade_id, emotions, mistakes, thoughts) VALUES" \
            "(?, ?, ?, ?)", (trade_id, trade_notes.emotions, trade_notes.mistakes, trade_notes.thoughts))
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise t.ConstraintViolationError(f"INVALID TRADE_ID: {trade_id}, {e}") from e
        
        self.conn.commit()
        return cursor.lastrowid

    def get_entry_execution_points(self, entry_execution_id: int) -> int:
        """GET ENTRY EXECUTION POINTS FROM DATABASE"""
        """ARGS: ENTRY_EXECUTION_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""

        cursor = self.conn.cursor()
        cursor.execute("SELECT points FROM entry_execution WHERE entry_execution_id = ?", (entry_execution_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.Invalid_Identifier_Error(f"ENTRY EXECUTION ID {entry_execution_id} NOT FOUND.")
        
        return row["points"]

    def get_trade_management_points(self, management_id: int) -> int:
        """GET MANAGEMENT POINTS FROM DATABASE"""
        """ARGS: MANAGEMENT_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT points FROM trade_management WHERE management_id = ?", (management_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.Invalid_Identifier_Error(f"MANAGEMENT ID {management_id} NOT FOUND.")
        
        return row["points"]

    def add_trade_parameters(self, trade_id: int, parameter_id: int) -> None:
        """POPULATES THE TRADE_PARAMETERS JUNCTION TABLE."""
        """ARGS: TRADE_ID, PARAMETER_ID: JOINT PRIMARY KEY"""

        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO trade_parameters (trade_id, parameter_id) VALUES (?, ?)", (trade_id, parameter_id))
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise t.ConstraintViolationError(f"CAN'T LINK {trade_id} TO {parameter_id} : {e}") from e
        
        self.conn.commit()
        return cursor.lastrowid

    def get_parameters_points(self, trade_id: int) -> int:
        """FIND HOW MANY PARAMETER POINTS THE TRADE HAS"""
        """ARGS: TRADE_ID ROW IDENTIFIER"""
        """RETURNS INT AS THE NUMBER OF PARAMETER POINTS FOR THE TRADE."""

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trade_parameters WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if row is None:
            raise t.TradeNotFoundError(f"TRADE_ID {trade_id} NOT FOUND.")
        
        return row[0]

    def create_trading_account(self, account: Accounts) -> int:
        """STORE TRADING ACCOUNT DETAILS TO DATABASE"""
        """ARGS: ACCOUNT OBJECT."""
        """RETURNS INT AS THE ACCOUNT ID FOR THAT ACCOUNT."""

        if account.account_type not in ["FUNDED CHALLENGE", "FUNDED LIVE", "PERSONAL LIVE"]:
            raise t.Invalid_Account_Error("WRONG ACCOUNT TYPE DETECTED.")

        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO accounts (account_name, account_type, broker, starting_balance, is_active) VALUES" \
        "(?, ?, ?, ?, ?)", (account.account_name, account.account_type, account.broker, account.starting_balance, account.is_active))

        self.conn.commit()
        return cursor.lastrowid

#RESEARCH THE MECHANICS OF CLOSE() METHOD
#OPEN FILE LOCKS/STREAMLIT PROCESS FOR EVERY RERUN
#REAL THREAD CONCURRENCY IN SQLITE3 MECHANICS.
    def close_db_connection(self):
        self.conn.close()

#if __name__ == "__main__":
#    main()

    
        
