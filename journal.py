from datetime import datetime
from typing import get_args

import exceptions as t
import trade_calculator as y
from models import (
    Account,
    AmendableColumns,
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
from repository import Repository
from validation import validate_trade_data


class Journal:

    def __init__(self, db: Repository):
        self.db: Repository = db

    #A) SINGLE WRITE METHOD
    def record_trade(self, trade: Trade) -> Trade:
        """RECORDS A TRADE IN THE JOURNAL"""

        #1: ASSEMBLE/DERIVE TRADE DATA CALLER DOESN'T HAVE.
        trade = self._compute_derived_fields(trade)
        #TRADE ISN'T GRADED AT THIS POINT BECAUSE TRADE PARAMETERS
        #MAY NOT HAVE BEEN SUBMITTED YET.
        #FINALIZE_GRADE() METHOD WILL HANDLE GRADING AND UPDATING OF OVERALL_TRADE_GRADE

        #2: VALIDATE THE TRADE DATA.
        valid_trade: Trade = validate_trade_data(trade)

        #3: PERSIST TO THE DATABASE & #4: TRANSLATE THE ERRORS.
        try:
            trade_id: int = self.db.save_trade(trade=valid_trade)
            trade.trade_id = trade_id
        except t.ConstraintViolationError as e:
            raise t.TradeRecordingError(f"TRADE NOT SAVED DUE TO POSSIBLE ERROR: {e}") from e

        #5: RETURN SOMETHING MEANINGFUL.
        return trade


#DOLLAR_AMOUNT, RESULT, RR_MULTIPLE, DURATION ARE DERIVED.
    def _compute_derived_fields(self, trade: Trade) -> Trade:
        """COMPUTES DERIVED FIELDS USING THE CALCULATOR MODULE."""

        setup: TradeSetup = self._convert_to_trade_setup(trade)

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

        live_account_balance = self.db.get_current_account_balance(trade.account_id) # pyright: ignore[reportArgumentType]
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
    def attach_charts(self, chart: TradeChart) -> TradeChart:

        #TRADE_ID ISN'T BEING VERIFIED ANYWHERE
        #3: PERSIST TO DATABASE AND TRANSLATE FAILURES.
        try:
            chart_id = self.db.add_chart(chart)
            chart.chart_id = chart_id
        except t.ConstraintViolationError as e:
            raise t.ChartUploadError(f"CONSTRAINT VIOLATION ERROR DETECTED {e}") from e

        #4: RETURN SOMETHING MEANINGFUL.
        return chart

    def evaluate_trade(self, trade: Trade) -> dict:

        #3: GET POINTS DATA FROM RELEVANT TABLES USING IDENTIFIERS.
        #4: TRANSLATE THE ERRORS.
        try:
            entry_score = self.db.get_entry_execution_points(trade.entry_execution_id)
            management_score = self.db.get_trade_management_points(trade.management_id)
            trade_parameters = self.db.get_trade_parameters(trade.trade_id) # pyright: ignore[reportArgumentType]
        except t.InvalidIdentifierError as e:
            raise t.NotFoundError(f"PROVIDED IDs ARE INVALID: {e}") from e

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
        cut_off = 4
        grading_points = self.evaluate_trade(trade)
        entry_score = grading_points["entry_score"]
        management_score = grading_points["management_score"]
        parameters_score = grading_points["parameters_score"]

        trade_execution_average = (entry_score + management_score)/2
        trade_points = parameters_score + 1 if trade_execution_average >= cut_off else parameters_score

        #GRADING OF TRADE BASED ON TRADE_POINTS.
        #(POINTS, GRADE) -> (8, A), (6/7, A), (5, B), (4, C), (3, D) (<3, F)
        grading_system: list[tuple[int, TradeGrade]] = [
            (8, TradeGrade.A), (7, TradeGrade.A),
            (6, TradeGrade.A), (5, TradeGrade.B),
            (4, TradeGrade.C), (3, TradeGrade.D),
            (2, TradeGrade.F), (1, TradeGrade.F), (0, TradeGrade.F)]

        for points, grade in grading_system:
            if trade_points == points:
                trade.overall_trade_grade = grade

        #trade_grade is possibly unbound
        #UnboundLocalError: cannot access local variable 'trade_grade'
        #where it is not associated with a value
        #UPDATE THE GRADE OF THE TRADE FROM NONE TO TRADE_GRADE
        self.db.update_trade_grade(
            trade_id=trade.trade_id, new_grade=trade.overall_trade_grade) # pyright: ignore[reportArgumentType]

        return trade

    def add_reflection_notes(self, trade_notes: TradeNotes) -> TradeNotes:

        #THIN WRAPPER METHOD, ONLY SERVES TO TRANSLATES ERRORS.
        try:
            self.db.add_trade_notes(notes=trade_notes)
        except t.ConstraintViolationError as e:
            raise t.NotesRecordingError(
                f"TRADE_ID MUST BE UNIQUE AND ALL INPUTS ARE REQUIRED: {e}") from e

        return trade_notes

    def get_trade(self, trade_id: int) -> Trade:

        return self.db.get_by_id(trade_id)

    def fetch_all_trades(self) -> list[Trade]:
        return self.db.get_all_trades()

    def get_journal_entry(self, trade_id: int) -> JournalEntry:
        """READ AN ENTIRE JOURNAL ENTRY FROM DATABASE AT ONCE."""

        ##DOES THIS NEED TO BE AN ATOMIC TRANSACTION??
        #SOME TRADES MIGHT HAVE SOME CHILDREN MISSING BUT WE STILL WANT TO
        #DISPLAY WHATEVER IS AVAILABLE.
        #THIS COULD ALSO BE A QUICK WAY TO TELL WHICH TRADES LACKS WHAT??

        #throws TradeNotFoundError when id is invalid
        trade: Trade = self.db.get_by_id(trade_id)

        #throws NotesNotFoundError when notes are missing
        trade_notes: TradeNotes = self.db.get_trade_notes(trade_id)

        #throws TradeNotFoundError when trade is invalid
        #trade_id is a FK on the table so chances of trade missing is low.
        #if trade is deleted, charts also deleted. cascade delete set
        #return empty list when charts don't exist.
        trade_charts: list[TradeChart] = self.db.get_trade_charts(trade_id)

        #throws TradeNotFoundError when trade is invalid.
        #trade_id is a FK & PKon the table so chances of trade missing is low.
        #return empty list when parameters don't exist in the junction table.
        parameter_ids: list[int] = self.db.get_trade_parameters(trade_id)

        if parameter_ids:
            parameter_names: list[str] = self.db.get_parameter_names(parameter_ids)

        return JournalEntry(
            trade= trade,
            charts= trade_charts,
            trade_notes= trade_notes,
            parameter_names= parameter_names, # pyright: ignore[reportPossiblyUnboundVariable]
        )

#RECORD_JOURNAL_ENTRY METHOD ISN'T BEING CALLED BY STREAMLIT UI
#THERE IS A BUG IN THE ADD_CHART DB CALL SINCE METHOD ASSUMES ATOMIC TRANSACTION
#CHARTS UPLOAD IS DONE IN BATCHES AND SO WE CAN HAVE 3/4 SUCCESSES
#MEANING CHART UPLOADS, COMMITS ARE DONE PER CHART.

#NOTE TO FUTURE SELF/DEVELOPER
#RECORD_JOURNAL_ENTRY METHOD WAS DELETED ON 30/8/2026.
#WITH THE GIVEN STREAMLIT CODE PATH, THERE IS NO USE FOR THE JOURNAL METHOD.
#IN THE FUTURE IF NEED ARISES, YOU CAN REWRITE IT.

    def amend_trade_entry(self, amendment: Amendments) -> Amendments:
        if amendment.column_name not in get_args(AmendableColumns):
            raise t.ConflictError(f"CAN'T AMEND COLUMN: {amendment.column_name}")

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
        except (KeyError, ValueError) as e:
            raise t.TradeValidationError("TRADE VALIDATION FAILED") from e

        try:
            with self.db.transaction():
                trade: Trade = self.db.get_by_id(trade_id=amendment.trade_id)
                amendment.old_value = getattr(trade, amendment.column_name)
                setattr(trade, amendment.column_name, amendment.new_value)

                recompute_method = recompute_values.get(amendment.column_name)
                if recompute_method:
                    recompute_method(trade)

                #MAJOR BUG IN THE CODE: NONE OF THE RECOMPUTED VALUES ARE STORED BACK TO THE DATABASE.
                #ONLY THE AMENDED COLUMN IS STORED IN THE DATABASE. THE RECOMPUTES GO STALE.
                valid_trade: Trade = validate_trade_data(trade)
                self.db.update_trade_field(
                    trade_id=valid_trade.trade_id, # pyright: ignore[reportArgumentType]
                    new_value=amendment.new_value,
                    column=amendment.column_name) # type: ignore  # noqa: PGH003
                amendment.amended_at = datetime.now()
                amendment.amendment_id = self.db.add_trade_amendments(amendment)
        except t.ConstraintViolationError as e:
            raise t.TradeRecordingError(f"COULDN'T RECORD NEW TRADE UPDATE: {e}") from e

        return amendment

    def finalize_grade(self, trade_id: int, parameter_names: list) -> Trade:

        if parameter_names:
            parameter_ids: list[int] = self.db.get_parameter_ids(parameter_names)
        else:
            parameter_ids = []

        #TRADE IS ALREADY GRADED AND CLIENT RESUBMITS SAME PARENTERS. = INTERNAL
        #TRADE_ID DOESN'T EXIST, FK CONSTRAINT FAILS == INTERNAL
        try:
            with self.db.transaction():
                trade: Trade = self.db.get_by_id(trade_id)
                for parameter in parameter_ids: # type: ignore  # noqa: PGH003
                    self.db.add_trade_parameters(trade_id, parameter_id=parameter)
                if trade.overall_trade_grade is None:
                    graded_trade: Trade = self.grade_trade(trade)
                else:
                    raise t.TradeAlreadyGradedError("GRADING ERROR: TRADE HAS ALREADY BEEN GRADED")
        except t.ConstraintViolationError as e:
            raise t.ParametersConflictError(
                f"PARAMETERS VIOLATE JUNCTION TABLE JOINT PK CONSTRAINT: {e}") from e

        return graded_trade

    def register_trading_account(self, account: Account) -> Account:

        try:
            account_id = self.db.create_trading_account(account)
            account.account_id = account_id
        except t.ConstraintViolationError as e:
            raise t.AccountCreationError(f"ACCOUNT COULDN'T BE CREATED DUE TO DB ERROR: {e}") from e

        return account

    def fetch_all_trading_accounts(self) -> list[Account]:

        return self.db.get_trading_accounts()

    def delete_trading_account(self, account_id: int) -> None:
        try:
            self.db.delete_account_from_db(account_id)
        except t.ConstraintViolationError as e:
            raise t.ConflictError(f"AN ACCOUNT WITH TRADES CAN'T BE DELETED: {e}") from e

    def fetch_trade_notes(self, trade_id: int) -> TradeNotes:

        return self.db.get_trade_notes(trade_id)

    def fetch_present_parameters(self, trade_id: int) -> list[str]:
        #CHECK TO SEE IF THE TRADE_ID EXISTS.
        #TRADE CAN HAVE ZERO PARAMETERS ATTACHED TO IT. FIX THIS


        parameter_ids: list[int] = self.db.get_trade_parameters(trade_id)

        return self.db.get_parameter_names(parameter_ids) if parameter_ids else []

    def delete_trade_entry(self, trade_id: int) -> None:

        self.db.delete_trade(trade_id)

    def update_trading_notes(self, trade_notes: TradeNotes) -> None:

        #database method inserts the notes row if the trade_id didn't have notes.
        #this means that this is an INSERT, not an UPDATE if no notes already exist
        try:
            self.db.update_trading_notes(new_notes=trade_notes)
        except t.ConstraintViolationError as e:
            raise t.NotesRecordingError(f"TRADE NOT FOUND: {e}") from e

    def fetch_models_list(self) -> list[TradingModel]:
        return self.db.get_models_list()

    def fetch_entry_executions_list(self) -> list[EntryExecution]:
        return self.db.get_entry_executions_list()

    def fetch_trade_management_lists(self) -> list[TradeManagement]:
        return self.db.get_trade_managements_list()

    def fetch_parameters_list(self) -> list[Parameter]:
        return self.db.get_parameters_list()

    def fetch_trading_charts(self, trade_id) -> list[TradeChart]:
        return self.db.get_trade_charts(trade_id)
