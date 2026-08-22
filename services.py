#CONTAINS UI CONNECTOR FUNCTIONS THAT COORDINATE BETWEEN JOURNAL.PY AND STREAMLIT APP
from datetime import date, time

import exceptions as t
from journal import Journal
from models import (
    Account,
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
            entry_time= time(trade_details["entry_time"]),
            exit_time= time(trade_details["exit_time"]),
            date= date(trade_details["date"]),
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
            parameters_submitted= False,
            overall_trade_grade= None
        )
    except (ValueError, KeyError) as e:
        return ServiceResult(success= False, message= f"Invalid input values: {e}", data= None)
    
    #STEP #3: CALL JOURNAL.PY METHOD # #STEP #4: CATCH/TRANSLATE ERRORS
    try:
        recorded_trade = journal.record_trade(trade)
    except t.Trade_Recording_Error as e:
        return ServiceResult(success= False, message= f"TRADE NOT SAVED TO JOURNAL: {e}", data= None)
    except t.Trade_Validation_Error as e:
        return ServiceResult(success= False, message= f"TRADE VALIDATION FAILED: {e}", data= None)

    #STEP #5: RETURN UI VALID OBJECT
    return ServiceResult(success= True, message= "TRADE RECORDED SUCCESSFULLY!", data= recorded_trade)

def submit_trade_notes(trade_id: int, trade_notes: dict, journal: Journal):

    try:
        trading_notes = TradeNotes(
            trade_id= trade_id,
            emotions= trade_notes["emotions"],
            mistakes= trade_notes["mistakes"],
            lessons= trade_notes["lessons"],
            general_notes= trade_notes["general_notes"]
        )
    except KeyError as e:
        return ServiceResult(success= False, message= f"SOME VALUES MISSING: {e}", data= None)

    try:
        journal.add_reflection_notes(trade_id, trade_notes)
    except t.Notes_Recording_Error as e:
        return ServiceResult(success= False, message= f"ERROR OCCURRED WHILE RECORDING NOTES: {e}")

    return ServiceResult(success= True, message= "TRADE NOTES RECORDED SUCCESSFULLY!", data= trading_notes)

def submit_trade_parameters(trade_id: int, trade_parameters: list):
    #ACCEPT UI LIST OF PARAMETERS
    #CONSTRUCT DOMAIN OBJECT: LIST OF STRs
    #CALL FINALIZE_GRADE JOURNAL METHOD
    #CATCH AND TRANSLATE RELEVANT ERRORS
    #RETURN SERVICERESULT
    pass

def submit_trade_charts(trade_id: int, trade_charts: dict, journal: Journal):
    #FROM STREAMLIT DOCS
    #The UploadedFile class is a subclass of BytesIO, and therefore is "file-like". 
    #This means you can pass an instance of it anywhere a file is expected.

    charts = TradeChart(
        chart_id= None,
        trade_id= trade_id,
        filepath= trade_charts["charts"],
        timeframe= trade_charts["timeframes"]
    )

    try:
        uploaded_charts = journal.attach_charts(trade_id, charts)
    except t.Chart_Upload_Error as e:
        return ServiceResult(success= False, message= f"ERROR UPLOADING CHART: {e}", data= None)

    return ServiceResult(success= True, message="TRADE CHARTS RECORDED SUCCESSFULLY!", data= uploaded_charts)

def submit_journal_entry(
            trade_details: dict,
            trade_notes: dict,
            trade_charts: dict,
            trade_parameters: list,
            journal: Journal):

    trade = Trade(
            trade_id= None,
            entry_price= float(trade_details["entry_price"]),
            exit_price= float(trade_details["exit_price"]),
            take_profit= float(trade_details["take_profit"]),
            stop_loss= float(trade_details["stop_loss"]),
            position_size= float(trade_details["position_size"]),
            entry_time= time(trade_details["entry_time"]),
            exit_time= time(trade_details["exit_time"]),
            date= date(trade_details["date"]),
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
            parameters_submitted= False,
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
            trade_id= None,
            filepath= trade_charts["charts"],
            timeframe= trade_charts["timeframes"]
        )
    journal_entry = JournalEntry(
        trade= trade,
        charts= charts,
        trade_notes= trading_notes,
        parameter_names= trade_parameters
    )

    try:
        recorded_journal_entry = journal.record_journal_entry(journal_entry)
    except t.Journal_Entry_Error as e:
        return ServiceResult(success= False, message= f"ERROR RECORDING JOURNAL ENTRY: {e}", data= None)
    except t.Trade_Validation_Error as e:
        return ServiceResult(success= False, message= f"CHECK VALIDITY OF TRADE ENTRY DATA: {e}", data= None)
    except t.Grading_Error as e:
        return ServiceResult(success= False, message= f"ERROR CALCULATING THE GRADE OF TRADE: {e}", data= None)

    return ServiceResult(success= True, message= "JOURNAL ENTRY RECORDED SUCCESSFULLY!", data= recorded_journal_entry)


def submit_amendment():
    pass

#OBJECTIVE #3: DISPLAY A TRADE AND JOURNAL ENTRY
def fetch_trade():
    pass

def fetch_journal_entry():
    pass