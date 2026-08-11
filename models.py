from dataclasses import dataclass
from datetime import date, time, timedelta
from enum import Enum


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

class TradeResult(str, Enum):
    """THIS CLASS REPRESENTS RESULT AS A TYPE"""
    PROFIT = "PROFIT"
    LOSS = "LOSS"
    
@dataclass
class Trade:
    """THIS CLASS MANAGES TRADE DATA"""
    trade_id : int | None
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    position_size : float
    entry_time : time
    exit_time : time
    date : date
    model_id : int
    account_id : int | None
    management_id : int
    entry_execution_id : int
    asset : TradeAsset
    direction : TradeDirection
    dollar_amount : float | None
    duration : timedelta | None
    result : TradeResult | None
    rr_multiple : float | None
    overall_trade_grade : TradeGrade | None = None

@dataclass
class Account:
    """THIS CLASS MANAGES TRADING ACCOUNTS DATA"""
    account_id : int | None
    account_name : str
    account_type : str
    broker : str
    starting_balance : int
    is_active : bool

@dataclass
class TradeChart:
    "THIS CLASS MANAGES TRADING CHARTS DATA"
    chart_id : int | None
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

#CAN A DATACLASS CONTAIN OTHER DATACLASSES AS VALUE TYPES?
@dataclass
class JournalEntry:
    """THIS CLASS MANAGES ENTIRE JOURNAL ENTRY DATA"""
    trade : Trade
    account : Account
    charts : TradeChart
    trade_notes : TradeNotes
    parameter_ids : list[int]
