from fastapi import APIRouter, HTTPException, status

import services as s
from dependencies import JournalDep
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
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= "ACCOUNT CREATION FAILED DUE TO A DATABASE ERROR"
        )

    return results.data

@router.get(path= "", response_model= list[AccountResponse])
def get_accounts(journal: JournalDep):

    results: s.ServiceResult = s.view_trading_accounts(journal= journal)
    if not results.success:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "NO ACCOUNTS CREATED YET"
        )

    return results.data

@router.delete(path="/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, journal: JournalDep):

    results: s.ServiceResult = s.delete_account_info(account_id= account_id, journal= journal)
    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="ACCOUNT WITH THAT ID NOT FOUND!")
