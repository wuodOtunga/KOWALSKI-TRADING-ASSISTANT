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
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e
        except t.Invalid_Identifier_Error as e:
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e

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
            raise t.Chart_Upload_Error(f"TRADE_ID PROVIDED {trade_id} DOESN'T EXIST: {e}") from e

        charts.chart_id = chart_id

        #4: RETURN SOMETHING MEANINGFUL.
        return charts

#DID YOU SPECIFY WHICH PROVIDED ID IS INVALID.
#DOES from e OFFER CONTEXT ON WHICH ID DOESN'T EXIST?
#DOES THE TRADE OBJECT GET TO THIS METHOD AS CLEAN DATA?
#THERE IS NO VALIDATION/ASSEMBLE/DERIVE TO BE DONE HERE.  
    def evaluate_trade(self, trade: Trade) -> int:

        #3: GET POINTS DATA FROM RELEVANT TABLES USING IDENTIFIERS.
        #4: TRANSLATE THE ERRORS.
        try:
            entry_score = self.db.get_entry_execution_points(trade.entry_execution_id)
            management_score = self.db.get_trade_management_points(trade.management_id)
            parameters_score = self.db.get_parameters_points(trade.trade_id)
        except t.Invalid_Identifier_Error as e:
            raise t.Grading_Error(f"PROVIDED IDs ARE INVALID: {e}") from e
        except t.Trade_Not_Found_Error as e:
            raise t.Grading_Error(f"TRADE_ID {trade.trade_id} IS INVALID: {e}") from e
        
        #5. RETURN SOMETHING MEANINGFUL.
        return entry_score, management_score, parameters_score

#HOW DOES TUPLE UNPACKING WORKING.
    def grade_trade(self, trade: Trade):

        #CALCULATE TRADE_POINTS.
        #TRADE_POINTS == POINTS SCORED ON MODEL CHECKLIST.
        entry_score, management_score, parameters_score = self.evaluate_trade(trade)
        trade_execution_average = (entry_score + management_score)/2
        if trade_execution_average >= 4:
            trade_points = parameters_score + 1
        else:
            trade_points = parameters_score

        #GRADING OF TRADE BASED ON TRADE_POINTS.
        #(POINTS, GRADE) -> (8, A+), (6/7, A), (5, B), (4, C), (3, D) (<3, F)
        grading_system = [(8, "A+"), (7, "A"), (6, "A"), (5, "B"), (4, "C"), (3, "D"), (2, "F"), (1, "F"), (0, "F")]
        for points, grade in grading_system:
            if trade_points == points:
                trade_grade = grade

        #UPDATE THE GRADE OF THE TRADE FROM NONE TO TRADE_GRADE
        try:
            self.db.update_trade_grade(trade.trade_id, trade_grade)
        except t.Invalid_Grade_Error as e:
            raise t.Grading_Error(f"{trade_grade} IS INVALID. SHOULD BE BETWEEN (A+ - F), {e}") from e
        except t.Trade_Not_Found_Error as e:
            raise t.Grading_Error(f"{trade.trade_id} IS INVALID. PROVIDE VALID TRADE_ID, {e}") from e

        #RETURN SOMETHING MEANINGFUL.
        #RETURN GRADE FOR ANYONE WHO NEEDS IT.
        return trade_grade

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