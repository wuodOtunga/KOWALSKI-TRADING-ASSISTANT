#OBJECTIVE #1: GET FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #2: RECORD FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #3: DISPLAY FULL TRADE DETAILS TO USER/TRADER
#OBJECTIVE #4: ENABLE TRADING CALCULATOR FUNCTIONALITY.
#OBJECTIVE #5: ADD IMPROVEMENTS TO THE WEBSITE.
from dataclasses import asdict
from datetime import datetime

import pandas as pd
import streamlit as st

import services as s
from database import Database
from journal import Journal
from models import TradeAsset, TradeDirection
from seed_data import (
    account_options,
    accounts_df,
    column_names,
    entry_execution_df,
    entry_execution_options,
    models_df,
    models_options,
    parameters,
    parameters_df,
    trade_management_df,
    trade_management_options,
)

min_date = datetime(1990, 1, 1)  # noqa: DTZ001
max_date = datetime.now()  # noqa: DTZ005

@st.cache_resource
def get_database():
    return Database()

@st.cache_resource
def get_journal():
    return Journal(get_database())

def main():
    journal = get_journal()
    kowalski = Kowalski(journal)
    kowalski._render_widgets()

    if st.session_state.show_trade_details_form:
        kowalski._render_trade_details_form()

    if st.session_state.show_trade_notes_form:
        kowalski._render_trade_notes_form()

    if st.session_state.show_trade_parameters_form:
        kowalski._render_trade_parameters_form()

    if st.session_state.show_trade_charts_form:
        kowalski._render_trade_charts_form()

    if st.session_state.show_trade_amendment_form:
        kowalski._render_trade_amendment_form()

    if st.session_state.show_view_trade_table:
        kowalski._render_view_trade_table()

    if st.session_state.show_all_trades:
        kowalski._render_all_trades_table()

    if st.session_state.show_journal_entry:
        kowalski._render_journal_entry_data()

    if st.session_state.show_accounts_table:
        kowalski._render_available_accounts_table()

    if st.session_state.show_trade_calculator_form:
        kowalski._render_trade_calculator_form()

    if st.session_state.show_position_sizing_form:
        kowalski._render_position_sizing_form()

