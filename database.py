import sqlite3
from models import Trade, TradeCharts, TradeNotes, Accounts

class Database:
    """CLASS TO MANAGE DATABASE OPERATIONS"""
    """HANDLES ALL THE SQL AND SQLITE3 MECHANICS."""

    def __init__(self, db_path="trades.db") -> None:
        """OPENS THE CONNECTION AND CREATES THE CURSOR"""
        """CONNECTS TO THE DATABASE FILE"""

        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.initialize_database()

#A CODE SMELL TO DO WITH THE FILE RELATIVE PATH.
#WHAT IF DATABASE IS FROM A DIFFERENT WORKING DIRECTORY.
    def initialize_database(self) -> None:
        """RUNS SCHEMA STATEMENTS FROM SCHEMA.SQL"""
        """MAKES SURE TABLES EXISTS"""

        with open("schema.sql") as f:
            self.cursor.executescript(f.read())
        self.conn.commit()

#CRUD OPERATIONS.
#HOW DO WE DO INPUT VALIDATION FOR METHODS LIKE THIS WITH SQL AND PYTHON SYNTAX TOGETHER.
#WHAT CAN GO WRONG IN THIS SCENARIO? FIND OUT.
#RESEARCH THE BUILT-IN CLASSES OF ERRORS IN SQLITE3 AND WHAT THEY MEAN.
#ADD CUSTOM EXECPTIONS TO THE CODE FOR SECOND COMMIT.

    def save_trade(self, trade: Trade) -> int:
        """SAVE TRADE TO DATABASE"""
        """RETURNS LASTROWID REPRESENTING TRADEID"""

        self.cursor.execute("INSERT INTO trades (entry_price, exit_price, take_profit, stop_loss, position_size," \
        "date, model_id, account_id, management_id, entry_execution_id, asset, direction, dollar_amount, profit_loss, rr_ratio,\
        overall_trade_grade, parameter_ids) VALUES"
        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        (trade.entry_price, trade.exit_price, trade.take_profit, trade.stop_loss, trade.position_size, trade.date, trade.model_id,
         trade.account_id, trade.management_id, trade.entry_execution_id, trade.asset, trade.direction, trade.dollar_amount,
         trade.profit_loss, trade.rr_ratio, trade.overall_trade_grade, trade.parameter_ids))
        self.conn.commit()
        return self.cursor.lastrowid
    
#FETCHONE RETURNS NONE IF THE TRADE_ID DOESN'T EXIST.
#WE NEED TO CHECK IF ROW IS NONE
#PATTERN #1: A FUNCTION CAN RETURN SOMETHING
#OTHER THAN THE HAPPY PATH TYPE AND THE CALLER NEEDS TO CHECK.
#PATTERN #2: RAISE AN EXCEPTION INSTEAD OF RETURNING NONE.
    def get_by_id(self, trade_id: int) -> Trade:
        """GET TRADE DETAILS BY ID FROM DATABASE"""
        """RETURN TRADE ROW DETAILS FROM TRADES TABLE"""
        
        self.cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise ValueError(f"TRADEID {trade_id} NOT FOUND.")
        
        return Trade(*row)
    
#WHAT DOES IT MEAN TO UPDATE A TRADE? WHAT TRADE DETAILS GET UPDATED?
#OVERRAL_TRADE_GRADE, CHARTS, TRADE_NOTES.
#THIS METHOD ONLY UPDATES TRADE_GRADE BECAUSE IT GETS FILLED IN LAST.
#HAVE METHODS THAT UPDATE CHARTS AND TRADE_NOTES.
    def update_trade_grade(self, trade_id: int, overall_trade_grade: str) -> None:
        """UPDATES OVERALL_TRADE_GRADE TO DATABASE"""

        self.cursor.execute("UPDATE trades SET overall_trade_grade = ? WHERE trade_id = ?", (overall_trade_grade, trade_id))
        self.conn.commit()

