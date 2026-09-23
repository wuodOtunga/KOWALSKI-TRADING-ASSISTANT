from typing import Any

from sqlalchemy import create_engine, exc, func, select
from sqlalchemy.orm import sessionmaker

import exceptions as t
from database_models import Base, Models, TradeModel, TradeNotesModel
from models import Trade, TradeGrade, TradeNotes
from schemas import AmendableColumns

SQLALCHEMY_DATABASE_URL = "sqlite:///./kowalski.db"


model_rows = [
    Models(
        model_name= 'BREAD AND BUTTER MODEL',
        description= 'REVERSAL OR CONTINUATION USING WEEKLY AND DAILY PROFILES.' \
        'ENTRY FRAMED ON CISD ORDERBLOCK LIMIT ENTRY.'
    ),
    Models(
        model_name= 'ONE SHOT ONE KILL',
        description= 'USE ICT WEEKLY PROFILES TO NARROW DOWN REVERSAL DAY OF THE WEEK. ENTRY ON PREMIUM/DISCOUNT PD ARRAYS.'
    ),
    Models(
        model_name= '2022 FVG MODEL',
        description= 'STOP RAID IN OPPOSITE DIRECTION OF DAILY BIAS. MARKET STRUCTURE SHIFT. ENTRY ON FIRST FVG AFTER REVERSAL.'
    ),
    Models(
        model_name= 'ERL TO IRL MODEL',
        description= 'PRICE TRADES BELOW OLD LOW (ERL) LEADING TO A MOVE HIGHER INTO FVG (IRL). ENTRY USING LTF CISD PATTERN.'
    ),
    Models(
        model_name= 'NO MODEL USED',
        description= 'NO TRADING MODEL WAS USED FOR THIS TRADE. IT WAS A YOLO TRADE AKA A GHOST TRADE. INSTANT F GRADE.'
    )
]

#result = session.execute(statement) returns a Result object which is a Row. So result = Row(TradeModel,)
#This is like that every return value in sqlite is a tuple, even one element tuple.
#.scalars exist to unwrap this Row object into a single element, so something like TradeModel called ScalarResult.
#.scalar() is called on a Result object
#
class Repository:
    def __init__(self, db_path=SQLALCHEMY_DATABASE_URL):
        self.db_path = db_path

        self.engine = create_engine(
            url= self.db_path,
            connect_args= {"check_same_thread" : False},
            echo= True
        )

        self.SessionLocal = sessionmaker(bind= self.engine, expire_on_commit= False)
        self.initialize_database()

    def initialize_database(self):

        import database_models  # noqa: F401
        Base.metadata.create_all(bind= self.engine)

        with self.SessionLocal.begin() as session:
            count = session.scalar(select(func.count()).select_from(Models))
            if count == 0:
                session.add_all(model_rows)

