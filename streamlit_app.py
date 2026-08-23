#OBJECTIVE #1: GET FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #2: RECORD FULL TRADE DETAILS FROM USER/TRADER
#OBJECTIVE #3: DISPLAY FULL TRADE DETAILS TO USER/TRADER
#OBJECTIVE #4: ENABLE TRADING CALCULATOR FUNCTIONALITY.
#OBJECTIVE #5: ADD IMPROVEMENTS TO THE WEBSITE.
from datetime import datetime

import streamlit as st

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
    kowalski._render_trade_details_form()
    kowalski._render_trade_notes_form()
    kowalski._render_trade_parameters_form()
    kowalski._render_trade_charts_form()
    kowalski._render_trade_amendment_form()

class Kowalski:
    def __init__(self, journal: Journal):

        if "trade_details" not in st.session_state:
            st.session_state.trade_details = {}

        if "trade_notes" not in st.session_state:
            st.session_state.trade_notes = {}

        if "trade_parameters" not in st.session_state:
            st.session_state.trade_parameters = []

        if "trade_charts" not in st.session_state:
            st.session_state.trade_charts = {}

        if "trade_amendment" not in st.session_state:
            st.session_state.trade_amendment = {}
    
    #UNDERSTAND WHETHER I SHOULD BUILD THE TRADE_DETAILS FIRST OUTSIDE SESSION_STATE
    #THEN AT IF SUBMIT IS WHEN I ADD THE DICT TO SESSION_STATE
    def _render_trade_details_form(self):
        st.header("TRADE DETAILS ENTRY FORM")
        with st.form("TRADE DATA", enter_to_submit=False):

            st.session_state.trade_details["entry_price"] = st.number_input("ENTRY PRICE", value=None)
            st.session_state.trade_details["exit_price"] = st.number_input("EXIT PRICE", value=None)
            st.session_state.trade_details["stop_loss"] = st.number_input("STOP LOSS", value=None)
            st.session_state.trade_details["take_profit"] = st.number_input("TAKE PROFIT", value=None)

            st.session_state.trade_details["position_size"] = st.number_input("POSITION SIZE", min_value=0.01, value=None)
            st.session_state.trade_details["asset"] = st.selectbox("ASSET", list(TradeAsset), index=None, format_func=lambda a: a.value)
            st.session_state.trade_details["direction"] = st.radio("DIRECTION", list(TradeDirection), index=None, format_func=lambda d: d.value)
            st.session_state.trade_details["account_balance"] = st.number_input("ACCOUNT BALANCE", value=None)
            st.session_state.trade_details["risk_percent"] = st.number_input("RISK PERCENT", value=None)

            st.session_state.trade_details["entry_time"] = st.time_input("ENTRY TIME", value=None)
            st.session_state.trade_details["exit_time"] = st.time_input("EXIT TIME", value=None)
            st.session_state.trade_details["date"] = st.date_input("DATE", min_value= min_date, max_value= max_date, value=None)

            st.session_state.trade_details["model_id"] = st.selectbox("MODEL ID", models_df["model_id"], index=None,
                                                                    format_func=lambda model_id: models_df.loc[models_df["model_id"] == model_id, "model_name"].iloc[0])
            st.session_state.trade_details["account_id"] = st.selectbox("ACCOUNT ID", accounts_df["account_id"], index=None,
                                                                        format_func=lambda account_id: accounts_df.loc[accounts_df["account_id"] == account_id, "account_name"].iloc[0])
            st.session_state.trade_details["management_id"] = st.selectbox("MANAGEMENT ID", trade_management_df["id"], index=None,
                                                                        format_func=lambda id: trade_management_df.loc[trade_management_df["id"] == id, "archetype"].iloc[0])
            st.session_state.trade_details["entry_execution_id"] = st.selectbox("ENTRY EXECUTION ID", entry_execution_df["id"], index=None,
                                                                                format_func=lambda id: entry_execution_df.loc[entry_execution_df["id"] == id, "archetype"].iloc[0])

            submit = st.form_submit_button(label="SUBMIT")
            empty_values = [key for key, value in st.session_state.trade_details.items() if value is None]
            if submit:
                if empty_values:
                    st.warning(f"Please fill in all these values: {','.join(empty_values)}")
                else:
                    st.success("TRADE DETAILS SUBMITTED SUCCESSFULLY!")
                    st.balloons()
                    st.write("### TRADE DETAILS INFO")
                    for key, value in st.session_state.trade_details.items():
                        st.write(f"{key} : {value}")

    def _render_trade_notes_form(self):
        st.header("TRADE NOTES ENTRY FORM")
        with st.form("TRADE NOTES", enter_to_submit=False):
            st.session_state.trade_notes["emotions"] = st.text_area("EMOTIONS DURING TRADE",
                                                                    key="emotions", 
                                                                    placeholder="eg., Anxious at entry, confident during move.")
            st.session_state.trade_notes["mistakes"] = st.text_area("MISTAKES MADE", 
                                                                    key="mistakes",
                                                                    placeholder="eg., Entered too early, added to loosers.")
            st.session_state.trade_notes["lessons"] = st.text_area("LESSONS LEARNT", 
                                                                key="lessons",
                                                                placeholder="eg., Follow the trading model.")
            st.session_state.trade_notes["general_notes"] = st.text_area("GENERAL NOTES", 
                                                                        key="notes",
                                                                        placeholder="Notes on trade grade, trade execution and management, etc")

            submit = st.form_submit_button(label="SUBMIT")
            empty_values = [key for key, value in st.session_state.trade_notes.items() if value is None]
            if submit:
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    st.success("TRADE NOTES SUBMITTED SUCCESSFULLY!")
                    st.balloons()
                    st.write("### TRADE NOTES INFO")
                    for key, value in st.session_state.trade_notes.items():
                        st.write(f"{key} : {value}")
                        
    #IN THIS FORM, WHAT GETS RETURNED, LIST OF INTS OR LIST OF PARAMETERS
    #WHEN YOU PRINT OUT TRADE_PARAMETERS, IT PRINTS THE LIST OF PARAMETERS.
    #SO WHEN DOES THE LIST GET TO THE TRADE PARAMETERS JUNCTION TABLE?
    def _render_trade_parameters_form(self):
        st.header("TRADE PARAMETERS CHECKLIST")
        with st.form("PARAMETERS CHECKLIST", enter_to_submit=False):
            st.session_state.trade_parameters = st.multiselect("PARAMETERS CHECKLIST", parameters, key="checklist")

            submit = st.form_submit_button(label="SUBMIT")
            if submit:
                st.write("PARAMETERS PRESENT IN THE TRADE INCLUDE:")
                for parameter in st.session_state.trade_parameters:
                    st.write(parameter)

    def _render_trade_charts_form(self):
        st.header("TRADING CHARTS UPLOAD")
        with st.form("TRADING CHARTS", enter_to_submit=False):
            st.session_state.trade_charts["charts"] = st.file_uploader("UPLOAD TRADING CHARTS", 
                                type=["png", "jpg", "jpeg"], 
                                key="charts", 
                                accept_multiple_files=True)
            st.session_state.trade_charts["timeframes"] = st.multiselect("SELECT TIMEFRAME", timeframes, key="timeframes")

            submit = st.form_submit_button(label="SUBMIT")
            empty_values = [key for key, value in st.session_state.trade_charts.items() if value is None]
            if submit:
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    st.success("TRADING CHARTS UPLOADED SUCCESSFULLY!")

    def _render_trade_amendment_form(self):
        st.header("TRADE AMENDMENTS ENTRY FORM")
        with st.form("TRADE CHANGES", enter_to_submit=False):
            st.session_state.trade_amendment["trade_id"] = st.number_input("TRADE_ID", value=None)
            st.session_state.trade_amendment["column_name"] = st.selectbox("COLUMN NAME", column_names, index=None)
            st.session_state.trade_amendment["new_value"] = st.number_input("NEW VALUE", value=None)

            submit = st.form_submit_button(label="SUBMIT")
            empty_values = [key for key, value in st.session_state.trade_amendment.items() if value is None]
            if submit:
                if empty_values:
                    st.warning(f"Please fill in all the values: {','.join(empty_values)}")
                else:
                    st.success("TRADE AMENDMENTS SUBMITTED SUCCESSFULLY!")

    def _render_widgets(self):
        st.title("KOWALSKI TRADING JOURNAL")

        st.sidebar.title("NAVIGATION")
        st.sidebar.subheader("TRADING JOURNAL")
        with st.sidebar.expander("JOURNAL ACTIONS"):
            st.button("RECORD TRADE")
            st.button("FETCH TRADE")
            st.button("AMEND TRADE")
            st.button("RECORD JOURNAL ENTRY")
            st.button("FETCH JOURNAL ENTRY")

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

        st.sidebar.subheader("RECORD OF ALL TRADES")
        with st.sidebar.expander("FULL TRADE HISTORY"):
            st.button("FETCH ALL TRADES")

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