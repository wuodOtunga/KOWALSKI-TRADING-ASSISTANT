from sqlalchemy import create_engine

SQLALCHEMY_DATABASE_URL = "sqlite:///./kowalski.db"

engine = create_engine(
    url= SQLALCHEMY_DATABASE_URL,
    connect_args= {"check_same_thread" : False},
    echo= True
)

class Repository:
    def __init__(self):
        pass

    def initialize_database(self):
        pass

#TRADE DOMAIN MODEL DATABASE METHODS; CRUD
    def save_trade(self):
        pass

    def get_by_id(self):
        pass

    def get_all_trade_rows(self):
        pass

    def update_trade_grade(self):
        pass

    def update_trade_field(self):
        pass

    def delete_trade(self):
        pass

#TRADE NOTES DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_notes(self):
        pass

    def get_trade_notes(self):
        pass

    def update_trading_notes(self):
        pass

#TRADE PARAMETERS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_parameters(self):
        pass

    def get_trade_parameters(self):
        pass

#TRADING ACCOUNTS DOMAIN MODEL DATABASE METHODS; CRUD
    def create_trading_account(self):
        pass

    def get_trading_accounts(self):
        pass

    def get_current_account_balance(self):
        pass

    def delete_account_from_db(self):
        pass

#TRADING CHARTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_chart(self):
        pass

    def get_trade_charts(self):
        pass

#TRADING AMENDMENTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_amendments(self):
        pass

#STATIC LOOK UP TABLES DATABASE READ METHODS; GETTER METHODS
#STATIC TABLES: MODELS, TRADE_MANAGEMENT, PARAMETERS, ENTRY_EXECUTION
    def get_parameter_ids(self):
            pass

    def get_parameter_names(self):
        pass

    def get_entry_execution_points(self):
        pass

    def get_trade_management_points(self):
        pass

#REPORTS/STATISTICS/ANALYTICS AGGREGATION DATABASE METHODS FOR REPORTS.PY
    def get_global_stats_rows(self):
        pass

#MISCELLANEOUS DATABASE METHODS FOR VARIOUS ABSTRACTIONS
    def check_foreign_keys(self):
        pass

    def close_db_connection(self):
        pass