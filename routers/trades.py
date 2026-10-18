from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Path, Response, UploadFile, status

import services as s
from dependencies import JournalDep
from http_errors import to_http_error
from models import ChartFile, ChartsBatchResult
from schemas import (
    ChangesResponse,
    ChartOutcomeResponse,
    ChartsBatchResponse,
    JournalEntryResponse,
    NewChanges,
    NewTrade,
    TradeResponse,
)

router = APIRouter()
MAX_CHART_BYTES = 10 * 1024 * 1024    #max chart size == 10MB

@router.get(path="", response_model=list[TradeResponse])
def get_all_trades(journal: JournalDep):

    results = s.view_all_trades(journal=journal)

    return results.data

@router.post(
    path="",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_trade(new_trade: NewTrade, journal: JournalDep):

    trade_details: dict[str, Any] = new_trade.model_dump()
    results = s.submit_trade(trade_details=trade_details, journal=journal)

    if not results.success:
        raise to_http_error(exc=results.error)

    return results.data


@router.get(path="/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int, journal: JournalDep):

    results = s.fetch_trade(trade_id=trade_id, journal=journal)

    if not results.success:
        raise to_http_error(exc=results.error)

    return results.data

def _to_response(trade_id: int, batch: ChartsBatchResult) -> ChartsBatchResponse:
    """CONVERT CHARTSBATCHRESULT TO A HTTP RESPONSE MODEL"""

    return ChartsBatchResponse(
        trade_id=trade_id,
        succeeded=len(batch.succeeded),
        failed=len(batch.failed),
        outcomes=[
            ChartOutcomeResponse(
                filename=o.filename,
                success=o.success,
                chart_id=o.chart.chart_id if o.chart else None,
                error=o.error_message,
            )
            for o in batch.outcomes
        ],
    )

@router.post(
        path="/{trade_id}/charts",
        response_model=ChartsBatchResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            207: {"model": ChartsBatchResponse, "description": "same files saved, some failed"},
            404: {"description": "Trade not found"},
            413: {"description": "A file exceeds the file limit"},
            415: {"description": "A file is not an image"},
            500: {"model": ChartsBatchResponse, "description": "every file failed to save"},
        },
)
def upload_chart(
        trade_id: Annotated[int, Path(gt=0)],
        charts: Annotated[list[UploadFile], File()],
        journal: JournalDep,
        response: Response,
) -> dict:

    results = s.fetch_trade(trade_id=trade_id, journal=journal)
    if not results.success:
        raise to_http_error(exc=results.error)

    files: list[ChartFile] = []
    for upload in charts:
        if not (upload.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"{upload.filename}: ONLY IMAGE FILES ARE ACCEPTED",
            )

        if upload.size is not None and upload.size > MAX_CHART_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"{upload.filename} EXCEEDS 10 MB LIMIT",
            )

        files.append(ChartFile(name=upload.filename or "unnamed", content=upload.file.read()))

    batch: ChartsBatchResult = s.submit_trade_charts(
        trade_charts={"trade_id": trade_id, "charts": files}, journal=journal
    )
    response_body: ChartsBatchResponse = _to_response(trade_id=trade_id, batch=batch)

    if response_body.failed == 0:
        response.status_code = status.HTTP_201_CREATED
    elif response_body.succeeded == 0:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        response.status_code = status.HTTP_207_MULTI_STATUS

    return response_body.model_dump()


@router.patch(path="/{trade_id}", response_model=ChangesResponse)
def update_trade_field(trade_id: int, changes: NewChanges, journal: JournalDep):

    # NO USE FOR EXCLUDE_UNSET = TRUE BECAUSE ALL FIELDS WILL BE PROVIDED
    trade_changes: dict = changes.model_dump()
    trade_changes["trade_id"] = trade_id
    results = s.submit_amendment(trade_amendment=trade_changes, journal=journal)

    if not results.success:
        raise to_http_error(exc=results.error)

    return trade_changes


@router.delete(path="/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_row(trade_id: int, journal: JournalDep):
    # THERE IS NO RESPONSE MODEL BECAUSE THERE IS NOTHING TO RETURN SINCE RESOURCE IS DELETED.
    # 204 NO CONTENT BECAUSE REQUEST IS SUCCESSFUL BUT THERE IS NO CONTENT TO RETURN.
    # IMPLEMENT CASCADE DELETE FOR DELETED TRADES

    results = s.delete_trade_from_db(trade_id=trade_id, journal=journal)

    if not results.success:
        raise to_http_error(exc=results.error)

@router.get("/{trade_id}/journal", response_model=JournalEntryResponse)
def get_journal_entry(trade_id: int, journal: JournalDep):
    results = s.fetch_journal_entry(trade_id=trade_id, journal=journal)
    if not results.success:
        raise to_http_error(exc=results.error)
    return results.data
