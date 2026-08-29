from datetime import date, datetime, time

import exceptions as t
import trade_calculator as y
from database import Database
from models import (
    Amendments,
    JournalEntry,
    Trade,
    TradeAsset,
    TradeChart,
    TradeDirection,
    TradeGrade,
    TradeNotes,
    TradeResult,
)
from validation import validate_trade_data


class Journal:

    def __init__(self, db: Database):
        self.db = db
 
    def record_trade(self, trade: Trade) -> Trade:
        """RECORDS A TRADE IN THE JOURNAL"""

        #1: ASSEMBLE/DERIVE TRADE DATA CALLER DOESN'T HAVE.
        trade = self._compute_derived_fields(trade)
        #AT THIS POINT TRADE.PARAMETERS_SUBMITTED = FALSE
        #SO MEANING WE CAN'T GRADE TRADE.
        #IT GETS TO THE DATABASE AS NONE FOR OVERRAL_TRADE_GRADE

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
    def attach_charts(self, chart: TradeChart):

        #TRADE_ID ISN'T BEING VERIFIED ANYWHERE
        #3: PERSIST TO DATABASE AND TRANSLATE FAILURES.
        try:
            chart_id = self.db.add_chart(chart)
            chart.chart_id = chart_id
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Chart_Upload_Error(f"TRADE_ID PROVIDED {chart.trade_id} DOESN'T EXIST: {e}") from e

        #4: RETURN SOMETHING MEANINGFUL.
        return chart
  
    def evaluate_trade(self, trade: Trade) -> dict:

        #3: GET POINTS DATA FROM RELEVANT TABLES USING IDENTIFIERS.
        #4: TRANSLATE THE ERRORS.
        try:
            entry_score = self.db.get_entry_execution_points(trade.entry_execution_id)
            management_score = self.db.get_trade_management_points(trade.management_id)
            trade_parameters = self.db.get_trade_parameters(trade.trade_id) # type: ignore
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
    
    def grade_trade(self, trade: Trade) -> Trade:

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
        #(POINTS, GRADE) -> (8, A), (6/7, A), (5, B), (4, C), (3, D) (<3, F)
        grading_system = [(8, TradeGrade.A), (7, TradeGrade.A), 
                          (6, TradeGrade.A), (5, TradeGrade.B), 
                          (4, TradeGrade.C), (3, TradeGrade.D), 
                          (2, TradeGrade.F), (1, TradeGrade.F), (0, TradeGrade.F)]
        for points, grade in grading_system:
            if trade_points == points:
                trade_grade = grade

        trade.overall_trade_grade = trade_grade # type: ignore
        #UPDATE THE GRADE OF THE TRADE FROM NONE TO TRADE_GRADE
        try:
            self.db.update_trade_grade(trade.trade_id, trade_grade) # type: ignore
        except t.Invalid_Grade_Error as e:
            raise t.Grading_Error(f"{trade_grade} IS INVALID. SHOULD BE BETWEEN (A - F), {e}") from e # type: ignore
        except t.Trade_Not_Found_Error as e:
            raise t.Grading_Error(f"{trade.trade_id} IS INVALID. PROVIDE VALID TRADE_ID, {e}") from e

        return trade

    def add_reflection_notes(self, trade_notes: TradeNotes) -> TradeNotes:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            self.db.add_trade_notes(trade_notes)
            self.db.commit()
        except t.Constraint_Violation_Error as e:
            self.db.rollback()
            raise t.Notes_Recording_Error(f"TRADE_ID {trade_notes.trade_id} IS INVALID, {e}") from e

        return trade_notes

    def get_trade(self, trade_id: int) -> Trade:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            trade = self.db.get_by_id(trade_id)
        except t.Trade_Not_Found_Error as e:
            raise t.Invalid_TradeID_Error(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}") from e

        return trade

    def get_all_trades(self) -> list[Trade]:

        try:
            trades = self.db.get_all_trade_rows()
            return trades
        except t.Empty_Trades_Table_Error as e:
            raise t.Trades_Not_Found_Error(f"EMPTY TRADES DATABASE TABLE: {e}")

#THE TRADER/USER WANTS TO SEE THE ENTIRE RECORDED JOURNAL ENTRY.
#METHOD NEEDS TO GET DATA FROM: TRADES, TRADE_PARAMETERS
#TRADE NOTES, CHARTS TABLE.
#METHOD NEEDS TO GET A LIST OF PARAMETERS NAMES FOR THE TRADE. 
    def get_journal_entry(self, trade_id: int) -> JournalEntry:
        """READ AN ENTIRE JOURNAL ENTRY FROM DATABASE AT ONCE."""

        try:
            trade = self.db.get_by_id(trade_id)
            trade_notes = self.db.get_trade_notes(trade_id)
            trade_charts = self.db.get_trade_charts(trade_id)
            parameter_ids = self.db.get_trade_parameters(trade_id)
            if parameter_ids:
                parameter_names = self.db.get_parameter_names(parameter_ids)
        except t.DatabaseError as e:
            raise t.Journal_Entry_Error(f"JOURNAL ENTRY CAN'T BE RETRIEVED DUE TO DATABASE ERRORS: {e}") from e

        return JournalEntry(
            trade= trade,
            charts= trade_charts,
            trade_notes= trade_notes,
            parameter_names= parameter_names, # type: ignore
        )

