#THIS IS JOURNAL.PY

from datetime import date, time

import exceptions as t
import trade_calculator as y
from database import Database
from models import Trade, TradeChart, TradeNotes, TradeResult
from validation import validate_trade_data

trade1 = Trade(
    trade_id= 1,
    entry_price= 4023.90,
    exit_price= 4030.40,
    take_profit= 4045.00,
    stop_loss= 4017.58,
    position_size= 0.04,
    entry_time= time(10, 30),
    exit_time= time(12, 45),
    date= date(2026, 8, 1),
    model_id= 4,
    account_id= 1,
    management_id= 1,
    entry_execution_id= 1,
    asset= "XAUUSD",
    direction= "long",
    dollar_amount= None,
    duration= None,  #check correctness.
    result= None,
    rr_multiple= None,
    overall_trade_grade= "C"
)

trade2 = y.TradeSetup(
    entry_price= 4023.90,
    exit_price= 4030.40,
    stop_loss= 4017.58,
    take_profit= 4045.00,
    account_balance= 5000,
    risk_percent= 1,
    lot_size= 0.04,
    symbol= "XAUUSD",
    direction= "long",
    entry_time= time(6, 14),
    exit_time= time(9, 16),
    date= date(2026, 7, 28),
    duration= None
)
def main():
    db = Database()
    journal = Journal(db)
    journal.record_trade(trade1)

class Journal:

    def __init__(self, db: Database):
        self.db = db
 
    def record_trade(self, trade: Trade) -> Trade:
        """RECORDS A TRADE IN THE JOURNAL"""

        #1: ASSEMBLE/DERIVE TRADE DATA CALLER DOESN'T HAVE.
        trade = self._compute_derived_fields(trade)
        #2: VALIDATE THE TRADE DATA.
        valid_trade = validate_trade_data(trade)

        #3: PERSIST TO THE DATABASE & #4: TRANSLATE THE ERRORS.
        #ISSUE #2: WHAT CAN GO WRONG WHEN CALLING THE DATABASE METHOD?
        #CONSTRAINT_VIOLATION_ERROR("FOREIGN KEY VIOLATION DETECTED.") AS A DB ERROR.
        try:
            trade_id = self.db.save_trade(valid_trade)
        except t.Constraint_Violation_Error as e:
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}")
        except t.Invalid_Identifier_Error as e:
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}")

        trade.trade_id = trade_id

        #5: RETURN SOMETHING MEANINGFUL.
        return "SUCCESS", trade

#DOLLAR_AMOUNT, RESULT, RR_MULTIPLE, DURATION ARE DERIVED.
    def _compute_derived_fields(self, trade: Trade) -> Trade:
        """COMPUTES DERIVED FIELDS USING THE CALCULATOR MODULE."""

        results = y.calculate_profit_loss(trade2)
        dollar_amount = results["DOLLAR_AMOUNT"]
        trade.dollar_amount = dollar_amount
        result = results["RESULT"]
        if result == "PROFIT":
            result = TradeResult.PROFIT
        elif result == "LOSS":
            result = TradeResult.LOSS

        trade.result = result
        
        values = y.calculate_risk_reward_multiple(trade2)
        rr_multiple = values["RR_MULTIPLE"]
        trade.rr_multiple = rr_multiple
        duration = y.calculate_trade_duration(trade2)
        trade.duration = duration

        return trade
    
#ASSEMBLE/DERIVE DATA AND VALIDATE DATA GETS HANDLED BY STREAMLIT.
#STREAMLIT OWNS THE COLLECTION OF CHARTS DATA LOGIC.
#ATTACH CHART RECEIVES A VALID, FULLY CONSTRUCTED CHARTS DATA. 
    def attach_charts(self, trade_id: int, charts: TradeChart):

        #3: PERSIST TO DATABASE AND TRANSLATE FAILURES.
        try:
            chart_id = self.db.add_chart(trade_id, charts)
        except t.Constraint_Violation_Error as e:
            raise t.Chart_Upload_Error(f"TRADE_ID PROVIDED {trade_id} DOESN'T EXIST: {e}")

        charts.chart_id = chart_id

        #4: RETURN SOMETHING MEANINGFUL.
        return charts

#INPUTS: TRADE_ID
#OUTPUTS: ENTRY_EXECUTION, TRADE_MANAGEMENT, TRADE_PARAMETERS, MODEL USED
#RESPONSIBILITY: EVALUATES THE POINTS ATTACHED TO A TRADE.
#ERRORS: INVALID_IDENTIFIER_ERROR, TRADE_NOT_FOUND_ERROR.
#CALLS GET_ENTRY_EXECUTION_POINTS, GET_TRADE_MANAGEMENT_POINTS
#AND GET_PARAMETER_POINTS METHODS IN DATABASE CLASS  
    def evaluate_trade(self, trade_id: int):
        pass

