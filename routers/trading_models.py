from fastapi import APIRouter

import services as s
from dependencies import JournalDep
from schemas import ExecutionArchetypes, ManagementArchetypes, Parameters, TradeModel

router = APIRouter()

@router.get(path="/models", response_model=list[TradeModel])
def models(journal: JournalDep):
    results = s.view_trading_models(journal)

    return results.data

@router.get(path="/entry_execution", response_model=list[ExecutionArchetypes])
def entry_execution(journal: JournalDep):
    results = s.view_entry_execution(journal)

    return results.data

@router.get(path="/trade_management", response_model=list[ManagementArchetypes])
def trade_management(journal: JournalDep):
    results = s.view_trade_management(journal)

    return results.data

@router.get(path="/parameters", response_model=list[Parameters])
def parameters(journal: JournalDep):
    pass
