from fastapi import APIRouter, status

import exceptions as t
import services as s
from dependencies import JournalDep
from http_errors import to_http_error
from schemas import AccountResponse, NewAccount

router = APIRouter()

@router.post(
        path= "",
        response_model= AccountResponse,
        status_code= status.HTTP_201_CREATED
)
def create_account(account: NewAccount, journal: JournalDep):

    account_details: dict = account.model_dump()
    results: s.ServiceResult = s.create_trading_account(account_info= account_details, journal= journal)

    if not results.success:
        raise to_http_error(exc=results.error)

    return results.data

@router.get(path= "", response_model= list[AccountResponse])
def get_accounts(journal: JournalDep):

    results: s.ServiceResult = s.view_trading_accounts(journal= journal)

    return results.data

@router.delete(path="/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, journal: JournalDep):

    results: s.ServiceResult = s.delete_account_info(account_id= account_id, journal= journal)
    if not results.success:
        raise to_http_error(exc=results.error, overrides={t.InvalidIdentifierError: 404})
