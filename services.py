#CONTAINS UI CONNECTOR FUNCTIONS THAT COORDINATE BETWEEN JOURNAL.PY AND STREAMLIT APP
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import exceptions as t
import trade_calculator as y
from journal import Journal
from models import (
    Account,
    Amendments,
    CalculatorResults,
    ChartsBatchResult,
    ChartUploadOutcome,
    EntryExecution,
    JournalEntry,
    Parameter,
    PositionSizing,
    PositionSizingInput,
    ServiceResult,
    Trade,
    TradeAsset,
    TradeChart,
    TradeDirection,
    TradeManagement,
    TradeNotes,
    TradeSetup,
    TradingModel,
)
from models import (
    ServiceErrorType as SET,
)


#OBJECTIVE #2: RECORD A TRADE AND JOURNAL ENTRY.
#REQUIRED SERVICE FUNCTIONS.
def submit_trade(trade_details: dict, journal: Journal) -> ServiceResult:
    #STEP #1: ACCEPT UI DICT/LIST DATA

    #STEP #2: CONSTRUCT DOMAIN OBJECT
    try:
        trade = Trade(
            trade_id= None,
            entry_price= float(trade_details["entry_price"]),
            exit_price= float(trade_details["exit_price"]),
            take_profit= float(trade_details["take_profit"]),
            stop_loss= float(trade_details["stop_loss"]),
            position_size= float(trade_details["position_size"]),
            entry_time= trade_details["entry_time"],
            exit_time= trade_details["exit_time"],
            date= trade_details["date"],
            model_id= int(trade_details["model_id"]),
            account_id= int(trade_details["account_id"]),
            management_id= int(trade_details["management_id"]),
            entry_execution_id= int(trade_details["entry_execution_id"]),
            asset= TradeAsset(trade_details["asset"]),
            direction= TradeDirection(trade_details["direction"]),
            dollar_amount= None,
            duration= None,
            result= None,
            rr_multiple= None,
            risk_percent= None,
            overall_trade_grade= None
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"KEYERROR. VALUE ISN'T IN DICTIONARY: {e}", data= None, error_type=SET.VALIDATION)
    except ValueError as e:
        return ServiceResult(success= False, message= f"TYPE CASTING FAILED: {e}", data= None, error_type=SET.VALIDATION)

    #STEP #3: CALL JOURNAL.PY METHOD # #STEP #4: CATCH/TRANSLATE ERRORS
    try:
        recorded_trade = journal.record_trade(trade)
    except t.TradeRecordingError as e:
        return ServiceResult(success= False, message= f"TRADE NOT SAVED TO JOURNAL: {e}", data= None, error_type=SET.INTERNAL)
    except t.TradeValidationError as e:
        return ServiceResult(success= False, message= f"TRADE VALIDATION FAILED: {e}", data= None, error_type=SET.VALIDATION)

    #STEP #5: RETURN UI VALID OBJECT
    return ServiceResult(success= True, message= "TRADE RECORDED SUCCESSFULLY!", data= recorded_trade, error_type=None)

def submit_trade_notes(trade_notes: dict, journal: Journal) -> ServiceResult:

    try:
        trading_notes = TradeNotes(
            trade_id= trade_notes["trade_id"],
            emotions= trade_notes["emotions"],
            mistakes= trade_notes["mistakes"],
            lessons= trade_notes["lessons"],
            general_notes= trade_notes["general_notes"]
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"SOME VALUES MISSING: {e}", data= None, error_type=SET.VALIDATION)

    try:
        journal.add_reflection_notes(trading_notes)
    except t.NotesRecordingError as e:
        return ServiceResult(success= False, message= f"ERROR OCCURRED WHILE RECORDING NOTES: {e}", data= None, error_type=SET.NOT_FOUND)

    return ServiceResult(success= True, message= "TRADE NOTES RECORDED SUCCESSFULLY!", data= trading_notes, error_type=None)

