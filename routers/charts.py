from fastapi import APIRouter, HTTPException, UploadFile, File, status
import services as s
from dependencies import JournalDep
from schemas import CreateChart, ChartsResponse

router = APIRouter()

@router.post(path="/{trade_id}", response_model=ChartsResponse)
def upload_chart(chart: CreateChart, trade_id: int, journal: JournalDep):
    pass

@router.get(path="/{trade_id}", response_model=ChartsResponse)
def get_charts(trade_id: int, journal: JournalDep):
    pass

router.patch(path="/{trade_id}", response_model=ChartsResponse)
def update_charts(trade_id: int, journal: JournalDep):
    pass