#RECORD_JOURNAL_ENTRY METHOD ISN'T BEING CALLED BY STREAMLIT UI
#THERE IS A BUG IN THE ADD_CHART DB CALL SINCE METHOD ASSUMES ATOMIC TRANSACTION
#CHARTS UPLOAD IS DONE IN BATCHES AND SO WE CAN HAVE 3/4 SUCCESSES
#MEANING CHART UPLOADS, COMMITS ARE DONE PER CHART.

#NOTE TO FUTURE SELF/DEVELOPER
#RECORD_JOURNAL_ENTRY METHOD WAS DELETED ON 30/8/2026.
#WITH THE GIVEN STREAMLIT CODE PATH, THERE IS NO USE FOR THE JOURNAL METHOD.
#IN THE FUTURE IF NEED ARISES, YOU CAN REWRITE IT.


    #ISSUE TO HANDLE: STREAMLIT DISPLAYS AND RETURNS THE COLUMN NAMES LIKE THIS : ENTRY PRICE
    #AMEND_TRADE_ENTRY METHOD IS WORKING WITH COLUMN NAMES LIKE THIS : entry_price
    #FIND OUT IF THIS MIGHT BE AN ISSUE: ENTRY PRICE != entry_price
    def amend_trade_entry(self, trade_id: int, amendment: Amendments) -> Trade:
        forbidden_columns = ["dollar_amount", "duration", "result", "rr_multiple", "overall_trade_grade"]
        if amendment.column_name in forbidden_columns:
            raise t.Invalid_Column_Name_Error(f"CAN'T AMEND COLUMN: {amendment.column_name}")

        recompute_values = {
            "entry_price" : self._compute_derived_fields,
            "exit_price" : self._compute_derived_fields,
            "take_profit" : self._compute_derived_fields,
            "stop_loss" : self._compute_derived_fields,
            "position_size" : self._compute_derived_fields,
            "entry_time" : self._compute_derived_fields,
            "exit_time" : self._compute_derived_fields,
            "date" : self._compute_derived_fields,
            "management_id" : self.grade_trade,
            "entry_execution_id" : self.grade_trade,
            "asset" : self._compute_derived_fields,
            "direction" : self._compute_derived_fields,
            "account_balance" : self._compute_derived_fields,
            "risk_percent" : self._compute_derived_fields,
        }

        #LOOK UP TABLE FOR TYPE CASTING OF NEW_VALUE GIVEN COLUMN_NAME
        column_types = {
            "entry_price": float,
            "exit_price": float,
            "take_profit": float,
            "stop_loss": float,
            "position_size": float,
            "entry_time": time,
            "exit_time": time,
            "date": date,
            "model_id": int,
            "account_id": int,
            "management_id": int,
            "entry_execution_id": int,
            "asset": TradeAsset,
            "direction": TradeDirection,
            "account_balance": float,
            "risk_percent": float,
        }
        #THE CASTING WON'T WORK FOR DATE/TIME VALUES.
        #STREAMLIT ALREADY RETURNS AS A DATETIME OBJECT.
        caster = column_types[amendment.column_name]
        typed_value = caster(amendment.new_value)
        amendment.new_value = typed_value

    #.GET() METHOD RETURNS NONE IF VALUE ISN'T IN THE DICTIONARY.
    #MEANING HAVING MODEL_ID, ACCOUNT_ID IN THE DICTIONARY IS REDUNDANT.
    #YOU STILL NEED TO CHECK FOR IF RECOMPUTE BECAUSE IT CAN STILL BE NONE.
        try:
            trade = self.db.get_by_id(trade_id)
            amendment.old_value = getattr(trade, amendment.column_name)
            setattr(trade, amendment.column_name, amendment.new_value)

            recompute_method = recompute_values.get(amendment.column_name)
            if recompute_method:
                recompute_method(trade)

            valid_trade = validate_trade_data(trade)
            self.db.update_trade_field(trade_id, amendment.column_name, amendment.new_value)
            amendment.amended_at = datetime.now()  # noqa: DTZ005
            amendment.amendment_id = self.db.add_trade_amendments(trade_id, amendment)
            self.db.commit()
        except t.DatabaseError as e:
            self.db.rollback()
            raise t.Trade_Recording_Error(f"COULDN'T RECORD NEW TRADE UPDATE: {e}") from e

        return valid_trade

    def finalize_grade(self, trade_id: int, parameter_names: list) -> Trade:

        #DB METHOD ISN'T WRAPPED IN TRY/EXCEPT BLOCK SINCE IT'S
        #CONDITIONALLY CALLED, IT'S A LOOK UP METHOD WITH NO RISKS
        #OFF DATABASEERRORS CONSULT THOUGH.
        if parameter_names:
            parameter_ids = self.db.get_parameter_ids(parameter_names)

        try:
            for parameter in parameter_ids: # type: ignore
                self.db.add_trade_parameters(trade_id, parameter)
            trade = self.db.get_by_id(trade_id)
            if trade.overall_trade_grade is None:
                graded_trade = self.grade_trade(trade)
            else:
                raise t.Grading_Error("GRADING ERROR: TRADE HAS ALREADY BEEN GRADED")
            self.db.commit()
        except t.DatabaseError as e:
            self.db.rollback()
            raise t.Grading_Error(f"ERROR FINALIZING GRADE: {e}")

        return graded_trade

#ADD JOURNAL METHOD FOR CREATING AN ACCOUNT
  