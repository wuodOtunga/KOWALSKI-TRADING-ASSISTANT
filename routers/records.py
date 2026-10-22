from fastapi import APIRouter

import services as s
from dependencies import JournalDep
from schemas import RecordsSummaryResponse, TradeRecordResponse

router = APIRouter()

@router.get(path="/trades", response_model=list[TradeRecordResponse])
def get_trade_records(journal: JournalDep):
    results = s.view_trade_records(journal=journal)
    return results.data


@router.get(path="/summary", response_model=RecordsSummaryResponse)
def get_trade_summary(journal: JournalDep):
    results = s.view_records_summary(journal=journal)
    return results.data
