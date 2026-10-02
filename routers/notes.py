from fastapi import APIRouter, HTTPException, status

import services as s
from database import Database
from journal import Journal
from schemas import NewNotes, NotesResponse

db = Database()
journal = Journal(db= db)

router = APIRouter()

@router.post(
    path="", response_model=NotesResponse, status_code=status.HTTP_201_CREATED
)
def create_trade_notes(notes: NewNotes):
    # WE ARE NOT CHECKING FOR KEYERROR BECAUSE PYDANTIC VALIDATES NewNotes INSTANCE IS VALID

    trade_notes: dict = notes.model_dump()

    results = s.submit_trade_notes(trade_notes=trade_notes, journal=journal)
    if not results.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="INVALID TRADE_ID. NO TRADE MATCHES",
        )

    return results.data


@router.get(path="/{trade_id}", response_model=NotesResponse)
def get_trade_notes(trade_id: int):

    results = s.view_trade_notes(trade_id=trade_id, journal=journal)
    if not results.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRADE NOTES WITH THAT TRADE_ID NOT FOUND",
        )

    return results.data


@router.put(path="/{trade_id}", response_model=NotesResponse)
def update_trade_notes(trade_id: int, notes: NewNotes):

    new_notes: dict = notes.model_dump()
    results = s.amend_trade_notes(updated_notes=new_notes, journal=journal)

    if not results.success and results.error_type.value == "NOT_FOUND":  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRADE WITH THAT TRADE_ID NOT FOUND",
        )

    return NotesResponse(
        trade_id=trade_id,
        emotions=notes.emotions,
        mistakes=notes.mistakes,
        lessons=notes.lessons,
        general_notes=notes.general_notes,
    )
