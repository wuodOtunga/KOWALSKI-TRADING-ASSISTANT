from fastapi import APIRouter, HTTPException, status

import services as s
from database import Database
from journal import Journal
from schemas import ChangesResponse, NewChanges, NewTrade, TradeResponse

db = Database()
journal = Journal(db= db)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              

router = APIRouter()

@router.get(path="", response_model=list[TradeResponse])
def get_all_trades():

    results = s.fetch_all_trades(journal=journal)

    if not results.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="NO TRADES FOUND!"
        )

    return results.data


@router.post(
    path="",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_trade(new_trade: NewTrade):

    trade_details = new_trade.model_dump()
    results = s.submit_trade(trade_details=trade_details, journal=journal)

    if not results.success:
        if results.error_type.value == "INTERNAL":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TRADE NOT SAVED TO JOURNAL",
            )
        elif results.error_type.value == "VALIDATION":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="TRADE VALIDATION FAILED.",
            )

    return results.data


@router.get(path="/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int):

    results = s.fetch_trade(trade_id=trade_id, journal=journal)

    if not results.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PROVIDED TRADE_ID IS INVALID"
        )

    return results.data


@router.patch(path="/{trade_id}", response_model=ChangesResponse)
def update_trade_field(trade_id: int, changes: NewChanges):

    # NO USE FOR EXCLUDE_UNSET = TRUE BECAUSE ALL FIELDS WILL BE PROVIDED
    trade_changes: dict = changes.model_dump()
    trade_changes["trade_id"] = trade_id
    results = s.submit_amendment(trade_amendment=trade_changes, journal=journal)

    if not results.success:
        if results.error_type.value == "NOT_FOUND":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TRADE WITH THAT ID NOT FOUND!",
            )

        if results.error_type.value == "INTERNAL":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DATABASE ERROR WHILE RECORDING TRADE CHANGES",
            )

        if results.error_type.value == "VALIDATION":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="TRADE VALIDATION FAILED. INVALID INPUT VALUES",
            )

        if results.error_type.value == "CONFLICT":  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="RESTRICTED COLUMN NAME. COLUMN CAN'T BE CHANGED",
            )

    return ChangesResponse(
        trade_id=trade_id,
        column_name=changes.column_name,
        new_value=changes.new_value,
        change_id=results.data.amendment_id,  # type: ignore
        old_value=results.data.old_value,  # type: ignore
        amended_at=results.data.amended_at,  # type: ignore
    )


@router.delete(path="/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_row(trade_id: int):
    # THERE IS NO RESPONSE MODEL BECAUSE THERE IS NOTHING TO RETURN SINCE RESOURCE IS DELETED.
    # 204 NO CONTENT BECAUSE REQUEST IS SUCCESSFUL BUT THERE IS NO CONTENT TO RETURN.
    # IMPLEMENT CASCADE DELETE FOR DELETED TRADES

    results = s.delete_trade_from_db(trade_id=trade_id, journal=journal)

    if not results.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NO TRADE FOUND WITH THAT TRADE_ID",
        )
