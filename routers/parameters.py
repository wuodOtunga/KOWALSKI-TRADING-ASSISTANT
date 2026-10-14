from fastapi import APIRouter, status

import services as s
from dependencies import JournalDep
from http_errors import to_http_error
from schemas import ParametersResponse, TradeParameters

router = APIRouter()

@router.post(
        path="",
        response_model=ParametersResponse,
        status_code=status.HTTP_201_CREATED,
)
def submit_parameters(parameters: TradeParameters, journal: JournalDep) -> dict:

    parameters_present: dict = parameters.model_dump()
    results: s.ServiceResult = s.submit_trade_parameters(
        trade_parameters= parameters_present, journal= journal
    )

    if not results.success:
        raise to_http_error(exc=results.error)

    return parameters_present

@router.get(path="/{trade_id}", response_model=ParametersResponse)
def get_parameters(trade_id: int, journal: JournalDep) -> dict:

    results = s.view_trade_parameters(trade_id= trade_id, journal= journal)

    #THIS HTTP CODE ISN'T TECHNICALLY ACCURATE. FIX THIS LATER.
    #WE CAN HAVE A VALID TRADE THAT DOESN'T HAVE ANY PARAMETERS TO IT.
    if not results.success:
        raise to_http_error(exc=results.error)

    #CAN'T JUST RETURN RESULTS.DATA BECAUSE TRADE_ID IS ALSO REQUIRED.
    return {"trade_id": trade_id, "parameters_list": results.data}