#WHAT HAPPENS WHEN A TRADER UPDATES A TRADE FIELD LIKE EXIT_PRICE
#DO WE NEED TO UPDATE THINGS LIKE GRADE, PROFIT ETC?
#A GENERAL UPDATE METHOD TO UPDATE MORE DYNAMIC TRADE FIELDS. 
    def update_trade_field(self, trade_id: int, column: str, value) -> None:
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""
        """ALLOWED_COLUMNS OFFERS PROTECTON AGAINST SQL INJECTION."""

        ALLOWED_COLUMNS = ["entry_price", "exit_price", "take_profit", "stop_loss", "position_size", "asset", "direction"]

        if column not in ALLOWED_COLUMNS:
            raise ValueError(f"CAN'T UPDATE COLUMN NAME {column}.")
        
        sql = f"UPDATE trades SET {column} = ? WHERE trade_id = ?"
        self.cursor.execute(sql, (value, trade_id))
        self.conn.commit()

    def delete_trade(self, trade_id: int) -> None:
        """DELETE TRADE ROW DETAILS FROM DATABASE"""

        self.cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
        self.conn.commit()

    def add_chart(self, trade_id: int, charts: TradeCharts) -> int:
        """ATTACH TRADE CHART TO DATABASE"""

        self.cursor.execute("INSERT INTO charts (trade_id, filepath, timeframe) VALUES (?, ?, ?)",
                            (trade_id, charts.filepath, charts.timeframe))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_trade_notes(self, trade_id: int, trade_notes: TradeNotes) -> int:
        """ATTACH TRADE NOTES TO DATABASE"""
        """TRADE NOTES INCLUDE EMOTIONS, MISTAKES, THOUGHTS"""
        """ARGS: trade_id IDENTIFIER, TRADENOTE OBJECT"""

        self.cursor.execute("INSERT INTO trade_notes (trade_id, emotions, mistakes, thoughts) VALUES" \
        "(?, ?, ?, ?)", (trade_id, trade_notes.emotions, trade_notes.mistakes, trade_notes.thoughts))
        self.conn.commit()
        return self.cursor.lastrowid

#WHEN WE USE CURSOR.EXECUTE() TO GET ONE INT FROM DATABASE,
#HOW DOES RETURN MECHANICS WORK, DO WE STORE IT IN A VARIABLE???
    def get_entry_execution_points(self, entry_execution_id: int) -> int:
        """GET ENTRY EXECUTION POINTS FROM DATABASE"""
        """ARGS: ENTRY_EXECUTION_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""

        self.cursor.execute("SELECT points FROM entry_execution WHERE entry_execution_id = ?", (entry_execution_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise ValueError(f"ENTRY EXECUTION ID {entry_execution_id} NOT FOUND.")
        
        return row[0]

    def get_trade_management_points(self, management_id: int) -> int:
        """GET MANAGEMENT POINTS FROM DATABASE"""
        """ARGS: MANAGEMENT_ID FROM TRADE OBJECT"""
        """RETURNS AN INT AS NUMBER OF POINTS SCORED BY TRADE"""
        
        self.cursor.execute("SELECT points FROM trade_management WHERE management_id = ?", (management_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise ValueError(f"MANAGEMENT ID {management_id} NOT FOUND.")
        
        return row[0]

#WE DON'T NEED TO CHECK IF FETCHONE() RETURNS NONE IN THIS METHOD
#BECAUSE THE AGGREGATE FUNCTION COUNT(*) WILL NOT RETURN NONE
#EVEN IF WE HAVE 0 PARAMETERS FOR THE TRADE.
#AGGREGATE FUNCTIONS ALWAYS RETURN ONE OUTPUT ROW EVEN FOR EMPTY RESULT SETS.

#DO WE HAVE A DATABASE METHOD THAT INSERTS INTO TRADE PARAMETERS TABLE.
#HOW DO WE INSERT INTO TRADE PARAMETERS TABLE?
    def get_parameters_points(self, trade_id: int) -> int:
        """FIND HOW MANY PARAMETER POINTS THE TRADE HAS"""
        """ARGS: TRADE_ID ROW IDENTIFIER"""
        """RETURNS INT AS THE NUMBER OF PARAMETER POINTS FOR THE TRADE."""

        self.cursor.execute("SELECT COUNT(*) FROM trade_parameters WHERE trade_id = ?", (trade_id,))
        row = self.cursor.fetchone()
        
        return row[0]

    def create_trading_account(self, account: Accounts) -> int:
        """STORE TRADING ACCOUNT DETAILS TO DATABASE"""
        """ARGS: ACCOUNT OBJECT."""
        """RETURNS INT AS THE ACCOUNT ID FOR THAT ACCOUNT."""

        self.cursor.execute("INSERT INTO accounts (account_name, account_type, broker, starting_balance, is_active) VALUES" \
        "(?, ?, ?, ?, ?)", (account.account_name, account.account_type, account.broker, account.starting_balance, account.is_active))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def close_db_connection(self):
        self.conn.close()
    
        
