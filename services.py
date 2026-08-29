#CONTAINS UI CONNECTOR FUNCTIONS THAT COORDINATE BETWEEN JOURNAL.PY AND STREAMLIT APP
import os
import uuid
from datetime import datetime
from pathlib import Path

import exceptions as t
from journal import Journal
from models import (
    Amendments,
    ChartsBatchResult,
    ChartUploadOutcome,
    JournalEntry,
    ServiceResult,
    Trade,
    TradeAsset,
    TradeChart,
    TradeDirection,
    TradeNotes,
)


#OBJECTIVE #2: RECORD A TRADE AND JOURNAL ENTRY.
#REQUIRED SERVICE FUNCTIONS.
def submit_trade(trade_details: dict, journal: Journal):
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
            account_balance= float(trade_details["account_balance"]),
            risk_percent= float(trade_details["risk_percent"]),
            overall_trade_grade= None
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"KEYERROR. VALUE ISN'T IN ST: {e}", data= None)
    except ValueError as e:
        return ServiceResult(success= False, message= f"TYPE CASTING FAILED: {e}", data= None)
    
    #STEP #3: CALL JOURNAL.PY METHOD # #STEP #4: CATCH/TRANSLATE ERRORS
    try:
        recorded_trade = journal.record_trade(trade)
    except t.Trade_Recording_Error as e:
        return ServiceResult(success= False, message= f"TRADE NOT SAVED TO JOURNAL: {e}", data= None)
    except t.Trade_Validation_Error as e:
        return ServiceResult(success= False, message= f"TRADE VALIDATION FAILED: {e}", data= None)

    #STEP #5: RETURN UI VALID OBJECT
    return ServiceResult(success= True, message= "TRADE RECORDED SUCCESSFULLY!", data= recorded_trade)

def submit_trade_notes(trade_notes: dict, journal: Journal):

    try:
        trading_notes = TradeNotes(
            trade_id= trade_notes["trade_id"],
            emotions= trade_notes["emotions"],
            mistakes= trade_notes["mistakes"],
            lessons= trade_notes["lessons"],
            general_notes= trade_notes["general_notes"]
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"SOME VALUES MISSING: {e}", data= None)

    try:
        journal.add_reflection_notes(trading_notes)
    except t.Notes_Recording_Error as e:
        return ServiceResult(success= False, message= f"ERROR OCCURRED WHILE RECORDING NOTES: {e}", data= None)

    return ServiceResult(success= True, message= "TRADE NOTES RECORDED SUCCESSFULLY!", data= trading_notes)

def submit_trade_parameters(trade_parameters: dict, journal: Journal):
    #ASSUMPTIONS INCLUDE: TRADE IS ALREADY IN THE TRADES DATABASE TABLE.
    #THE TRADE HASN'T BEEN GRADED YET SO WE CALL FINALIZE_GRADE TO GRADE IT.
    #TRADE CAN'T BE GRADED UNTIL PARAMETERS_SUBMITTED BOOL == TRUE
    #THIS SERVICE FUNCTION NEEDS TO FLIP THE BOOL FROM FALSE DEFAULT TO TRUE.

    trade_id = trade_parameters["trade_id"] #MIGHT RAISE KEYERROR, HANDLE THAT IF IT DOES.
    parameters_list = trade_parameters["parameters_list"]

    try:
        graded_trade = journal.finalize_grade(trade_id, parameters_list)

    except t.Invalid_TradeID_Error:  #WE DON'T NEED AS e BECAUSE THE ERROR MESSAGE IS SIMILAR TO .message
        return ServiceResult(success= False, message= f"PROVIDED TRADE_ID IS INVALID. GOT {trade_id}", data= None)
    except t.Grading_Error as e:
        return ServiceResult(success= False, message= f"ERROR GRADING TRADE: {e}", data= None)

    return ServiceResult(success= True, message= "TRADE PARAMETERS SUBMITTED SUCCESSFULLY!", data= graded_trade)


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
    except t.Invalid_TradeID_Error:
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
            upload_date= datetime.now().isoformat(),  # noqa: DTZ005
        )

        try:
            saved_chart = journal.attach_charts(chart)
            outcomes.append(ChartUploadOutcome(
                filename= uploaded_file.name,
                success= True,
                chart= saved_chart,
                error_message= None
            ))
        except t.Chart_Upload_Error as e:
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
    unique_filename = f"{uuid.uuid4().hex[:8]}_{original_name.stem}{original_name.suffix}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filepath, unique_filename
    
