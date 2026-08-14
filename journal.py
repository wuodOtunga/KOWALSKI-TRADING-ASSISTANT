from datetime import date, datetime, time

import exceptions as t
import trade_calculator as y
from database import Database
from models import (
    JournalEntry,
    Trade,
    TradeAmendments,
    TradeChart,
    TradeNotes,
    TradeResult,
)
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
        trade_grade = self.grade_trade(trade)
        trade.overall_trade_grade = trade_grade
        #2: VALIDATE THE TRADE DATA.
        valid_trade = validate_trade_data(trade)

        #3: PERSIST TO THE DATABASE & #4: TRANSLATE THE ERRORS.
        try:
            trade_id = self.db.save_trade(valid_trade)
            trade.trade_id = trade_id
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e
        except t.Invalid_Identifier_Error as e:
            self.db.rollback()
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e

        #5: RETURN SOMETHING MEANINGFUL.
        return trade

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
            charts.chart_id = chart_id
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Chart_Upload_Error(f"TRADE_ID PROVIDED {trade_id} DOESN'T EXIST: {e}") from e

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
            trade_parameters = self.db.get_trade_parameters(trade.trade_id)
        except t.Invalid_Identifier_Error as e:
            raise t.Grading_Error(f"PROVIDED IDs ARE INVALID: {e}") from e
        except t.Trade_Not_Found_Error as e:
            raise t.Grading_Error(f"TRADE_ID {trade.trade_id} IS INVALID: {e}") from e

        parameters_score = len(trade_parameters)
        #5. RETURN SOMETHING MEANINGFUL.
        return {
            "entry_score" : entry_score,
            "management_score" : management_score,
            "parameters_score" : parameters_score,
        }
    
    def grade_trade(self, trade: Trade) -> str:

        #CALCULATE TRADE_POINTS.
        #TRADE_POINTS == POINTS SCORED ON MODEL CHECKLIST.
        grading_points = self.evaluate_trade(trade)
        entry_score = grading_points["entry_score"]
        management_score = grading_points["management_score"]
        parameters_score = grading_points["parameters_score"]

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
            self.db.commit()
        except t.Invalid_Grade_Error as e:
            self.db.rollback()
            raise t.Grading_Error(f"{trade_grade} IS INVALID. SHOULD BE BETWEEN (A+ - F), {e}") from e
        except t.Trade_Not_Found_Error as e:
            self.db.rollback()
            raise t.Grading_Error(f"{trade.trade_id} IS INVALID. PROVIDE VALID TRADE_ID, {e}") from e

        #RETURN SOMETHING MEANINGFUL.
        #RETURN GRADE FOR ANYONE WHO NEEDS IT.
        return trade_grade

#I WANT TO FORMALIZE WHAT TRADE NOTES MEANS FOR UNIFORMITY ACROSS TRADES.
#TRADE NOTES INCLUDE: EMOTIONS, MISTAKES, LESSONS, NOTES.
#NOTES INCLUDE: NOTES ON THE GRADE OF TRADE, NOTES ON MODEL USED,
#NOTES ON ENTRY EXECUTION AND TRADE MANAGEMENT,
#NOTES ON ENTRY AND EXIT RATIONALE,
#NOTES ON TRADE PARAMETERS PRESENT AND ABSENT,
#NOTES ON EMOTIONS, MISTAKES MADE, LESSONS LEARNT.
#INSIDE STREAMLIT MODULE, VALIDATE THE ABOVE IS WHAT IS BEING RECORDED.
    def add_reflection_notes(self, trade_id: int, trade_notes: TradeNotes) -> TradeNotes:

        #TRADE_NOTES OBJECT IS SUPPLIED BY STREAMLIT MODULE. (CALLER)
        #NO ASSEMBLY/DERIVING TRADE_NOTES OBJECT, ARRIVES AS CLEAN TRUSTED OBJECT.
        #WHAT HAPPENS IF THIS METHOD ISN'T CALLED FROM THE STREAMLIT UI?
        #SCHEMA.SQL HAS NOT NULL CONSTRAINTS THAT RAISE INTEGRITYERROR.
        #DATABASE.PY CATCHES THE SQLITE ERRORS AND TRANSLATES. JOURNAL.PY ALSO TRANSLATES.
        try:
            self.db.add_trade_notes(trade_id, trade_notes)
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Notes_Recording_Error(f"TRADE_ID {trade_id} IS INVALID, {e}") from e

        return trade_notes

#THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
#DO I NEED TO VALIDATE THAT THE RETURNED TRADE HAS CORRECT TYPES?
#DON'T CATCH VALIDATION ERROR IN EXCEPT BLOCK SINCE DOESN'T NEED TRANSLATION
#OR ADDITIONAL INFO. LET IT PROPAGATE UP INTO STREAMLIT MODULE.
    def get_trade(self, trade_id: int) -> Trade:

        try:
            trade = self.db.get_by_id(trade_id)
            valid_trade = validate_trade_data(trade)
        except t.Trade_Not_Found_Error as e:
            raise t.Invalid_TradeID_Error(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}") from e

        return valid_trade

#THE TRADER/USER WANTS TO SEE THE ENTIRE RECORDED JOURNAL ENTRY.
#METHOD NEEDS TO GET DATA FROM: TRADES, ACCOUNTS, TRADE_PARAMETERS
#TRADE NOTES, CHARTS TABLE.
#METHOD NEEDS TO GET A LIST OF PARAMETERS IDS FOR THE TRADE. 
    def get_journal_entry(self, trade_id: int) -> JournalEntry:
        """READ AN ENTIRE JOURNAL ENTRY FROM DATABASE AT ONCE."""

        trade = self.db.get_by_id(trade_id)
        valid_trade = validate_trade_data(trade)

        try:
            account = self.db.get_trading_account(valid_trade)
            trade_notes = self.db.get_trade_notes(trade_id)
            trade_charts = self.db.get_trade_charts(trade_id)
            parameter_ids = self.db.get_trade_parameters(trade_id)
        except t.DatabaseError as e:
            raise t.Journal_Entry_Error(f"JOURNAL ENTRY CAN'T BE RETRIEVED DUE TO DATABASE ERRORS: {e}") from e

        return JournalEntry(
            trade= trade,
            account= account,
            charts= trade_charts,
            trade_notes= trade_notes,
            parameter_ids= parameter_ids,
        )

