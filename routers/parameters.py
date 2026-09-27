from fastapi import APIRouter, HTTPException, status

import services as s
from api import journal
from schemas import ParametersResponse, TradeParameters

router = APIRouter()

@router.post(
        path="/api/parameters",
        response_model=ParametersResponse,
        status_code=status.HTTP_201_CREATED,
)
def submit_parameters(parameters: TradeParameters):

    parameters_present: dict = parameters.model_dump()
    results = s.submit_trade_parameters(trade_parameters= parameters_present, journal= journal)

    if not results.success:
        #THE 422 RAISED HERE IS INTERESTING BECAUSE THE USER DOESN'T PROVIDE GRADES
        #IF THE GRADE FAILS VALIDATION, THEN THAT IS AN INTERNAL SERVER ERROR. DISCUSS.
        if results.error_type.value == "VALIDATION": # type: ignore
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="TRADE GRADE VALIDATION FAILED")
        if results.error_type.value == "NOT_FOUND": # type: ignore
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PROVIDED TRADE_ID IS INVALID")
        if results.error_type.value == "CONFLICT": # type: ignore
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TRADE ALREADY GRADED")
        if results.error_type.value == "INTERNAL": # type: ignore
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PARAMETERS VIOLATE JUNCTION TABLE JOINT PK CONSTRAINT")

    #IS IT POSSIBLE FOR A FUNCTION TO RETURN NONE AND THE RESPONSE MODEL STILL DOES IT'S JOB?
    return ParametersResponse(
        trade_id= parameters.trade_id,
        parameters_list= parameters.parameters_list,
    )

@router.get(path="/api/parameters/{trade_id}", response_model=ParametersResponse)
def get_parameters(trade_id: int):

    results = s.view_trade_parameters(trade_id= trade_id, journal= journal)

    #THIS HTTP CODE ISN'T TECHNICALLY ACCURATE. FIX THIS LATER.
    #WE CAN HAVE A VALID TRADE THAT DOESN'T HAVE ANY PARAMETERS TO IT.
    if not results.success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TRADE WITH THAT ID NOT FOUND")

    #CAN'T JUST RETURN RESULTS.DATA BECAUSE TRADE_ID IS ALSO REQUIRED.
    return ParametersResponse(
        trade_id= trade_id,
        parameters_list= results.data, # type: ignore
    )
