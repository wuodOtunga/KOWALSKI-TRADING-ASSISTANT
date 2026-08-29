from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
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
    A = "A"
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
    account_balance : float
    risk_percent : float
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
    filename : str
    upload_date: datetime | str

@dataclass
class TradeNotes:
    """THIS CLASS MANAGES TRADING NOTES DATA."""
    """TRADING NOTES INCLUDE EMOTIONS, MISTAKES, LESSONS, GENERAL_NOTES"""
    trade_id : int | None
    emotions : str
    mistakes : str
    lessons : str
    general_notes : str

#ACCOUNT INFO IS NOT PART OF JOURNAL ENTRY!
@dataclass
class JournalEntry:
    """THIS CLASS MANAGES ENTIRE JOURNAL ENTRY DATA"""
    trade : Trade
    charts : TradeChart
    trade_notes : TradeNotes
    parameter_names : list[str]

@dataclass
class Amendments:
    "THIS CLASS MANAGES CHANGES TO JOURNAL"
    amendment_id : int | None
    trade_id : int
    column_name : str
    old_value : float | str | None
    new_value : float | str
    amended_at : datetime | None

@dataclass
class ServiceResult:
    success : bool
    message : str
    data : Trade | TradeNotes | TradeChart | list[str] | JournalEntry | list[Trade] | None

@dataclass
class ChartUploadOutcome:
    """OUTCOME FOR A SINGLE FILE WITHIN A BATCH UPLOAD"""
    filename: str
    success: bool
    chart: TradeChart | None
    error_message: str | None

@dataclass
class ChartsBatchResult:
    """AGGREGATE RESULT FOR THE WHOLE RECORD TRADE CHARTS SUBMISSION"""
    outcomes: list[ChartUploadOutcome]

    @property
    def succeeded(self) -> list[TradeChart]:
        return [o.chart for o in self.outcomes if o.success] # type: ignore

    @property
    def failed(self) -> list[ChartUploadOutcome]:
        return [o for o in self.outcomes if not o.success]

    def all_succeeded(self) -> bool:
        return all(o.success for o in self.outcomes)