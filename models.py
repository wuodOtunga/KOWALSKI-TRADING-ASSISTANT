from dataclasses import dataclass
from typing import Optional

#THIS CLASS MANAGES TRADE DATA.
@dataclass
class Trade:
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    position_size : float
    asset : str
    direction : str
    date : str
    dollar_amount : float
    profit_loss : float
    rr_ratio : float

    overall_trade_grade : Optional[str] = None
    trade_id : int
    model_id : int
    account_id : int
    management_id : int
    entry_execution_id : int
    parameter_ids : list[int]

#THIS CLASS MANAGES TRADING ACCOUNTS DATA.
@dataclass
class Account:
    account_id : int
    account_name : str
    account_type : str
    broker : str
    starting_balance : int
    is_active : bool

#THIS CLASS MANAGES TRADING CHARTS DATA.
@dataclass
class TradeChart:
    chart_id : int
    filepath : str
    timeframe : str

#THIS CLASS MANAGES TRADING NOTES DATA.
#TRADING NOTES INCLUDE EMOTIONS, MISTAKES, THOUGHTS.
@dataclass
class TradeNote:
    emotions : str
    mistakes : str
    thoughts : str
