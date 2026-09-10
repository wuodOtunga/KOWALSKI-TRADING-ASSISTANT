#MODULE FOR PYDANTIC SCHEMA MODELS

from datetime import datetime, timedelta

from pydantic import BaseModel

from models import TradeAsset, TradeDirection, TradeResult


#DEBATE ON WHETHER YOU WANT ACCOUNT_ID OR ACCOUNT_NAME IN THE MODEL.
#ACCOUNT_ID IS TRIVIAL INFO, ACCOUNT_NAME HOLDS MORE CONTEXT.
class TradeResponse(BaseModel):
    """REPRESENTS THE FIELDS EXTERNAL CONSUMERS ARE ALLOWED TO SEE"""
    trade_id: int
    entry_price: float
    exit_price: float
    take_profit: float
    stop_loss: float
    asset: TradeAsset
    direction: TradeDirection
    position_size: float
    entry_time: datetime
    exit_time: datetime
    duration: timedelta
    dollar_amount: float
    result: TradeResult
    rr_multiple: float
    risk_percent: float
    