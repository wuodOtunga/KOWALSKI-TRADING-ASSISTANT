from fastapi import APIRouter, status

import services as s
from dependencies import JournalDep
from http_errors import to_http_error
from schemas import NewNotes, NotesResponse

router = APIRouter()

@router.post(
    path="", response_model=NotesResponse, status_code=status.HTTP_201_CREATED
)
def create_trade_notes(notes: NewNotes, journal: JournalDep):
#should a trader be able to add notes to a trade_id via the record notes UI button and POST notes endpoint?
#or do they have to explicitly use the update notes UI button and PUT notes endpoint

    trade_notes: dict = notes.model_dump()

    results: s.ServiceResult = s.submit_trade_notes(trade_notes=trade_notes, journal=journal)
    if not results.success:
        raise to_http_error(exc=results.error)

    return results.data


@router.get(path="/{trade_id}", response_model=NotesResponse)
def get_trade_notes(trade_id: int, journal: JournalDep):

    results: s.ServiceResult = s.view_trade_notes(trade_id=trade_id, journal=journal)
    if not results.success:
        raise to_http_error(exc=results.error)

    return results.data


@router.put(path="/{trade_id}", response_model=NotesResponse)
def update_trade_notes(trade_id: int, notes: NewNotes, journal: JournalDep) -> dict:

    new_notes: dict = notes.model_dump()
    results: s.ServiceResult = s.amend_trade_notes(updated_notes=new_notes, journal=journal)

    if not results.success:
        raise to_http_error(exc=results.error)

    return new_notes
