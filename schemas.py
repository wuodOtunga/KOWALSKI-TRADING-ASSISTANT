"""MODULE FOR THE PYDANTIC SCHEMA MODELS THAT DEFINE THE REQUESTS AND RESPONSES SHAPE FOR OUR FASTAPI API CONTRACT"""

from datetime import date, datetime, time, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from models import AmendableColumns, TradeAsset, TradeDirection, TradeResult

#DEBATE ON WHETHER YOU WANT ACCOUNT_ID OR ACCOUNT_NAME IN THE MODEL.
#ACCOUNT_ID IS TRIVIAL INFO, ACCOUNT_NAME HOLDS MORE CONTEXT.

#TRADE, NewTrade, TradeResponse
class TradeBase(BaseModel):
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

class NewTrade(TradeBase):
    """REPRESENTS THE REQUEST SHAPE FOR CREATING NEW TRADES"""
    model_id: int
    account_id: int
    management_id: int
    entry_execution_id: int

class TradeResponse(TradeBase):
    """REPRESENTS SHAPE OF TRADE RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)

    trade_id: Annotated[int, Field(gt=0)]
    dollar_amount: float
    duration: timedelta
    result: TradeResult
    rr_multiple: float
    risk_percent: float

class NewNotes(BaseModel):
    """REPRESENTS REQUEST SHAPE FOR CREATING NEW NOTES"""
    trade_id: Annotated[int, Field(gt=0)]
    emotions: str
    mistakes: str
    lessons: str
    general_notes: str

class NotesResponse(NewNotes):
    """REPRESENTS SHAPE OF NOTES RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)

class AccountBase(BaseModel):
    """REPRESENTS THE ACCOUNT BASE MODEL AS PARENT MODEL CLASS"""
    account_name: str
    account_type: str
    broker: str | None    #some accounts in database were recorded with no brokers
    starting_balance: int
    is_active: bool

class NewAccount(AccountBase):
    """REPRESENTS REQUEST SHAPE FOR CREATING NEW ACCOUNTS"""

class AccountResponse(AccountBase):
    """REPRESENTS SHAPE OF ACCOUNT RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)
    account_id: int

class ParametersBase(BaseModel):
    """REPRESENTS THE TRADE PARAMETERS BASE MODEL AS PARENT MODEL CLASS"""
    trade_id: int
    parameters_list: list[str]

class TradeParameters(ParametersBase):
    """REPRESENTS REQUEST SHAPE FOR POSTING PARAMETERS LINKED TO A TRADE"""

class ParametersResponse(ParametersBase):
    """REPRESENTS SHAPE OF TRADE PARAMETERS RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)


class TradeChanges(BaseModel):
    """REPRESENTS THE TRADE CHANGES BASE MODEL AS PARENT MODEL CLASS"""
    column_name: AmendableColumns
    new_value: float | str

class NewChanges(TradeChanges):
    """REPRESENTS REQUEST SHAPE FOR CREATING NEW CHANGES FOR A TRADE"""

class ChangesResponse(TradeChanges):
    """REPRESENTS SHAPE OF TRADE CHANGES RESPONSE CLIENT GETS TO SEE"""
    model_config = ConfigDict(from_attributes=True)

    trade_id: int
    change_id: int
    old_value: float | str
    amended_at: datetime

class TradeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_id: int
    model_name: str
    description: str

class ExecutionArchetypes(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    entry_execution_id: int
    archetype: str
    description: str
    points: int
    grade: str

class ManagementArchetypes(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    management_id: int
    archetype: str
    description: str
    points: int
    grade: str

class ParameterItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter_id: int
    parameter_name: str
