from dataclasses import dataclass
from datetime import datetime

#DESIGN FIX #1: model_id, account_id, management_id, entry_execution_id
#HAVE INT TYPES. IN SCHEMA.SQL, THE 4 TABLE COLUMNS DON'T HAVE
#NOT NULL CONSTRAINTS, THIS IS A TYPE INCONSISTENCY.
#IS A TRADE CREATED ALL AT ONCE OR GRADUALLY DURING JOURNALING WORKFLOW.

#The column names returned by SQL must match the dataclass field names.
@dataclass
class Trade:
    """THIS CLASS MANAGES TRADE DATA"""
    trade_id : int
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    position_size : float
    entry_time : datetime
    exit_time : datetime
    date : datetime
    model_id : int
    account_id : int
    management_id : int
    entry_execution_id : int
    asset : str
    direction : str
    dollar_amount : float
    profit_loss : float
    rr_multiple : int
    overall_trade_grade : str | None = None

@dataclass
class Account:
    """THIS CLASS MANAGES TRADING ACCOUNTS DATA"""
    account_id : int
    account_name : str
    account_type : str
    broker : str
    starting_balance : int
    is_active : bool

@dataclass
class TradeChart:
    "THIS CLASS MANAGES TRADING CHARTS DATA"
    chart_id : int
    trade_id : int
    filepath : str
    timeframe : str

@dataclass
class TradeNotes:
    """THIS CLASS MANAGES TRADING NOTES DATA."""
    """TRADING NOTES INCLUDE EMOTIONS, MISTAKES, THOUGHTS."""
    trade_id : int
    emotions : str
    mistakes : str
    thoughts : str
