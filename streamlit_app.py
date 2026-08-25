#OBJECTIVE #1: GET FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #2: RECORD FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #3: DISPLAY FULL TRADE DETAILS TO USER/TRADER
#OBJECTIVE #4: ENABLE TRADING CALCULATOR FUNCTIONALITY.
#OBJECTIVE #5: ADD IMPROVEMENTS TO THE WEBSITE.
from dataclasses import asdict
from datetime import datetime

import streamlit as st

import services as s
from database import Database
from journal import Journal
from models import TradeAsset, TradeDirection
from seed_data import (
    accounts_df,
    column_names,
    entry_execution_df,
    models_df,
    parameters,
    parameters_df,
    timeframes,
    trade_management_df,
)

min_date = datetime(1990, 1, 1)  # noqa: DTZ001
max_date = datetime.now()  # noqa: DTZ005

#UNDERSTAND WHY DATABASE AND JOURNAL AREN'T PART OF KOWALSKI CLASS
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

    kowalski._render_trade_amendment_form()

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
    
    #UNDERSTAND WHETHER I SHOULD BUILD THE TRADE_DETAILS FIRST OUTSIDE SESSION_STATE
    #THEN AT IF SUBMIT IS WHEN I ADD THE DICT TO SESSION_STATE
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
            st.number_input("ACCOUNT BALANCE", value=None, key= "account_balance")
            st.number_input("RISK PERCENT", value=None, key= "risk_percent")

            st.time_input("ENTRY TIME", value=None, key= "entry_time")
            st.time_input("EXIT TIME", value=None, key= "exit_time")
            st.date_input("DATE", value=None,  min_value= min_date, max_value= max_date, key= "date")

            st.selectbox("MODEL ID", models_df["model_id"], index=None,
                        format_func=lambda model_id: models_df.loc[models_df["model_id"] == model_id, "model_name"].iloc[0], key= "model_id")
            st.selectbox("ACCOUNT ID", accounts_df["account_id"], index=None,
                        format_func=lambda account_id: accounts_df.loc[accounts_df["account_id"] == account_id, "account_name"].iloc[0], key= "account_id")
            st.selectbox("MANAGEMENT ID", trade_management_df["id"], index=None,
                        format_func=lambda id: trade_management_df.loc[trade_management_df["id"] == id, "archetype"].iloc[0], key= "management_id")
            st.selectbox("ENTRY EXECUTION ID", entry_execution_df["id"], index=None,
                        format_func=lambda id: entry_execution_df.loc[entry_execution_df["id"] == id, "archetype"].iloc[0], key= "entry_execution_id")

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
                    "account_balance": st.session_state.account_balance,
                    "risk_percent": st.session_state.risk_percent,
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
                        for field, value in asdict(trade).items():
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
                        for field, value in asdict(trading_notes).items():
                            st.write(f"{field}: {value}")
                        
    #IN THIS FORM, WHAT GETS RETURNED, LIST OF INTS OR LIST OF PARAMETERS
    #WHEN YOU PRINT OUT TRADE_PARAMETERS, IT PRINTS THE LIST OF PARAMETERS.
    #SO WHEN DOES THE LIST GET TO THE TRADE PARAMETERS JUNCTION TABLE?
    def _render_trade_parameters_form(self):
        st.header("TRADE PARAMETERS CHECKLIST")
        with st.form("PARAMETERS CHECKLIST", enter_to_submit=False):
            st.number_input("TRADE ID", value= None, key= "trade_identifier")
            
            #WHAT DOES MULTISELECT RETURN WHEN NO OPTIONS HAVE BEEN SELECTED
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
                    for field, value in asdict(trade).items():
                        st.write(f"{field}: {value}")

    def _render_trade_charts_form(self):
        st.header("TRADING CHARTS UPLOAD")
        with st.form("TRADING CHARTS", enter_to_submit=False):
            st.number_input("TRADING ID", value= None, key= "charting_id")
            st.file_uploader("UPLOAD TRADING CHARTS", type=["png", "jpg", "jpeg"], key="charts", accept_multiple_files=True)
            st.multiselect("SELECT TIMEFRAME", timeframes, key="timeframes")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_charts = {
                    "trade_id": st.session_state.charting_id,
                    "charts": st.session_state.charts,
                    "timeframes": st.session_state.timeframes,
                }
                st.session_state.trade_charts = trade_charts
                empty_values = [key for key, value in st.session_state.trade_charts.items() if value is None]
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    #SQLITE3.PROGRAMMINGERROR RAISED WHEN ADDING CHARTS TO THE DB.
                    #CHARTS AND TIMEFRAMES ARE LISTS HENCE WE HAVE ERROR BINDING PARAMETERS
                    #SINCE TYPE LIST IS NOT SUPPORTED. FIND A FIX.
                    results = s.submit_trade_charts(st.session_state.trade_charts, self.journal)
                    if results.success:
                        st.session_state.last_charts_results = results
                        st.session_state.trade_charts = {}
                        st.success(results.message)
                    else:
                        st.session_state.last_charts_results = results
                        st.error(results.message)

                    if st.session_state.last_charts_results and st.session_state.last_charts_results.success:
                        uploaded_charts = st.session_state.last_charts_results.data
                        for field, value in asdict(uploaded_charts).items():
                            st.write(f"{field}: {value}")

    def _render_trade_amendment_form(self):
        st.header("TRADE AMENDMENTS ENTRY FORM")
        with st.form("TRADE CHANGES", enter_to_submit=False):
            st.number_input("TRADE_ID", value=None, key= "trade_id")
            st.selectbox("COLUMN NAME", column_names, index=None, key= "column_names")
            st.number_input("NEW VALUE", value=None, key= "new_value")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                trade_amendment = {
                    "trade_id": st.session_state.trade_id,
                    "column_names": st.session_state.column_names,
                    "new_value": st.session_state.new_value,
                }
                st.session_state.trade_amendment = trade_amendment
                empty_values = [key for key, value in st.session_state.trade_amendment.items() if value is None]
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    st.success("TRADE AMENDMENTS SUBMITTED SUCCESSFULLY!")

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
            st.button("RECORD JOURNAL ENTRY")
            st.button("EDIT RECORDED TRADE")

        st.sidebar.subheader("TRADING CALCULATOR")
        with st.sidebar.expander("CALCULATOR ACTIONS"):
            st.button("PROFIT-LOSS")
            st.button("POSITION SIZING")
            st.button("RISK-REWARD RATIO")

        st.sidebar.subheader("ACCOUNTS")
        with st.sidebar.expander("ACCOUNTS ACTIONS"):
            st.button("VIEW TRADING ACCOUNTS")
            st.button("CREATE TRADING ACCOUNT")

        st.sidebar.subheader("TRADE ANALYTICS")
        with st.sidebar.expander("VIEW ANALYTICS"):
            st.button("TRADE STATS")
            st.button("ANALYTICS CHARTS")

        st.sidebar.subheader("RECORDS OF TRADES")
        with st.sidebar.expander("TRADE HISTORY"):
            st.button("VIEW TRADE")
            st.button("VIEW ALL TRADES")
            st.button("VIEW JOURNAL ENTRY")

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