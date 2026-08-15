import exceptions as t
import trade_calculator as y
from database import Database
from models import (
    Amendments,
    JournalEntry,
    Trade,
    TradeChart,
    TradeNotes,
    TradeResult,
)
from seed_data import trade1
from validation import validate_trade_data


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
        except t.DatabaseError as e:
            self.db.rollback()
            raise t.Trade_Recording_Error(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e

        #5: RETURN SOMETHING MEANINGFUL.
        return trade

#DOLLAR_AMOUNT, RESULT, RR_MULTIPLE, DURATION ARE DERIVED.
    def _compute_derived_fields(self, trade: Trade) -> Trade:
        """COMPUTES DERIVED FIELDS USING THE CALCULATOR MODULE."""

        results = y.calculate_profit_loss(trade)
        dollar_amount = results["DOLLAR_AMOUNT"]
        trade.dollar_amount = dollar_amount
        result = results["RESULT"]
        if result == "PROFIT":
            result = TradeResult.PROFIT
        elif result == "LOSS":
            result = TradeResult.LOSS

        trade.result = result
        
        values = y.calculate_risk_reward_multiple(trade)
        rr_multiple = values["RR_MULTIPLE"]
        trade.rr_multiple = rr_multiple
        duration = y.calculate_trade_duration(trade)
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
    
    def grade_trade(self, trade: Trade) -> None:

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

        #RETURN NONE.
        #CALLER DOESNT NEED THE NEW GRADE BECAUSE METHOD ALREADY UPDATES THE NEW TRADE
        #TO THE TRADE BY CALLING UPDATE_TRADE_GRADE INTERNALLY.

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

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            self.db.add_trade_notes(trade_id, trade_notes)
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Notes_Recording_Error(f"TRADE_ID {trade_id} IS INVALID, {e}") from e

        return trade_notes

    def get_trade(self, trade_id: int) -> Trade:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
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

        try:
            trade = self.db.get_by_id(trade_id)
            valid_trade = validate_trade_data(trade)
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


    def amend_trade_entry(self, trade_id: int, amendment: Amendments) -> Trade:
        forbidden_columns = ["dollar_amount", "duration", "result", "rr_multiple", "overall_trade_grade"]
        if amendment.column_name in forbidden_columns:
            raise t.Invalid_Column_Name_Error(f"CAN'T AMEND COLUMN: {amendment.column_name}")

        trade_columns = [
            #(column_name, category)
            ("entry_price", 1),
            ("exit_price", 1),
            ("stop_loss", 1),
            ("take_profit", 1),
            ("position_size", 1),
            ("entry_time", 1),
            ("exit_time", 1),
            ("date", 1),
            ("model_id", 3),
            ("account_id", 3),
            ("management_id", 2),
            ("entry_execution_id", 2),
            ("asset", 1),
            ("direction", 1),
            ("account_balance", 1),
            ("risk_percent", 1),
        ]

        for column_name, category in trade_columns:
            try:
                trade = self.db.get_by_id(trade_id)
                amended_trade = setattr(trade, amendment.column_name, amendment.new_value)

                if amendment.column_name == column_name and category == 1:
                    trade = self._compute_derived_fields(amended_trade)
                elif amendment.column_name == column_name and category == 2:
                    self.grade_trade(amended_trade)
                else:
                    continue

                valid_trade = validate_trade_data(amended_trade)
                self.db.update_trade_field(trade_id, amendment.column_name, amendment.new_value)
                amendment_id = self.db.add_trade_amendments(trade_id, amendment)
                amendment.amendment_id = amendment_id
                self.db.commit()
            except t.DatabaseError as e:
                self.db.rollback()
                raise t.Trade_Recording_Error(f"COULDN'T RECORD NEW TRADE UPDATE: {e}") from e

        return valid_trade
  
if __name__ == "__main__":
    main()