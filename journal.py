from datetime import datetime

import exceptions as t
import trade_calculator as y
from database import Database
from models import (
    Account,
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
from validation import validate_trade_data


class Journal:

    def __init__(self, db: Database):
        self.db = db

    def record_trade(self, trade: Trade) -> Trade:
        """RECORDS A TRADE IN THE JOURNAL"""

        #1: ASSEMBLE/DERIVE TRADE DATA CALLER DOESN'T HAVE.
        trade = self._compute_derived_fields(trade)
        #TRADE ISN'T GRADED AT THIS POINT BECAUSE TRADE PARAMETERS
        #MAY NOT HAVE BEEN SUBMITTED YET.
        #FINALIZE_GRADE() METHOD WILL HANDLE GRADING AND UPDATING OF OVERALL_TRADE_GRADE

        #2: VALIDATE THE TRADE DATA.
        valid_trade = validate_trade_data(trade)

        #3: PERSIST TO THE DATABASE & #4: TRANSLATE THE ERRORS.
        try:
            trade_id = self.db.save_trade(valid_trade)
            trade.trade_id = trade_id
            self.db.commit()
        except t.DatabaseError as e:
            self.db.rollback()
            raise t.TradeRecordingError(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e

        #5: RETURN SOMETHING MEANINGFUL.
        return trade

#DOLLAR_AMOUNT, RESULT, RR_MULTIPLE, DURATION ARE DERIVED.
    def _compute_derived_fields(self, trade: Trade) -> Trade:
        """COMPUTES DERIVED FIELDS USING THE CALCULATOR MODULE."""

        setup = self._convert_to_trade_setup(trade)

        results = y.calculate_profit_loss(setup)
        dollar_amount = results["DOLLAR_AMOUNT"]
        trade.dollar_amount = dollar_amount
        result = results["RESULT"]
        if result == "PROFIT":
            result = TradeResult.PROFIT
        elif result == "LOSS":
            result = TradeResult.LOSS

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

        live_account_balance = self.db.get_current_account_balance(trade.account_id) # type: ignore
        setup = TradeSetup(
            entry_price= trade.entry_price,
            exit_price= trade.exit_price,
            stop_loss= trade.stop_loss,
            take_profit= trade.take_profit,
            asset= trade.asset,
            direction= trade.direction,
            position_size= trade.position_size,
            account_balance= live_account_balance,
            entry_time= trade.entry_time,
            exit_time= trade.exit_time,
            date= trade.date
        )

        return setup

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
        except t.ConstraintViolationError as e:
            self.db.rollback()
            raise t.ChartUploadError(f"TRADE_ID PROVIDED {chart.trade_id} DOESN'T EXIST: {e}") from e

        #4: RETURN SOMETHING MEANINGFUL.
        return chart

    def evaluate_trade(self, trade: Trade) -> dict:

        #3: GET POINTS DATA FROM RELEVANT TABLES USING IDENTIFIERS.
        #4: TRANSLATE THE ERRORS.
        try:
            entry_score = self.db.get_entry_execution_points(trade.entry_execution_id)
            management_score = self.db.get_trade_management_points(trade.management_id)
            trade_parameters = self.db.get_trade_parameters(trade.trade_id) # type: ignore
        except t.InvalidIdentifierError as e:
            raise t.GradingError(f"PROVIDED IDs ARE INVALID: {e}") from e
        except t.TradeNotFoundError as e:
            raise t.GradingError(f"TRADE_ID {trade.trade_id} IS INVALID: {e}") from e

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
        except t.InvalidGradeError as e:
            raise t.GradingError(f"{trade_grade} IS INVALID. SHOULD BE BETWEEN (A - F), {e}") from e # type: ignore
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"{trade.trade_id} IS INVALID. PROVIDE VALID TRADE_ID, {e}") from e

        return trade

    def add_reflection_notes(self, trade_notes: TradeNotes) -> TradeNotes:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            self.db.add_trade_notes(trade_notes)
            self.db.commit()
        except t.ConstraintViolationError as e:
            self.db.rollback()
            raise t.NotesRecordingError(f"TRADE_ID {trade_notes.trade_id} IS INVALID, {e}") from e

        return trade_notes

    def get_trade(self, trade_id: int) -> Trade:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            trade = self.db.get_by_id(trade_id)
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}") from e

        return trade

    def get_all_trades(self) -> list[Trade]:

        try:
            trades = self.db.get_all_trade_rows()
            return trades
        except t.EmptyTradesTableError as e:
            raise t.TradesNotFoundError(f"EMPTY TRADES DATABASE TABLE: {e}") from e

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
            raise t.JournalEntryError(f"JOURNAL ENTRY CAN'T BE RETRIEVED DUE TO DATABASE ERRORS: {e}") from e

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

    def amend_trade_entry(self, trade_id: int, amendment: Amendments) -> Amendments:
        forbidden_columns = ["dollar_amount", "duration", "result", "rr_multiple", "overall_trade_grade", "risk_percent"]
        if amendment.column_name in forbidden_columns:
            raise t.InvalidColumnNameError(f"CAN'T AMEND COLUMN: {amendment.column_name}")

        recompute_values = {
            "entry_price" : self._compute_derived_fields,
            "exit_price" : self._compute_derived_fields,
            "take_profit" : self._compute_derived_fields,
            "stop_loss" : self._compute_derived_fields,
            "position_size" : self._compute_derived_fields,
            "management_id" : self.grade_trade,
            "entry_execution_id" : self.grade_trade,
            "asset" : self._compute_derived_fields,
            "direction" : self._compute_derived_fields,
        }

        #LOOK UP TABLE FOR TYPE CASTING OF NEW_VALUE GIVEN COLUMN_NAME

        try:
            column_types = {
                "entry_price": float,
                "exit_price": float,
                "take_profit": float,
                "stop_loss": float,
                "position_size": float,
                "model_id": int,
                "account_id": int,
                "management_id": int,
                "entry_execution_id": int,
                "asset": TradeAsset,
                "direction": TradeDirection,
            }

            caster = column_types[amendment.column_name]
            typed_value = caster(amendment.new_value)
            amendment.new_value = typed_value
        except (KeyError, ValueError):
            raise t.TradeValidationError("TRADE VALIDATION FAILED")

        try:
            trade = self.db.get_by_id(trade_id)
            amendment.old_value = getattr(trade, amendment.column_name)
            setattr(trade, amendment.column_name, amendment.new_value)

            recompute_method = recompute_values.get(amendment.column_name)
            if recompute_method:
                recompute_method(trade)

            #MAJOR BUG IN THE CODE: NONE OF THE RECOMPUTED VALUES ARE STORED BACK TO THE DATABASE.
            #ONLY THE AMENDED COLUMN IS STORED IN THE DATABASE. THE RECOMPUTES GO STALE.
            valid_trade = validate_trade_data(trade)
            self.db.update_trade_field(valid_trade.trade_id, amendment.column_name, amendment.new_value) # type: ignore
            amendment.amended_at = datetime.now()
            amendment.amendment_id = self.db.add_trade_amendments(trade_id, amendment)
            self.db.commit()
        except t.TradeNotFoundError as e:
            self.db.rollback()
            raise t.InvalidTradeIDError(f"TRADE WITH THAT ID DOESN'T EXIST: {e}")
        except t.ConstraintViolationError as e:
            self.db.rollback()
            raise t.TradeRecordingError(f"COULDN'T RECORD NEW TRADE UPDATE: {e}") from e

        return amendment

    def finalize_grade(self, trade_id: int, parameter_names: list) -> Trade:

        if parameter_names:
            parameter_ids = self.db.get_parameter_ids(parameter_names)
        else:
            parameter_ids = []

        #TRADE IS ALREADY GRADED AND CLIENT RESUBMITS SAME PARENTERS. = INTERNAL
        #TRADE_ID DOESN'T EXIST, FK CONSTRAINT FAILS == INTERNAL
        try:
            trade = self.db.get_by_id(trade_id)
            if trade.overall_trade_grade is None:
                graded_trade = self.grade_trade(trade)
            else:
                raise t.TradeAlreadyGradedError("GRADING ERROR: TRADE HAS ALREADY BEEN GRADED")
            for parameter in parameter_ids: # type: ignore
                self.db.add_trade_parameters(trade_id, parameter)
            self.db.commit()
        except t.ConstraintViolationError as e:
            self.db.rollback()
            raise t.ParametersJunctionTableConflict(f"PARAMETERS VIOLATE JUNCTION TABLE JOINT PK CONSTRAINT: {e}") from e
        except t.TradeNotFoundError:
            self.db.rollback()
            raise t.InvalidTradeIDError("PROVIDED TRADE_ID IS INVALID")

        return graded_trade

    def register_trading_account(self, account: Account) -> Account:

        try:
            account_id = self.db.create_trading_account(account)
            account.account_id = account_id
        except t.ConstraintViolationError as e:
            raise t.AccountCreationError(f"ACCOUNT COULDN'T BE CREATED DUE TO DB ERROR: {e}") from e

        return account

    def fetch_all_trading_accounts(self) -> list[Account]:

        try:
            accounts: list[Account] = self.db.get_trading_accounts()
        except t.EmptyAccountsTableError as e:
            raise t.AccountsNotFoundError(f"ERROR! EMPTY ACCOUNTS TABLE: {e}") from e

        return accounts

    def delete_trading_account(self, account_id: int) -> None:
        try:
            self.db.delete_account_from_db(account_id)
        except t.InvalidAccountError:
            raise t.AccountNotFoundError("INVALID ACCOUNT_ID. NO ACCOUNT MATCHES!")

    def fetch_trade_notes(self, trade_id: int):

        try:
            notes = self.db.get_trade_notes(trade_id)
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}") from e

        return notes

    def fetch_present_parameters(self, trade_id: int):
        #CHECK TO SEE IF THE TRADE_ID EXISTS.
        #TRADE CAN HAVE ZERO PARAMETERS ATTACHED TO IT. FIX THIS

        try:
            parameter_ids = self.db.get_trade_parameters(trade_id)
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}") from e

        if parameter_ids:
            parameter_names: list[str] = self.db.get_parameter_names(parameter_ids)

        return parameter_names  # type: ignore POSSIBLY UNBOUND

    def delete_trade_entry(self, trade_id: int) -> None:

        try:
            self.db.delete_trade(trade_id)
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"NO TRADE MATCHES THIS TRADEID {trade_id}, {e}")

    def update_trading_notes(self, trade_notes: TradeNotes) -> None:

        try:
            self.db.update_trading_notes(trade_notes)
        except t.TradeNotFoundError as e:
            raise t.InvalidTradeIDError(f"TRADE NOT FOUND: {e}") from e

    def fetch_models_list(self) -> list[TradingModel]:
        return self.db.get_models_list()

    def fetch_entry_executions_list(self) -> list[EntryExecution]:
        return self.db.get_entry_executions_list()

    def fetch_trade_management_lists(self) -> list[TradeManagement]:
        return self.db.get_trade_managements_list()

    def fetch_parameters_list(self) -> list[Parameter]:
        return self.db.get_parameters_list()