#INPUTS: ENTRY_EXECUTION POINTS, TRADE_MANAGEMENT POINTS,
#TRADE_PARAMETERS, TRADE_ID
#OUTPUTS: GRADE AS A STR VALUE.
#RESPONSIBILITY: RETURN THE GRADE OF A TRADE.
#ERRORS: CONSTRAINT VIOLATION ERROR, INVALID IDENTIFIER ERROR.
#CALLS EVALUATE_TRADE() METHOD IN JOURNAL CLASS
    def grade_trade(self):
        pass

#INPUTS: TRADE_NOTE OBJECT, TRADE_ID.
#OUTPUTS: NOTHING. HOW DO WE KNOW THAT THE NOTES HAVE BEEN ADDED?
#RESPONSIBILITY: Add thoughts, mistakes, emotions, lessons, observations.
#ERRORS: TRADE_NOT_FOUND_ERROR.
#CALLS ADD_TRADE_NOTES METHOD IN DATABASE CLASS.
    def add_reflection_notes(self, trade_id: int, trade_notes: TradeNotes):
        pass

#INPUTS: TRADE_ID.
#OUTPUTS: A TRADE OBJECT FROM THE TRADES TABLE.
#RESPONSIBILITY: SHOW THE TRADE DATA OF A PARTICULAR TRADE.
#ERRORS: TRADE_NOT_FOUND_ERROR FOR MISSING TRADE.
#CALLS GET_BY_ID METHOD IN DATABASE CLASS.
    def get_trade(self, trade_id: int):
        pass

#JOURNAL ENTRY DEFINITION: TRADES DATA FROM TRADES TABLE,
#TRADE NOTES, CHARTS, TRADE_PARAMETERS PRESENT AND ABSENT,
#ACCOUNT USED, TRADE MANAGEMENT/ENTRY_EXECUTION INFO STATS,
#MODEL USED, GRADE.
#INPUTS: TRADE_ID
#OUTPUTS: TRADE OBJECT, TRADE_NOTE OBJECT, CHART OBJECT,
#TRADE PARAMETERS DATA, MANAGEMENT/ENTRY_EXECUTION DATA ETC
#RESPONSIBILITY: SHOW THE COMPLETE TRADE INFORMATION TO A USER.
#ERRORS: ALL METHODS CALLED BY THIS FUNCTION, ALL THEIR ERRORS APPLY TOO
#TBD: SPECIFIC DEFINITION OF THE ERRORS IS TO BE DETERMINED.
    def get_journal_entry(self, trade_id: int):
        pass

#ENTIRE TRADE DEFINITION: SAME AS ABOVE.
#INPUTS: TRADE OBJECT, TRADE_NOTE OBJECT, CHART OBJECT,
#TRADE PARAMETERS DATA, MANAGEMENT/ENTRY_EXECUTION DATA, ETC
#OUTPUT: SUCCESS/FAILURE MESSAGE TO SHOW SUCCESS OR FAILURE.
#RESPONSIBILITY: CREATE A FULL JOURNAL ENTRY THAT CONTAINS ALL THE
#TRADE DATA STATS TO BE JOURNALED AT ONCE.
#ERRORS: ALL METHODS CALLED BY THIS FUNCTION, ALL THEIR ERRORS APPLY TOO
#TBD: SPECIFIC DEFINITION OF THE ERRORS IS TO BE DETERMINED. 
    def record_journal_entry(self, trade: Trade, chart: TradeChart, trade_notes: TradeNotes):
        pass

#QUESTION TO PONDER: WHAT DOES AMEND JOURNALE ENTRY MEAN?
#I discovered something was wrong or incomplete. Change it.
#WHAT IS BEING AMENDED? TRADES TABLE OR ANY OTHER TABLE?
#INPUTS: TRADE_ID, TRADE CHANGES TO BE MADE.
#OUTPUTS: SUCCESS/FAILURE MESSAGE.
#RESPONSIBILITY: AMEND A TABLE IN DATABASE DEPENDING ON USER PREFERENCE.
#ERRORS: TRADE_NOT_FOUND_ERROR.
#CALLS UPDATE_TRADE_GRADE, UPDATE_TRADE_FIELD.
    def amend_journal_entry(self, trade_id: int, trade_changes):
        pass

main()