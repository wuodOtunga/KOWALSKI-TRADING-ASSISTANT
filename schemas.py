#MODULE FOR PYDANTIC SCHEMA MODELS

from datetime import date, time, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from models import TradeAsset, TradeDirection, TradeResult

#DEBATE ON WHETHER YOU WANT ACCOUNT_ID OR ACCOUNT_NAME IN THE MODEL.
#ACCOUNT_ID IS TRIVIAL INFO, ACCOUNT_NAME HOLDS MORE CONTEXT.

#TRADE, NewTrade, TradeResponse
class Trade(BaseModel):
    """REPRESENTS THE TRADE BASE MODEL AS PARENT MODEL CLASS"""

    #FIELDS SHARED BETWEEN NewTrade AND TradeResponse
    entry_price: float
    exit_price: float
    take_profit: float
    stop_loss: float
    position_size: float
    entry_time: time
    exit_time: time
    date: date
    asset: TradeAsset
    direction: TradeDirection

class NewTrade(Trade):
    """REPRESENTS THE REQUEST SHAPE FOR CREATING NEW TRADES"""
    model_id: int
    account_id: int
    management_id: int
    entry_execution_id: int

class TradeResponse(Trade):
    """REPRESENTS SHAPE OF TRADE RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)

    trade_id: Annotated[int, Field(gt=0)]
    dollar_amount: float
    duration: timedelta
    result: TradeResult
    rr_multiple: float
    risk_percent: float


    