#TARGET TABLES: TRADES, ACCOUNTS, TRADE_PARAMETERS, TRADE_NOTES, CHARTS.
#INPUTS: DATACLASS OBJECTS AND A LIST OF PARAMETER IDS.
#DATACLASS OBJECTS INCLUDE: TRADE, ACCOUNT, TRADE_NOTE, TRADE_CHARTS.
#LIST OF PARAMETER IDS IS PROVIDED BY THE CALLER.
#OUTPUT: ENTIRE JOURNAL ENTRY. JOURNALENTRY DATACLASS.
#CAN A DATACLASS CONTAIN OTHER DATACLASSES AS VALUE TYPES?
    def record_journal_entry(self, journal_entry: JournalEntry) -> JournalEntry:
        """SAVE AN ENTIRE JOURNAL ENTRY TO DATABASE AT ONCE."""

        #STEP 1:ASSEMBLE/DERIVE DATA CALLER DOESN'T HAVE.
        #TRADE HAS DERIVED FIELDS, OTHER OBJECTS COME FULLY FORMED FROM CALLER.
        trade = self._compute_derived_fields(journal_entry.trade)
        trade_grade = self.grade_trade(trade)
        journal_entry.trade.overall_trade_grade = trade_grade

        #STEP 2: VALIDATE THE DATA.
        valid_trade = validate_trade_data(trade)

        #STEP 3: PERSIST TO DB. STEP 4:TRANSLATE ERRORS.
        #NOTICE WE ARE CATCHING THE BROAD DATABASE ERROR.
        #BECAUSE IT COVERS ALL THE SUB CLASSES OF ERRORS RAISED BY INDIVIDUAL METHOD RUNS.
        try:
            account_id = self.db.create_trading_account(journal_entry.account)
            journal_entry.trade.account_id = account_id
            trade_id = self.db.save_trade(valid_trade)
            journal_entry.trade.trade_id = trade_id
            chart_id = self.db.add_chart(journal_entry.trade.trade_id, journal_entry.charts)
            journal_entry.charts.chart_id = chart_id
            self.db.add_trade_notes(journal_entry.trade.trade_id, journal_entry.trade_notes)

            for parameter_id in journal_entry.parameter_ids:
                self.db.add_trade_parameters(journal_entry.trade.trade_id, parameter_id)

            self.db.commit()
        except t.DatabaseError as e:
            self.db.rollback()
            raise t.Journal_Entry_Error(f"JOURNAL ENTRY NOT SAVED DUE TO DATABASE ERRORS: {e}") from e

        #STEP 5: RETURN SOMETHING MEANINGFUL.
        return journal_entry

    def amend_trade_entry(self, trade_id: int, column: str, value):
        #AMENDED FIELDS: EVERYTHING IN THE TRADE OBJECT EXCEPT COMPUTED FIELDS.
        #CATEGORIES OF TRADE OBJECT FIELDS TO BE AMENDED.
        #CATEGORY #1:
        #ENTRY_PRICE, EXIT_PRICE, TAKE_PROFIT, STOP_LOSS, POSITION_SIZE, DATE
        #ENTRY_TIME, EXIT_TIME, ASSET, DIRECTION, ACCOUNT_ID

        #CATEGORY #2:
        #MANAGEMENT_ID, ENTRY_EXECUTION_ID
        #CATEGORY #3: MODEL_ID, ACCOUNT_ID. DOESN'T AFFECT ANYTHING.

        #DERIVED/COMPUTED TRADE FIELDS CAN'T BE MANUALLY AMENDED.
        FORBIDDEN_COLUMNS = ["dollar_amount", "duration", "result", "rr_multiple", "overall_trade_grade"]
        if column in FORBIDDEN_COLUMNS:
            raise t.Invalid_Column_Name_Error(f"CAN'T UPDATE COLUMN NAME {column}.")

        #TRADE COLUMNS DIVIDED INTO THREE CATEGORIES.
        #CATEGORY #1 AFFECTS COMPUTED/DERIVED FIELDS FROM CALCULATOR MODULE.
        #CATEGORY #2 AFFECTS GRADE OF THE TRADE.
        #CATEGORY #3 AFFECTS NOTHING.
        category_one = [
            "entry_price", "exit_price", "take_profit", "stop_loss", "position_size",
            "date", "entry_time", "exit_time", "asset", "direction"
        ]

        category_two = ["management_id", "entry_execution_id"]

        #ASSEMBLE/DERIVE OLD, NEW VALUE AND WHEN CHANGE HAPPENED.
        amended_trade = self.db.get_by_id(trade_id)
        trade = self._compute_derived_fields(amended_trade)
        valid_trade = validate_trade_data(trade)

        if column in category_one:
            old_value = amended_trade[column]
            new_value = value

            amendment = TradeAmendments(
                trade_id= trade_id,
                column_name= column,
                old_value= old_value,
                new_value= new_value,
                amended_at= datetime.now()  # noqa: DTZ005
            )

        #VALIDATE TRADE OBJECT, PERSIST THE DATA AND TRANSLATE FAILURES.
            try:
                amendment_id = self.db.add_trade_amendments(trade_id, amendment)
                amendment.ammendment_id = amendment_id
                trade_id = self.db.save_trade(valid_trade)
                valid_trade.trade_id = trade_id
                self.db.commit()
            except t.DatabaseError as e:
                self.db.rollback()
                raise t.Journal_Entry_Error(f"TRADE ENTRY COULDN'T BE AMENDED: {e}") from e

        if column in category_two:
            self.evaluate_trade(valid_trade)
            new_grade = self.grade_trade(valid_trade)

            amendment = TradeAmendments(
                trade_id= trade_id,
                column_name= column,
                old_value= valid_trade.overall_trade_grade,
                new_value= new_grade,
                amended_at= datetime.now()  # noqa: DTZ005
            )

            try:
                amendment_id = self.db.add_trade_amendments(trade_id, amendment)
                amendment.ammendment_id = amendment_id
                self.db.commit()
            except t.Constraint_Violation_Error as e:
                raise t.Journal_Entry_Error(f"TRADE ENTRY COULDN'T BE AMENDED: {e}") from e

        #RETURN SOMETHING MEANINGFUL.
        return amendment
main()