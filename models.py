from dataclasses import dataclass
from typing import list


#THIS CLASS MANAGES TRADE DATA.
#COLUMN ORDER NEEDS TO EXACTLY MATCH THE DATACLASS DEFINITION ORDER
@dataclass
class Trade:
    trade_id : int
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    position_size : float
    date : str
    model_id : int
    account_id : int
    management_id : int
    entry_execution_id : int
    asset : str
    direction : str
    dollar_amount : float
    profit_loss : float
    rr_ratio : int
    overall_trade_grade : str | None = None

#THIS CLASS MANAGES TRADING ACCOUNTS DATA.
@dataclass
class Accounts:
    account_id : int
    account_name : str
    account_type : str
    broker : str
    starting_balance : int
    is_active : bool

#THIS CLASS MANAGES TRADING CHARTS DATA.
@dataclass
class TradeCharts:
    chart_id : int
    trade_id : int
    filepath : str
    timeframe : str

#THIS CLASS MANAGES TRADING NOTES DATA.
#TRADING NOTES INCLUDE EMOTIONS, MISTAKES, THOUGHTS.
@dataclass
class TradeNotes:
    trade_id : int
    emotions : str
    mistakes : str
    thoughts : str
