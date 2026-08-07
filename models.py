from dataclasses import dataclass
from datetime import date, time
from enum import Enum

#DESIGN FIX #1: model_id, account_id, management_id, entry_execution_id
#HAVE INT TYPES. IN SCHEMA.SQL, THE 4 TABLE COLUMNS DON'T HAVE
#NOT NULL CONSTRAINTS, THIS IS A TYPE INCONSISTENCY.
#IS A TRADE CREATED ALL AT ONCE OR GRADUALLY DURING JOURNALING WORKFLOW.

#ERROR FIX #1: ENTRY_TIME, EXIT_TIME, DATE AS DATETIME IS WRONG.
#ABOVE ERROR ISSUE HAS BEEN FIXED.

#The column names returned by SQL must match the dataclass field names.
class TradeDirection(str, Enum):
    """THIS CLASS REPRESENTS DIRECTION AS A TYPE"""
    LONG = "long"
    SHORT = "short"

class TradeAsset(str, Enum):
    """THIS CLASS REPRESENTS ASSET AS A TYPE"""
    XAUUSD = "XAUUSD"
    XAGUSD = "XAGUSD"
    NQ = "NQ"
    ES = "ES"

#FIGURE HOW TO TYPE A+ INTO THE ENUM
class TradeGrade(str, Enum):
    """THIS CLASS REPRESENTS GRADE AS A TYPE"""
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    
@dataclass
class Trade:
    """THIS CLASS MANAGES TRADE DATA"""
    trade_id : int
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    position_size : float
    entry_time : time
    exit_time : time
    date : date
    model_id : int
    account_id : int
    management_id : int
    entry_execution_id : int
    asset : TradeAsset
    direction : TradeDirection
    dollar_amount : float
    result : float
    rr_multiple : float
    overall_trade_grade : TradeGrade | None = None

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