class Kowalski:
    def __init__(self, journal: Journal):
        self.journal = journal

        if "trade_details" not in st.session_state:
            st.session_state.trade_details = {}

        if "trade_notes" not in st.session_state:
            st.session_state.trade_notes = {}

        if "trade_parameters" not in st.session_state:
            st.session_state.trade_parameters = {}

        if "trade_charts" not in st.session_state:
            st.session_state.trade_charts = {}

        if "trade_amendment" not in st.session_state:
            st.session_state.trade_amendment = {}

        if "account_info" not in st.session_state:
            st.session_state.account_info = {}

        if "setup_values" not in st.session_state:
            st.session_state.setup_values = {}

        if "position_sizing_inputs" not in st.session_state:
            st.session_state.position_sizing_inputs = {}

        if "show_trade_details_form" not in st.session_state:
            st.session_state.show_trade_details_form = False

        if "last_trade_result" not in st.session_state:
            st.session_state.last_trade_result = None

        if "show_trade_notes_form" not in st.session_state:
            st.session_state.show_trade_notes_form = False

        if "last_trade_notes_results" not in st.session_state:
            st.session_state.last_trade_notes_results = None

        if "show_trade_parameters_form" not in st.session_state:
            st.session_state.show_trade_parameters_form = False

        if "last_parameters_results" not in st.session_state:
            st.session_state.last_parameters_results = None

        if "show_trade_charts_form" not in st.session_state:
            st.session_state.show_trade_charts_form = False

        if "last_charts_results" not in st.session_state:
            st.session_state.last_charts_results = None

        if "show_trade_amendment_form" not in st.session_state:
            st.session_state.show_trade_amendment_form = False

        if "last_trade_changes_results" not in st.session_state:
            st.session_state.last_trade_changes_results = None

        if "show_view_trade_table" not in st.session_state:
            st.session_state.show_view_trade_table = False

        if "last_view_trade_results" not in st.session_state:
            st.session_state.last_view_trade_results = None

        if "show_all_trades" not in st.session_state:
            st.session_state.show_all_trades = False

        if "all_trades_results" not in st.session_state:
            st.session_state.all_trades_results = None

        if "journal_entry_results" not in st.session_state:
            st.session_state.journal_entry_results = None

        if "show_journal_entry" not in st.session_state:
            st.session_state.show_journal_entry = False

        if "account_info_results" not in st.session_state:
            st.session_state.account_info_results = None

        if "show_account_creation_form" not in st.session_state:
            st.session_state.show_account_creation_form = False

        if "show_accounts_table" not in st.session_state:
            st.session_state.show_accounts_table = False

        if "available_accounts_results" not in st.session_state:
            st.session_state.available_accounts_results = None

        if "show_trade_calculator_form" not in st.session_state:
            st.session_state.show_trade_calculator_form = False

        if "setup_values_results" not in st.session_state:
            st.session_state.setup_values_results = None

        if "position_sizing_results" not in st.session_state:
            st.session_state.position_sizing_results = None

        if "show_position_sizing_form" not in st.session_state:
            st.session_state.show_position_sizing_form = False
    
    def _render_trade_details_form(self):
        st.header("TRADE DETAILS ENTRY FORM")
        with st.form("TRADE DETAILS", enter_to_submit=False):

            st.number_input("ENTRY PRICE", value=None, key= "entry_price")
            st.number_input("EXIT PRICE", value=None, key= "exit_price")
            st.number_input("STOP LOSS", value=None, key= "stop_loss")
            st.number_input("TAKE PROFIT", value=None, key= "take_profit")

            st.number_input("POSITION SIZE", min_value=0.01, value=None, key= "position_size")
            st.selectbox("ASSET", list(TradeAsset), index=None, format_func=lambda a: a.value, key= "asset")
            st.radio("DIRECTION", list(TradeDirection), index=None, format_func=lambda d: d.value, key= "direction")

            st.time_input("ENTRY TIME", value=None, key= "entry_time")
            st.time_input("EXIT TIME", value=None, key= "exit_time")
            st.date_input("DATE", value=None,  min_value= min_date, max_value= max_date, key= "date")

            st.selectbox(label= "MODEL ID", options= list(models_options.keys()), index=None,
                         format_func= lambda x: models_options[x], key= "model_id")
            st.selectbox(label= "ACCOUNT ID", options= list(account_options.keys()), index=None,
                         format_func= lambda x: account_options[x], key= "account_id")
            st.selectbox(label= "MANAGEMENT ID", options= list(trade_management_options.keys()), index=None,
                         format_func= lambda x: trade_management_options[x], key= "management_id")
            st.selectbox(label= "ENTRY EXECUTION ID", options= list(entry_execution_options.keys()), index=None,
                         format_func= lambda x: entry_execution_options[x], key= "entry_execution_id")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_details = {
                    "entry_price": st.session_state.entry_price,
                    "exit_price": st.session_state.exit_price,
                    "stop_loss": st.session_state.stop_loss,
                    "take_profit": st.session_state.take_profit,
                    "position_size": st.session_state.position_size,
                    "asset": st.session_state.asset,
                    "direction": st.session_state.direction,
                    "entry_time": st.session_state.entry_time,
                    "exit_time": st.session_state.exit_time,
                    "date": st.session_state.date,
                    "model_id": st.session_state.model_id,
                    "account_id": st.session_state.account_id,
                    "management_id": st.session_state.management_id,
                    "entry_execution_id": st.session_state.entry_execution_id,
                }
                st.session_state.trade_details = trade_details
                empty_values = [key for key, value in st.session_state.trade_details.items() if value is None]
                if empty_values:
                    st.warning(f"Please fill in all these values: {','.join(empty_values)}")
                else:
                    results = s.submit_trade(st.session_state.trade_details, self.journal)

                    if results.success:
                        st.session_state.last_trade_result = results
                        st.session_state.trade_details = {}
                        st.success(results.message)
                        st.balloons()
                    else:
                        st.session_state.last_trade_result = results
                        st.error(results.message)

                    if st.session_state.last_trade_result and st.session_state.last_trade_result.success:
                        st.write("### RECORDED TRADE")
                        trade = st.session_state.last_trade_result.data
                        for field, value in asdict(trade).items(): # type: ignore
                            st.write(f"{field} : {value}")

                
    def _render_trade_notes_form(self):
        st.header("TRADE NOTES ENTRY FORM")
        with st.form("TRADE NOTES", enter_to_submit=False):
            st.number_input("TRADE ID", value= None, key= "tradingID")
            st.text_area("EMOTIONS DURING TRADE", key="emotions", placeholder="eg., Anxious at entry, confident during move.")
            st.text_area("MISTAKES MADE", key="mistakes", placeholder="eg., Entered too early, added to loosers.")
            st.text_area("LESSONS LEARNT", key="lessons", placeholder="eg., Follow the trading model.")
            st.text_area("GENERAL NOTES", key="general_notes", placeholder="Notes on trade grade, trade execution and management, etc")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_notes = {
                    "trade_id": st.session_state.tradingID,
                    "emotions": st.session_state.emotions,
                    "mistakes": st.session_state.mistakes,
                    "lessons": st.session_state.lessons,
                    "general_notes": st.session_state.general_notes,
                }
                st.session_state.trade_notes = trade_notes
                empty_values = [key for key, value in st.session_state.trade_notes.items() if value is None]
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    results = s.submit_trade_notes(st.session_state.trade_notes, self.journal)

                    if results.success:
                        st.session_state.last_trade_notes_results = results
                        st.session_state.trade_notes = {}
                        st.success(results.message)
                        st.balloons()
                    else:
                        st.session_state.last_trade_notes_results = results
                        st.error(results.message)

                    if st.session_state.last_trade_notes_results and st.session_state.last_trade_notes_results.success:
                        st.write("### RECORDED TRADE NOTES")
                        trading_notes = st.session_state.last_trade_notes_results.data
                        for field, value in asdict(trading_notes).items(): # type: ignore
                            st.write(f"{field}: {value}")
                        
    def _render_trade_parameters_form(self):
        st.header("TRADE PARAMETERS CHECKLIST")
        with st.form("PARAMETERS CHECKLIST", enter_to_submit=False):
            st.number_input("TRADE ID", value= None, key= "trade_identifier")
            
            #RESEARCH ABOUT PERSIST_STATE PARAMETER, NONE/PAGE/SESSION
            st.multiselect("PARAMETERS CHECKLIST", parameters, key="checklist")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_parameters = {
                    "trade_id": st.session_state.trade_identifier,
                    "parameters_list": st.session_state.checklist,
                }
                st.session_state.trade_parameters = trade_parameters
                #NO CHECK FOR EMPTY VALUES BECAUSE THE parameters_list CAN HAVE 0 SELECTED OPTIONS
                results = s.submit_trade_parameters(st.session_state.trade_parameters, self.journal)
                if results.success:
                    st.session_state.last_parameters_results = results
                    st.session_state.trade_parameters = {}
                    st.success(results.message)
                else:
                    st.session_state.last_parameters_results = results
                    st.error(results.message)

                #DISPLAY THE GRADED TRADE BACK TO THE TRADER.
                if st.session_state.last_parameters_results and st.session_state.last_parameters_results.success:
                    st.write(f"GRADED TRADE WITH ID OF {st.session_state.trade_identifier}")
                    trade = st.session_state.last_parameters_results.data
                    for field, value in asdict(trade).items(): # type: ignore
                        st.write(f"{field}: {value}")

    def _render_trade_charts_form(self):
        st.header("TRADING CHARTS UPLOAD")
        with st.form("TRADING CHARTS", enter_to_submit=False):
            st.number_input("TRADING ID", value= None, key= "charting_id")
            st.file_uploader("UPLOAD TRADING CHARTS", type=["png", "jpg", "jpeg"], key="charts", accept_multiple_files=True)

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_charts = {
                    "trade_id": st.session_state.charting_id,
                    "charts": st.session_state.charts,
                }
                st.session_state.trade_charts = trade_charts
                if not st.session_state.charts and st.session_state.charting_id:
                    st.warning("Please fill in all the values!")
                else:
                    results = s.submit_trade_charts(st.session_state.trade_charts, self.journal)
                    for outcome in results.outcomes:
                        if outcome.success:
                            st.session_state.last_charts_results = results
                            st.session_state.trade_charts = {}
                            st.success(f"{outcome.filename} UPLOADED SUCCESSFULLY!")
                            st.image(outcome.chart.filepath, caption= outcome.chart.filename) # pyright: ignore[reportOptionalMemberAccess]
                        else:
                            st.session_state.last_charts_results = results
                            st.error(f"{outcome.filename}: {outcome.error_message}")

    def _render_trade_amendment_form(self):
        st.header("TRADE AMENDMENTS ENTRY FORM")
        with st.form("TRADE CHANGES", enter_to_submit=False):
            st.number_input("TRADE_ID", value=None, key= "trade_id")
            st.selectbox("COLUMN NAME", column_names, index=None, key= "column_names")
            #COLUMN_NAME CAN BE A GENERIC ONE, SO ST.NUMBER_INPUT DOESN'T HANDLE
            #COLUMN VALUES THAT AREN'T NUMBER VALUES LIKE TIME, STR VALUES. FIX THIS.
            st.number_input("NEW VALUE", value=None, key= "new_value")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_amendment = {
                    "trade_id": st.session_state.trade_id,
                    "column_name": st.session_state.column_names,
                    "new_value": st.session_state.new_value,
                }
                st.session_state.trade_amendment = trade_amendment
                empty_values = [key for key, value in st.session_state.trade_amendment.items() if value is None]
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    results = s.submit_amendment(st.session_state.trade_amendment, self.journal)
                    if results.success:
                        st.session_state.last_trade_changes_results = results
                        st.session_state.trade_amendment = {}
                        st.success(results.message)
                        st.balloons()
                    else:
                        st.session_state.last_trade_changes_results = results
                        st.error(results.message)

    def _render_view_trade_table(self):
        st.subheader("VIEW RECORDED TRADE")
        with st.form("VIEW TRADE", enter_to_submit= False):
            st.number_input("TRADE_ID", min_value= 1, value= None, key= "identifier")

            submit =st.form_submit_button("SUBMIT")
            if submit:
                if not st.session_state.identifier:
                    st.warning("PLEASE PROVIDE A TRADE_ID")
                else:
                    results = s.fetch_trade(st.session_state.identifier, self.journal)
                    st.session_state.last_view_trade_results = results
                    if results.success:
                        st.success(results.message)
                        st.balloons()
                    else:
                        st.error(results.message)

        if st.session_state.last_view_trade_results and st.session_state.last_view_trade_results.success:
            trade = st.session_state.last_view_trade_results.data
            st.table(pd.DataFrame(asdict(trade), index=["info"])) # type: ignore

    def _render_all_trades_table(self):
        st.subheader("RECORD OF ALL TRADES")
        if st.session_state.show_all_trades:
            results = s.fetch_all_trades(self.journal)
            st.session_state.all_trades_results = results

            if results.success:
                st.success(results.message)
                st.balloons()
            else:
                st.error(results.message)

            if st.session_state.all_trades_results and st.session_state.all_trades_results.success:
                trades = st.session_state.all_trades_results.data
                st.table(pd.DataFrame(trades)) # type: ignore

    def _render_journal_entry_data(self):
        st.subheader("VIEW JOURNAL ENTRY")
        st.write("JOURNAL ENTRY REFERS TO TRADE DETAILS, NOTES, CHARTS, PARAMETERS BUNDLED TOGETHER")
        with st.form("JOURNAL ENTRY", clear_on_submit= True, enter_to_submit= False):
            st.number_input("TRADE_ID", min_value= 1, key= "journal_entry_id")

            submit = st.form_submit_button("SUBMIT")
            if submit:
                if not st.session_state.journal_entry_id:
                    st.warning("PLEASE PROVIDE A TRADE_ID")
                else:
                    results = s.fetch_journal_entry(st.session_state.journal_entry_id, self.journal)
                    st.session_state.journal_entry_results = results

                    if results.success:
                        st.success(results.message)
                        st.balloons()
                    else:
                        st.error(results.message)

        if st.session_state.journal_entry_results and st.session_state.journal_entry_results.success:
            journal_entry = st.session_state.journal_entry_results.data
            st.subheader("JOURNAL ENTRY RESULTS")
            st.divider()

            st.subheader("TRADE DETAILS INFO")
            st.table(pd.DataFrame(asdict(journal_entry.trade), index= ["info"])) # type: ignore
            st.divider()

            st.subheader("CHARTS ATTACHED TO THE TRADE")
            for chart in journal_entry.charts: # type: ignore
                st.image(image= chart.filepath, caption= chart.filename)
            st.divider()

            st.subheader("NOTES REGARDING THE TRADE")
            st.table(pd.DataFrame(asdict(journal_entry.trade_notes), index= ["info"])) # type: ignore
            st.divider()

            st.subheader("TRADE PARAMETERS PRESENT")
            for parameter in journal_entry.parameter_names: # type: ignore
                st.write(parameter)

    def _render_account_creation_form(self):
        st.subheader("CREATE TRADING ACCOUNT")

        with st.form("ACCOUNT CREATION", clear_on_submit= True, enter_to_submit= False):
            st.text_input("ACCOUNT NAME", value= None, key= "account_name")
            st.selectbox("ACCOUNT TYPE", ['FUNDED CHALLENGE', 'FUNDED LIVE', 'PERSONAL LIVE', 'DEMO ACCOUNT'], index= None, key= "account_type")
            st.text_input("BROKER NAME", value= None, key= "broker_name")
            st.number_input("STARTING BALANCE", value= None, key= "starting_balance")
            st.radio("IS_ACTIVE", options= [True, False], index= None, key= "is_active")

            submit = st.form_submit_button("SUBMIT")
            if submit:
                account_info = {
                    "account_name": st.session_state.account_name,
                    "account_type": st.session_state.account_type,
                    "broker_name": st.session_state.broker_name,
                    "starting_balance": st.session_state.starting_balance,
                    "is_active": st.session_state.is_active,
                }
                st.session_state.account_info = account_info
                empty_values = [key for key, value in st.session_state.account_info.items() if value is None]
                if empty_values:
                    st.warning(f"PLEASE FILL IN ALL REQUIRED FIELDS: {','.join(empty_values)}")
                else:
                    results = s.create_trading_account(st.session_state.account_info, self.journal)
                    st.session_state.account_info_results = results
                    if results.success:
                        st.success(results.message)
                        st.session_state.account_info = {}
                        st.balloons()
                    else:
                        st.error(results.message)

        st.divider()
        st.subheader("### REGISTERED ACCOUNT INFO")
        if st.session_state.account_info_results and st.session_state.account_info_results.success:
            account = st.session_state.account_info_results.data
            for key, value in asdict(account).items(): # type: ignore
                st.write(f"{key}: {value}")

    def _render_available_accounts_table(self):
        st.subheader("AVAILABLE ACCOUNTS INFO")

        if st.session_state.show_accounts_table:
            results = s.view_trading_accounts(self.journal)
            st.session_state.available_accounts_results = results

            if results.success:
                st.success(results.message)
                st.balloons()
            else:
                st.error(results.message)

            if st.session_state.available_accounts_results and st.session_state.available_accounts_results.success:
                accounts = st.session_state.available_accounts_results.data

                st.table(pd.DataFrame(accounts)) # type: ignore

    #THINK ABOUT WHETHER YOU ACTUALLY WANT CLEAR_ON_SUBMIT PARAMETER.
    #IN PRACTICE, I REALIZED THAT I WANT THE VALUES TO BE DISPLAYED.
    #FIGURE OUT PROS AND CONS.
    def _render_trade_calculator_form(self):
        st.subheader("TRADING CALCULATOR")
        with st.form("TRADING CALCULATOR", enter_to_submit= False):
            st.number_input("ENTRY PRICE", value= None, key="opening_price")
            st.number_input("EXIT PRICE", value= None, key= "closing_price")
            st.number_input("STOP LOSS", value= None, key= "loss_price")
            st.number_input("TAKE PROFIT", value= None, key= "profit_price")
            st.radio("ASSET", options= list(TradeAsset), index= None, format_func= lambda a: a.value, key= "instrument")
            st.radio("DIRECTION", options= list(TradeDirection), index= None, format_func= lambda d: d.value, key= "trade_direction")
            st.number_input("POSITION SIZE", value= None, key= "lot_size")
            st.number_input("ACCOUNT BALANCE", value= None, key= "balance")

            submit = st.form_submit_button("SUBMIT")
            if submit:
                setup_values = {
                    "entry_price": st.session_state.opening_price,
                    "exit_price": st.session_state.closing_price,
                    "stop_loss": st.session_state.loss_price,
                    "take_profit": st.session_state.profit_price,
                    "asset": st.session_state.instrument,
                    "direction": st.session_state.trade_direction,
                    "position_size": st.session_state.lot_size,
                    "account_balance": st.session_state.balance,
                }
                st.session_state.setup_values = setup_values
                results = s.run_calculator(st.session_state.setup_values)
                st.session_state.setup_values_results = results

                if results.success:
                    st.success(results.message)
                    st.session_state.setup_values = {}
                    st.balloons()
                else:
                    st.error(results.message)

        if st.session_state.setup_values_results and st.session_state.setup_values_results.success:
            profit_loss = st.session_state.setup_values_results.profit_loss
            risk_reward = st.session_state.setup_values_results.risk_reward

            st.subheader("CALCULATOR TRADE METRICS RESULTS")
            st.divider()
            st.write("PROFIT AND LOSS METRICS FOR THE TRADE SETUP")
            for key, value in profit_loss.items(): # type: ignore
                st.write(f"{key}: {value}")

            st.divider()
            st.write("RISK-REWARD METRICS FOR THE TRADE SETUP")
            for key, value in risk_reward.items(): # type: ignore
                st.write(f"{key}: {value}")

    def _render_position_sizing_form(self):
        with st.form("POSITION SIZE", enter_to_submit= False):
            st.number_input("ENTRY PRICE", value= None, key= "potential_entry")
            st.number_input("STOP LOSS", value= None, key= "potential_exit")
            st.radio("ASSET", options= list(TradeAsset), index= None, format_func= lambda a: a.value, key= "symbol")
            st.number_input("ACCOUNT BALANCE", value= None, key= "available_balance")
            st.number_input("RISK PERCENT", value= None, key= "allowed_risk")

            submit = st.form_submit_button("SUBMIT")
            if submit:
                position_sizing_inputs = {
                    "entry_price": st.session_state.potential_entry,
                    "stop_loss": st.session_state.potential_exit,
                    "asset": st.session_state.symbol,
                    "account_balance": st.session_state.available_balance,
                    "risk_percent": st.session_state.allowed_risk,
                }
                st.session_state.position_sizing_inputs = position_sizing_inputs
                results = s.position_sizing(st.session_state.position_sizing_inputs)
                st.session_state.position_sizing_results = results
                if results.success:
                    st.success(results.message)
                    st.session_state.position_sizing_inputs = {}
                    st.balloons()
                else:
                    st.error(results.message)

        if st.session_state.position_sizing_results and st.session_state.position_sizing_results.success:
            calculated_position_size = st.session_state.position_sizing_results.position_size
            st.subheader("OPTIMAL POSITION SIZE")
            st.divider()
            st.write(f"POSITION SIZE: {calculated_position_size}")

    def _render_landing_page(self):
        pass

    def _render_widgets(self):
        st.title("KOWALSKI TRADING JOURNAL")

        st.sidebar.title("NAVIGATION")
        st.sidebar.subheader("TRADING JOURNAL")
        with st.sidebar.expander("JOURNAL ACTIONS"):
            if st.button("RECORD TRADE"):
                st.session_state.show_trade_details_form = True
            if st.button("RECORD TRADE NOTES"):
                st.session_state.show_trade_notes_form = True
            if st.button("RECORD TRADE PARAMETERS"):
                st.session_state.show_trade_parameters_form = True
            if st.button("RECORD TRADE CHARTS"):
                st.session_state.show_trade_charts_form = True

            if st.button("RECORD JOURNAL ENTRY"):
                st.session_state.show_trade_details_form = True
                st.session_state.show_trade_notes_form = True
                st.session_state.show_trade_parameters_form = True
                st.session_state.show_trade_charts_form = True

            if st.button("EDIT RECORDED TRADE"):
                st.session_state.show_trade_amendment_form = True

        st.sidebar.subheader("TRADING CALCULATOR")
        with st.sidebar.expander("CALCULATOR ACTIONS"):
            if st.button("RUN CALCULATOR"):
                st.session_state.show_trade_calculator_form = True

            if st.button("POSITION SIZING"):
                st.session_state.show_position_sizing_form = True

        st.sidebar.subheader("ACCOUNTS")
        with st.sidebar.expander("ACCOUNTS ACTIONS"):
            if st.button("CREATE TRADING ACCOUNT"):
                st.session_state.show_account_creation_form = True
            if st.button("VIEW TRADING ACCOUNTS"):
                st.session_state.show_accounts_table = True

        st.sidebar.subheader("TRADE ANALYTICS")
        with st.sidebar.expander("VIEW ANALYTICS"):
            st.button("TRADE STATS")
            st.button("ANALYTICS CHARTS")

        st.sidebar.subheader("RECORDS OF TRADES")
        with st.sidebar.expander("TRADE HISTORY"):
            if st.button("VIEW TRADE"):
                st.session_state.show_view_trade_table = True

            if st.button("VIEW ALL TRADES"):
                st.session_state.show_all_trades = True

            if st.button("VIEW JOURNAL ENTRY", key= "show_entry"):
                st.session_state.show_journal_entry = True

        st.write("USE THE TABS TO IDENTIFY RELEVANT IDs REQUIRED BY THE JOURNAL.")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["tab1", "tab2", "tab3", "tab4", "tab5"])
        with tab1:
            st.subheader("TRADING MODELS")
            st.table(models_df)

        with tab2:
            st.subheader("ENTRY EXECUTION ARCHETYPES")
            st.table(entry_execution_df)

        with tab3:
            st.subheader("TRADE MANAGEMENT ARCHETYPES")
            st.table(trade_management_df)

        #WHERE DOES THE USER CREATE AN ACCOUNT?
        with tab4:
            st.subheader("TRADING ACCOUNTS")
            st.table(accounts_df)

        with tab5:
            st.subheader("TRADE PARAMETERS")
            st.table(parameters_df)

main()