#TRADE DOMAIN MODEL DATABASE METHODS; CRUd
    def save_trade(self, trade: Trade) -> int:
        """PERSIST A TRADE TO THE REPOSITORY"""

        new_trade = TradeModel(
            entry_price = trade.entry_price,
            exit_price = trade.exit_price,
            take_profit= trade.take_profit,
            stop_loss= trade.stop_loss,
            position_size= trade.position_size,
            entry_time= trade.entry_time,
            exit_time= trade.exit_time,
            date= trade.date,
            model_id= trade.model_id,
            account_id= trade.account_id,
            management_id= trade.management_id,
            entry_execution_id= trade.entry_execution_id,
            asset= trade.asset,
            direction= trade.direction,
            dollar_amount= trade.dollar_amount,
            duration= trade.duration,
            result= trade.result,
            rr_multiple= trade.rr_multiple,
            risk_percent= trade.risk_percent,
            overall_trade_grade= trade.overall_trade_grade
        )

        with self.SessionLocal.begin() as session:
            session.add(new_trade)

            try:
                session.flush()
            except exc.IntegrityError as e:
                raise t.Constraint_Violation_Error(f"CONSTRAINT VIOLATION DETECTED: {e.orig}") from e

            trade_id = new_trade.trade_id

        return trade_id

    def get_by_id(self, trade_id: int) -> TradeModel:
        """RETRIEVE A TRADE FROM THE REPOSITORY"""

        #what is one row of my result supposed to contain?
        with self.SessionLocal.begin() as session:
            result = session.execute(select(TradeModel).where(TradeModel.trade_id == trade_id))

            #scalar_one_or_none() - Preferred for querying using a PK.
            trade = result.scalar_one_or_none()
            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NOT TRADE FOUND!")

        return trade

    def get_all_trade_rows(self):
        """RETRIEVES ALL TRADES FROM THE REPOSITORY"""

        with self.SessionLocal.begin() as session:
            result = session.execute(select(TradeModel))
            trades = result.scalars().all()

        return trades

    def update_trade_grade(self, trade_id: int, new_grade: TradeGrade):
        """UPDATES TRADE.OVERALL_TRADE_GRADE IN THE REPOSITORY"""

        if not isinstance(new_grade, TradeGrade):
            raise t.Invalid_Grade_Error("GRADE NEEDS TO BE OF TYPE TRADEGRADE.")

        with self.SessionLocal() as session:
            trade_row = session.execute(
                select(TradeModel).where(TradeModel.trade_id == trade_id)
            ).scalar_one_or_none()

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")

            trade_row.overall_trade_grade = new_grade

            session.commit()

    def update_trade_field(self, trade_id: int, new_value: Any, column: AmendableColumns):
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""

        with self.SessionLocal() as session:
            trade_row = session.execute(
                select(TradeModel).where(TradeModel.trade_id == trade_id)
            ).scalar_one_or_none()

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")
        #COMPLETE THIS LATER!

    def delete_trade(self, trade_id: int):
        """DELETES A TRADE ROW FROM THE REPOSITORY"""

        with self.SessionLocal.begin() as session:
            trade_row = session.get(TradeModel, trade_id)

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")

            session.delete(trade_row)

#TRADE NOTES DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_notes(self, trade_id: int, notes: TradeNotes):

        with self.SessionLocal.begin() as session:
            trade = session.get(TradeModel, trade_id)

            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE FOUND")

            session.add(TradeNotesModel(
                trade_id= notes.trade_id,
                emotions= notes.emotions,
                mistakes= notes.mistakes,
                lessons= notes.lessons,
                general_notes= notes.general_notes,
            ))

            try:
                session.flush()
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

    def get_trade_notes(self, trade_id: int):

        with self.SessionLocal() as session:
            notes = session.get(TradeNotesModel, trade_id)

            if not notes:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. TRADE NOT FOUND")

        return notes

    def update_trading_notes(self, trade_id: int, new_notes: TradeNotes):
        """UPDATES FULL ROW ON TRADE NOTES DATABASE TABLE"""

        with self.SessionLocal() as session:
            notes = session.get(TradeNotesModel, trade_id)

            if not notes:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE FOUND")

            notes.emotions = new_notes.emotions
            notes.mistakes = new_notes.mistakes
            notes.lessons = new_notes.lessons
            notes.general_notes = new_notes.general_notes

            session.commit()

#TRADE PARAMETERS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_parameters(self):
        pass

    def get_trade_parameters(self):
        pass

#TRADING ACCOUNTS DOMAIN MODEL DATABASE METHODS; CRUD
    def create_trading_account(self):
        pass

    def get_trading_accounts(self):
        pass

    def get_current_account_balance(self):
        pass

    def delete_account_from_db(self):
        pass

#TRADING CHARTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_chart(self):
        pass

    def get_trade_charts(self):
        pass

#TRADING AMENDMENTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_amendments(self):
        pass

#STATIC LOOK UP TABLES DATABASE READ METHODS; GETTER METHODS
#STATIC TABLES: MODELS, TRADE_MANAGEMENT, PARAMETERS, ENTRY_EXECUTION
    def get_parameter_ids(self):
            pass

    def get_parameter_names(self):
        pass

    def get_entry_execution_points(self):
        pass

    def get_trade_management_points(self):
        pass

#REPORTS/STATISTICS/ANALYTICS AGGREGATION DATABASE METHODS FOR REPORTS.PY
    def get_global_stats_rows(self):
        pass

#MISCELLANEOUS DATABASE METHODS FOR VARIOUS ABSTRACTIONS
    def check_foreign_keys(self):
        pass

    def close_db_connection(self):
        pass

Repository()