def submit_trade_parameters(trade_parameters: dict, journal: Journal) -> ServiceResult:
    #ASSUMPTIONS INCLUDE: TRADE IS ALREADY IN THE TRADES DATABASE TABLE.
    #THE TRADE HASN'T BEEN GRADED YET SO WE CALL FINALIZE_GRADE TO GRADE IT.
    #TRADE CAN'T BE GRADED UNTIL PARAMETERS_SUBMITTED BOOL == TRUE
    #THIS SERVICE FUNCTION NEEDS TO FLIP THE BOOL FROM FALSE DEFAULT TO TRUE.

    trade_id = trade_parameters["trade_id"] #MIGHT RAISE KEYERROR, HANDLE THAT IF IT DOES.
    parameters_list = trade_parameters["parameters_list"]

    try:
        graded_trade = journal.finalize_grade(trade_id, parameters_list)

    except t.InvalidTradeIDError:  #WE DON'T NEED AS e BECAUSE THE ERROR MESSAGE IS SIMILAR TO .message
        return ServiceResult(success= False, message= f"PROVIDED TRADE_ID IS INVALID. GOT {trade_id}", data= None, error_type=SET.NOT_FOUND)
    except t.GradingError as e:
        return ServiceResult(success= False, message= f"PROVIDED GRADE IS INVALID: {e}", data= None, error_type=SET.VALIDATION)
    except t.TradeAlreadyGradedError:
        return ServiceResult(
            success=False,
            message="GRADING ERROR: TRADE HAS ALREADY BEEN GRADED",
            data=None,
            error_type=SET.CONFLICT,
        )
    except t.ParametersJunctionTableConflict:
        return ServiceResult(
            success=False,
            message="PARAMETERS VIOLATE JUNCTION TABLE JOINT PK CONSTRAINT",
            data=None,
            error_type=SET.INTERNAL,
        )

    return ServiceResult(success= True, message= "TRADE PARAMETERS SUBMITTED SUCCESSFULLY!", data= graded_trade, error_type=None)


def submit_trade_charts(trade_charts: dict, journal: Journal) -> ChartsBatchResult:
    #FROM STREAMLIT DOCS
    #The UploadedFile class is a subclass of BytesIO, and therefore is "file-like".
    #This means you can pass an instance of it anywhere a file is expected.

    trade_id = trade_charts["trade_id"]
    uploaded_files = trade_charts["charts"]

    if not uploaded_files:
        return ChartsBatchResult(outcomes=[])

    #CHECK LEGITIMACY OF TRADE_ID BEFORE BATCH LOOPING OPERATIONS
    try:
        journal.get_trade(trade_id)
    except t.InvalidTradeIDError:
        return ChartsBatchResult(outcomes=[
            ChartUploadOutcome(filename= f.name, success= False,
                               chart= None, error_message= f"TRADE_ID {trade_id} INVALID")
                               for f in uploaded_files
        ])

    outcomes = []
    for uploaded_file in uploaded_files:
        filepath = None

        try:
            filepath, filename = _save_uploaded_charts(uploaded_file)
        except OSError as e:
            outcomes.append(ChartUploadOutcome(
                filename= uploaded_file.name,
                success= False,
                chart= None,
                error_message= f"COULD NOT SAVE FILE {e}"
            ))

            continue

        chart = TradeChart(
            chart_id= None,
            trade_id= trade_id,
            filepath= filepath,
            filename= filename,
            upload_date= datetime.now(tz=UTC)
        )

        try:
            saved_chart: TradeChart = journal.attach_charts(chart)
            outcomes.append(ChartUploadOutcome(
                filename= uploaded_file.name,
                success= True,
                chart= saved_chart,
                error_message= None
            ))
        except t.ChartUploadError as e:
            #YOU HAVE TO REMOVE THE SAVED CHARTS IF DATABASE INSERT FAILS
            os.remove(filepath)
            outcomes.append(ChartUploadOutcome(
                filename= uploaded_file.name,
                success= False,
                chart= None,
                error_message= f"DATABASE SAVE FAILED {e}"
            ))

    return ChartsBatchResult(outcomes= outcomes)