def submit_journal_entry(
            trade_details: dict,
            trade_notes: dict,
            trade_charts: dict,
            trade_parameters: list,
            journal: Journal):
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
                account_balance= float(trade_details["account_balance"]),
                risk_percent= float(trade_details["risk_percent"]),
                overall_trade_grade= None
            )

        trading_notes = TradeNotes(
                trade_id= None,
                emotions= trade_notes["emotions"],
                mistakes= trade_notes["mistakes"],
                lessons= trade_notes["lessons"],
                general_notes= trade_notes["general_notes"]
            )

        charts = TradeChart(
                chart_id= None,
                trade_id= trade_charts["trade_id"],
                filepath= trade_charts["charts"],
                filename= trade_charts["filename"],
                upload_date= datetime.now()  # noqa: DTZ005
            )
        
        journal_entry = JournalEntry(
            trade= trade,
            charts= charts,
            trade_notes= trading_notes,
            parameter_names= trade_parameters
        )
    except (KeyError, ValueError) as e:
        return ServiceResult(success= False, message= f"ERROR OCCURRED DURING OBJECT CONSTRUCTION: {e}", data= None)
    

    try:
        recorded_journal_entry = journal.record_journal_entry(journal_entry)
    except t.Journal_Entry_Error as e:
        return ServiceResult(success= False, message= f"ERROR RECORDING JOURNAL ENTRY: {e}", data= None)
    except t.Trade_Validation_Error as e:
        return ServiceResult(success= False, message= f"CHECK VALIDITY OF TRADE ENTRY DATA: {e}", data= None)
    except t.Grading_Error as e:
        return ServiceResult(success= False, message= f"ERROR CALCULATING THE GRADE OF TRADE: {e}", data= None)

    return ServiceResult(success= True, message= "JOURNAL ENTRY RECORDED SUCCESSFULLY!", data= recorded_journal_entry)


def submit_amendment(trade_amendment: dict, journal: Journal):

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
        return ServiceResult(success= False, message= f"INVALID KEY REFERENCE: {e}", data=None)

    try:
        amended_trade = journal.amend_trade_entry(amendment.trade_id, amendment)
    except t.Trade_Recording_Error as e:
        return ServiceResult(success= False, message= f"ERROR RECORDING AMENDMENT: {e}", data= None)
    except t.Trade_Validation_Error as e:
        return ServiceResult(success= False, message= f"INVALID AMENDMENT VALUES: {e}", data= None)
    except t.Invalid_Column_Name_Error as e:
        return ServiceResult(success= False, message= f"COLUMN NAME CAN'T BE AMENDED: {e}", data= None)

    return ServiceResult(success= True, message= "AMENDMENT RECORDED SUCCESSFULLY!", data= amended_trade)


#STREAMLIT DISPLAY SERVICE FUNCTIONS
def fetch_trade(trade_id: int, journal: Journal):
    try:
        trade = journal.get_trade(trade_id)
    except t.Invalid_TradeID_Error as e:
        return ServiceResult(success= False, message= f"INVALID TRADE_ID. PLEASE CHECK THE ID: {trade_id}, {e}", data= None)
    
    return ServiceResult(success= True, message= "TRADE FETCHED SUCCESSFULLY!", data= trade)

def fetch_journal_entry(trade_id: int, journal: Journal):

    try:
        journal_entry = journal.get_journal_entry(trade_id)
    except t.Journal_Entry_Error as e:
        return ServiceResult(success= False, message= f"ERROR RETRIEVING JOURNAL ENTRY: {e}", data= None)

    return ServiceResult(success= True, message= "JOURNAL ENTRY RETRIEVED SUCCESSFULLY", data= journal_entry)

#STREAMLIT SERVICE FUNCTIONS FOR ACCOUNTS ACTIONS
#ACCOUNTS ACTION: VIEW ACCOUNTS, CREATE ACCOUNT