def _save_uploaded_charts(uploaded_file) -> tuple[str, str]:
    UPLOAD_DIR = "uploaded_charts"
    Path(UPLOAD_DIR).mkdir(exist_ok=True)

    original_name = Path(uploaded_file.name)  #.name is the string filename attribute
    unique_filename: str = f"{uuid.uuid4().hex[:8]}_{original_name.stem}{original_name.suffix}"
    filepath: str = os.path.join(UPLOAD_DIR, unique_filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filepath, unique_filename

#NOTE TO FUTURE DEVELOPER: SUBMIT_JOURNAL_ENTRY SERVICE FUNCTION WAS DELETED ON 30/8/2026.
#WITH THE GIVEN STREAMLIT CODE PATH, THERE IS NO USE FOR THE SERVICE FUNCTION.
#IN THE FUTURE IF NEED ARISES FOR THIS SERVICE FUNCTION, SIMPLY REWRITE IT.

def submit_amendment(trade_amendment: dict, journal: Journal) -> ServiceResult:

    try:
        amendment = Amendments(
            amendment_id= None,
            trade_id= trade_amendment["trade_id"],
            column_name= trade_amendment["column_name"],
            old_value= None,
            new_value= trade_amendment["new_value"],
            amended_at= None
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"INVALID KEY REFERENCE: {e}", data=None, error_type=SET.VALIDATION)

    try:
        changes: Amendments = journal.amend_trade_entry(amendment.trade_id, amendment)
    except t.InvalidTradeIDError as e:
        return ServiceResult(success= False, message= f"TRADE NOT FOUND: {e}", data=None, error_type=SET.NOT_FOUND)
    except t.TradeRecordingError as e:
        return ServiceResult(success= False, message= f"ERROR RECORDING AMENDMENT: {e}", data= None, error_type=SET.INTERNAL)
    except t.TradeValidationError as e:
        return ServiceResult(success= False, message= f"INVALID AMENDMENT VALUES: {e}", data= None, error_type=SET.VALIDATION)
    except t.InvalidColumnNameError as e:
        return ServiceResult(success= False, message= f"COLUMN NAME CAN'T BE AMENDED: {e}", data= None, error_type=SET.CONFLICT)

    return ServiceResult(success= True, message= "AMENDMENT RECORDED SUCCESSFULLY!", data= changes, error_type=None)


#STREAMLIT DISPLAY SERVICE FUNCTIONS
def fetch_trade(trade_id: int, journal: Journal) -> ServiceResult:
    try:
        trade: Trade = journal.get_trade(trade_id)
    except t.InvalidTradeIDError as e:
        return ServiceResult(success= False, message= f"INVALID TRADE_ID. PLEASE CHECK THE ID: {trade_id}, {e}", data= None, error_type=SET.NOT_FOUND)

    return ServiceResult(success= True, message= "TRADE FETCHED SUCCESSFULLY!", data= trade, error_type=None)

def fetch_all_trades(journal: Journal) -> ServiceResult:
    try:
        trades: list[Trade] = journal.get_all_trades()
    except t.TradesNotFoundError as e:
        return ServiceResult(success= False, message= f"NO TRADES FOUND: {e}", data= None, error_type=SET.NOT_FOUND)

    return ServiceResult(success= True, message= "AVAILABLE TRADES FOUND SUCCESSFULLY", data= trades, error_type=None)

def fetch_journal_entry(trade_id: int, journal: Journal) -> ServiceResult:

    try:
        journal_entry: JournalEntry = journal.get_journal_entry(trade_id)
    except t.JournalEntryError as e:
        return ServiceResult(success= False, message= f"ERROR RETRIEVING JOURNAL ENTRY: {e}", data= None, error_type=SET.INTERNAL)

    return ServiceResult(success= True, message= "JOURNAL ENTRY RETRIEVED SUCCESSFULLY", data= journal_entry, error_type=None)

def view_trade_notes(trade_id: int, journal: Journal) -> ServiceResult:

    try:
        trade_notes: TradeNotes = journal.fetch_trade_notes(trade_id)
    except t.InvalidTradeIDError as e:
        return ServiceResult(
            success= False,
            message= f"INVALID TRADE_ID. PLEASE CHECK THE ID: {trade_id}. {e}",
            data= None,
            error_type=SET.NOT_FOUND
        )

    return ServiceResult(
        success= True,
        message= "TRADE NOTES RETRIEVED SUCCESSFULLY!",
        data= trade_notes,
        error_type=None,
    )

def amend_trade_notes(updated_notes: dict, journal: Journal) -> ServiceResult:

    try:
        notes = TradeNotes(
            trade_id= updated_notes["trade_id"],
            emotions= updated_notes["emotions"],
            mistakes= updated_notes["mistakes"],
            lessons= updated_notes["lessons"],
            general_notes= updated_notes["general_notes"],
        )
    except KeyError as e:
        return ServiceResult(
            success= False,
            message= f"SOME INPUT VALUES ARE MISSING. CHECK INPUTS: {e}",
            data= None,
            error_type= SET.VALIDATION
        )

    try:
        journal.update_trading_notes(trade_notes= notes)
    except t.InvalidTradeIDError as e:
        return ServiceResult(
            success= False,
            message= f"TRADE NOT FOUND. INVALID TRADE_ID: {e}",
            data= None,
            error_type= SET.NOT_FOUND
        )

    return ServiceResult(
        success= True,
        message= "TRADE NOTES UPDATED SUCCESSFULLY!",
        data= None,
        error_type= None
    )

def view_trade_parameters(trade_id: int, journal: Journal) -> ServiceResult:

    try:
        parameters: list[str] = journal.fetch_present_parameters(trade_id)
    except t.InvalidTradeIDError:
        return ServiceResult(
            success=False,
            message=f"INVALID TRADE_ID. PLEASE CHECK THE ID: {trade_id}",
            data=None,
            error_type=SET.NOT_FOUND
        )

    return ServiceResult(
        success=True,
        message="TRADE PARAMETERS RETRIEVED SUCCESSFULLY!",
        data= parameters,
        error_type=None
    )

def delete_trade_from_db(trade_id: int, journal: Journal) -> ServiceResult:

    try:
        journal.delete_trade_entry(trade_id)
    except t.InvalidTradeIDError:
        return ServiceResult(
            success=False,
            message=f"INVALID TRADE_ID. PLEASE CHECK THE ID: {trade_id}",
            data=None,
            error_type=SET.NOT_FOUND,
        )

    return ServiceResult(
        success=True,
        message="TRADE DELETED SUCCESSFULLY!",
        data=None,
        error_type=None
    )

#STREAMLIT SERVICE FUNCTIONS FOR ACCOUNTS ACTIONS
#ACCOUNTS ACTION: VIEW ACCOUNTS, CREATE ACCOUNT
def create_trading_account(account_info: dict, journal: Journal) -> ServiceResult:
    try:
        account = Account(
            account_id= None,
            account_name= account_info["account_name"],
            account_type= account_info["account_type"],
            broker= account_info["broker_name"],
            starting_balance= account_info["starting_balance"],
            is_active= account_info["is_active"]
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"INVALID KEY REFERENCE: {e}", data= None, error_type=SET.VALIDATION)

    try:
        registered_account = journal.register_trading_account(account)
    except t.AccountCreationError as e:
        return ServiceResult(success= False, message= f"ACCOUNT REGISTRATION FAILED: {e}", data= None, error_type=SET.INTERNAL)

    return ServiceResult(success= True, message= "ACCOUNT REGISTERED SUCCESSFULLY!", data= registered_account, error_type=None)

def view_trading_accounts(journal: Journal) -> ServiceResult:
    try:
        available_accounts = journal.fetch_all_trading_accounts()
    except t.AccountsNotFoundError as e:
        return ServiceResult(success= False, message= f"NO ACCOUNTS FOUND! {e}", data= None, error_type=SET.NOT_FOUND)

    return ServiceResult(success= True, message= "ACCOUNTS FOUND SUCCESSFULLY!", data= available_accounts, error_type=None) # type: ignore

def delete_account_info(account_id: int, journal: Journal) -> ServiceResult:

    try:
        journal.delete_trading_account(account_id= account_id)
    except t.AccountNotFoundError:
        return ServiceResult(
            success=False,
            message= "ACCOUNT DOESN'T EXIST",
            data=None,
            error_type=SET.NOT_FOUND,
        )

    return ServiceResult(
        success=True,
        message="ACCOUNT DELETED SUCCESSFULLY!",
        data=None,
        error_type=None,
    )

def view_trading_models(journal: Journal) -> ServiceResult:
    trading_models: list[TradingModel] = journal.fetch_models_list()

    return ServiceResult(
        success=True,
        message="TRADING MODELS RETRIEVED SUCCESSFULLY!",
        data=trading_models,
        error_type=None
    )

def view_entry_execution(journal: Journal) -> ServiceResult:
    archetypes: list[EntryExecution] = journal.fetch_entry_executions_list()

    return ServiceResult(
        success=True,
        message="ENTRY EXECUTIONS RETRIEVED SUCCESSFULLY!",
        data=archetypes,
        error_type=None
    )

def view_trade_management(journal: Journal) -> ServiceResult:
    archetypes: list[TradeManagement] = journal.fetch_trade_management_lists()

    return ServiceResult(
        success=True,
        message="TRADE MANAGEMENTS RETRIEVED SUCCESSFULLY!",
        data=archetypes,
        error_type=None
    )

def view_parameters_list(journal: Journal) -> ServiceResult:
    parameters: list[Parameter] = journal.fetch_parameters_list()

    return ServiceResult(
        success=True,
        message="PARAMETERS LIST RETRIEVED SUCCESSFULLY!",
        data=parameters,
        error_type=None
    )

#SERVICE FUNCTIONS FOR STREAMLIT TRADE CALCULATOR FEATURE BUTTONS.
def run_calculator(setup_values: dict) -> CalculatorResults:
    #USER WANTS TO CALCULATE PROFIT/LOSS, RISK_REWARD RATIO
    try:
        setup = TradeSetup(
            entry_price= float(setup_values["entry_price"]),
            exit_price= float(setup_values["exit_price"]),
            stop_loss= float(setup_values["stop_loss"]),
            take_profit= float(setup_values["take_profit"]),
            asset= TradeAsset(setup_values["asset"]),
            direction= TradeDirection(setup_values["direction"]),
            position_size= float(setup_values["position_size"]),
            account_balance= float(setup_values["account_balance"]),
            entry_time= None,
            exit_time= None,
            date= None,
        )
    except ValueError as e:
        return CalculatorResults(
            success= False,
            message= f"TYPE VALIDATION FAILED. CHECK INPUT TYPES: {e}",
            profit_loss= None,
            risk_reward= None,
        )
    except KeyError as e:
        return CalculatorResults(
            success= False,
            message= f"SOME INPUT VALUES ARE MISSING. PROVIDE ALL REQUIRED FIELDS: {e}",
            profit_loss= None,
            risk_reward= None,
        )

    try:
        profit_loss_results = y.calculate_profit_loss(setup)
        risk_reward_results = y.calculate_risk_reward_multiple(setup)
    except t.TradeValidationError as e:
        return CalculatorResults(
            success= False,
            message= f"TRADE VALIDATION FAILED: {e}",
            profit_loss= None,
            risk_reward= None,
        )

    return CalculatorResults(
        success= True,
        message= "CALCULATIONS DONE SUCCESSFULLY!",
        profit_loss= profit_loss_results,
        risk_reward= risk_reward_results,
    )

def position_sizing(position_sizing_inputs: dict) -> PositionSizingInput:

    try:
        position_size = PositionSizing(
            entry_price= float(position_sizing_inputs["entry_price"]),
            stop_loss= float(position_sizing_inputs["stop_loss"]),
            asset= TradeAsset(position_sizing_inputs["asset"]),
            account_balance= float(position_sizing_inputs["account_balance"]),
            risk_percent= float(position_sizing_inputs["risk_percent"])
        )
    except (KeyError, ValueError) as e:
        return PositionSizingInput(
            success= False,
            message= f"WRONG INPUT VALUES. ENTER VALID VALUES: {e}",
            position_size= None
        )

    try:
        lot = y.calculate_position_size(position_size)
    except t.TradeValidationError as e:
        return PositionSizingInput(
            success= False,
            message= f"INPUT VALIDATION FAILED: {e}",
            position_size= None
        )

    return PositionSizingInput(
        success= True,
        message= "POSITION SIZE CALCULATED SUCCESSFULLY!",
        position_size= lot
    )
