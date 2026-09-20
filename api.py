from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

import services as s
from database import Database
from journal import Journal
from schemas import (
    AccountResponse,
    ChangesResponse,
    NewAccount,
    NewChanges,
    NewNotes,
    NewTrade,
    NotesResponse,
    ParametersResponse,
    TradeParameters,
    TradeResponse,
)

#HTTP REQUEST IN -> API.PY CALLS A SERVICES.PY FUNCTION -> SERVICERESULT OUT -> HTTP RESPONSE OUT!
#METHOD + PATH + REQUEST SHAPE + RESPONSE SHAPE + FAILURE MODE TO STATUS CODE MAPPING

db = Database()
journal = Journal(db= db)


app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

#HTML PAGE ROUTES FOR RENDERING PROPER HTML FOR BROWSER CONSUMER
#SET UP HREF PAGE LINKS TO INDIVIDUAL PAGES FROM HOME.LAYOUT USING URL_FOR("trade_page", trade_id=trade.trade_id)
#ASK CLAUDE WHY WE NEED BOTH FROM FASTAPI.EXCEPTIONS IMPORT HTTPEXCEPTIONS AND ALSO FROM STARLETTE.EXCEPTIONS IMPORT HTTPEXCEPTIONS
@app.get(path="/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request= request, name="home.html")

@app.get(path="/trades", include_in_schema=False)
def trades_page(request: Request):
    results = s.fetch_all_trades(journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "NO TRADES FOUND!")

    trades = results.data
    trade_responses = [TradeResponse.model_validate(trade, from_attributes=True) for trade in trades] # type: ignore

    return templates.TemplateResponse(request= request, name="trades_list.html", context={"trades": trade_responses})


@app.get(path="/trades/{trade_id}", include_in_schema=False)
def trade_page(trade_id: int, request: Request):
    results = s.fetch_trade(trade_id= trade_id, journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "TRADE NOT FOUND!")

    trade_response = TradeResponse.model_validate(results.data, from_attributes=True)

    return templates.TemplateResponse(request= request, name="trade_detail.html", context={"trade": trade_response})

#API ROUTES FOR RETURNING JSON DATA FOR PROGRAMMATIC ACCESS CONSUMER
@app.get(path="/api/trades", response_model= list[TradeResponse])
def get_all_trades():

    results = s.fetch_all_trades(journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "NO TRADES FOUND!")

    return results.data

@app.post(
        path="/api/trades",
        response_model=TradeResponse,
        status_code= status.HTTP_201_CREATED
)
def create_new_trade(new_trade: NewTrade):

    trade_details = new_trade.model_dump()
    results = s.submit_trade(trade_details= trade_details, journal= journal)

    if not results.success:
        if results.error_type.value == "INTERNAL": # type: ignore
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TRADE NOT SAVED TO JOURNAL")
        elif results.error_type.value == "VALIDATION": # type: ignore
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="TRADE VALIDATION FAILED.")

    return results.data

@app.get(path="/api/trades/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int):

    results = s.fetch_trade(trade_id= trade_id, journal= journal)

    if not results.success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PROVIDED TRADE_ID IS INVALID")

    return results.data

@app.patch(path="/api/trades/{trade_id}", response_model=ChangesResponse)
def update_trade_field(trade_id: int, changes: NewChanges):

    #NO USE FOR EXCLUDE_UNSET = TRUE BECAUSE ALL FIELDS WILL BE PROVIDED
    trade_changes: dict = changes.model_dump()
    trade_changes["trade_id"] = trade_id
    results = s.submit_amendment(trade_amendment= trade_changes, journal= journal)

    if not results.success:
        if results.error_type.value == "NOT_FOUND": # type: ignore
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= "TRADE WITH THAT ID NOT FOUND!",
            )

        if results.error_type.value == "INTERNAL": # type: ignore
            raise HTTPException(
                status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail= "DATABASE ERROR WHILE RECORDING TRADE CHANGES",
            )

        if results.error_type.value == "VALIDATION": # type: ignore
            raise HTTPException(
                status_code= status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="TRADE VALIDATION FAILED. INVALID INPUT VALUES",
            )

        if results.error_type.value == "CONFLICT": # type: ignore
            raise HTTPException(
                status_code= status.HTTP_409_CONFLICT,
                detail= "RESTRICTED COLUMN NAME. COLUMN CAN'T BE CHANGED",
            )

    return ChangesResponse(
        trade_id= trade_id,
        column_name= changes.column_name,
        new_value= changes.new_value,
        change_id= results.data.amendment_id, # type: ignore
        old_value= results.data.old_value, # type: ignore
        amended_at= results.data.amended_at, # type: ignore
    )

@app.delete(path="/api/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_row(trade_id: int):
    #THERE IS NO RESPONSE MODEL BECAUSE THERE IS NOTHING TO RETURN SINCE RESOURCE IS DELETED.
    #204 NO CONTENT BECAUSE REQUEST IS SUCCESSFUL BUT THERE IS NO CONTENT TO RETURN.
    #IMPLEMENT CASCADE DELETE FOR DELETED TRADES

    results = s.delete_trade_from_db(trade_id= trade_id, journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="NO TRADE FOUND WITH THAT TRADE_ID")


@app.post(
        path="/api/notes",
        response_model=NotesResponse,
        status_code=status.HTTP_201_CREATED
)
def create_trade_notes(notes: NewNotes):
    #WE ARE NOT CHECKING FOR KEYERROR BECAUSE PYDANTIC VALIDATES NewNotes INSTANCE IS VALID

    trade_notes: dict = notes.model_dump()

    results = s.submit_trade_notes(trade_notes= trade_notes, journal= journal)
    if not results.success:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "INVALID TRADE_ID. NO TRADE MATCHES"
        )

    return results.data

@app.get(path="/api/notes/{trade_id}", response_model= NotesResponse)
def get_trade_notes(trade_id: int):

    results = s.view_trade_notes(trade_id= trade_id, journal= journal)
    if not results.success:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "TRADE NOTES WITH THAT TRADE_ID NOT FOUND"
        )

    return results.data

@app.put(path="/api/notes/{trade_id}", response_model=NotesResponse)
def update_trade_notes(trade_id: int, notes: NewNotes):

    new_notes: dict = notes.model_dump()
    results = s.amend_trade_notes(updated_notes= new_notes, journal= journal)

    if not results.success and results.error_type.value == "NOT_FOUND": # type: ignore
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "TRADE WITH THAT TRADE_ID NOT FOUND"
        )

    return NotesResponse(
        trade_id= trade_id,
        emotions= notes.emotions,
        mistakes= notes.mistakes,
        lessons= notes.lessons,
        general_notes= notes.general_notes
    )

@app.post(
        path= "/api/accounts",
        response_model= AccountResponse,
        status_code= status.HTTP_201_CREATED
)
def create_account(account: NewAccount):

    account_details: dict = account.model_dump()
    results = s.create_trading_account(account_info= account_details, journal= journal)

    if not results.success:
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= "ACCOUNT CREATION FAILED DUE TO A DATABASE ERROR"
        )

    return results.data

@app.get(path= "/api/accounts", response_model= list[AccountResponse])
def get_accounts():

    results = s.view_trading_accounts(journal= journal)
    if not results.success:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "NO ACCOUNTS CREATED YET"
        )

    return results.data

@app.delete(path="/api/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int):

    results = s.delete_account_info(account_id= account_id, journal= journal)
    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="ACCOUNT WITH THAT ID NOT FOUND!")


@app.post(
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

@app.get(path="/api/parameters/{trade_id}", response_model=ParametersResponse)
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


#CACHED RESOURCES. FETCHED ONCE AT APP STARTUP AND REUSED SINCE THE DATA DOESN'T CHANGE
#MAYBE IT COULD BE POSSIBLE TO GET ALL THESE CACHED RESOURCES AT ONCE INSTEAD OF HAVING INDIVIDUAL ENDPOINTS.
def get_cached_resources():
    pass

#PROBLEM: CURRENTLY, A HTTP 404 RESPONSE FOR A TRADE THAT DOESN'T EXIST RETURNS JSON FOR BOTH THE API ENDPOINT AND HTML PAGE ROUTES.
#WE NEED TO RETURN AN ERROR HTML PAGE FOR TRADE NOT FOUND WHILE STILL RETURNING JSON FOR THE API ENDPOINT.
#YOU NEED TO DIFFERENTIATE BETWEEN THE TWO SO WE NEED AN EXCEPTION HANDLER FUNCTION THAT DIFFERENTIATES BETWEEN THE TWO AND
#RETURNS THE APPROPRIATE RESPONSE FOR THE CLIENT WHETHER IT'S AN API CLIENT OR HTML BROWSER CLIENT.

#SOME QUESTIONS: WHY DO WE NEED TO IMPORT REQUESTVALIDATIONERROR IF FASTAPI THROUGH PYDANTIC HANDLES VALIDATION ERRORS BEFORE CALLING THE ENDPOINT FUNCTION?
#WHY DO WE NEED BOTH HTTPEXCEPTION FROM STARTLETTE AND FASTAPI, WHAT'S THE DIFFERENCE?
#THIS FUNCTION HANDLES THE QUESTION: WHAT DOES FASTAPI RETURN FOR A 404 WHEN THE CLIENT WANTS EITHER HTML OR JSON?

@app.exception_handler(StarletteHTTPException)
def general_exception_handler(request: Request, exception: StarletteHTTPException):
    #WE CREATE A CUSTOM MESSAGE IF STARTLETTE HANDLES AN EXCEPTION WITHOUT A DETAIL
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again"
    )

    #CHECK TO SEE WHETHER THE REQUEST WAS FROM AN API CLIENT
    if request.url.path.startswith("/api"):
        return JSONResponse(
            content={"details" : message},
            status_code=exception.status_code,
        )

    #IF NOT API CLIENT, RETURN TEMPLATE RESPONSE WITH THE ERROR.HTML ERROR PAGE
    return templates.TemplateResponse(
        request= request,
        name="error.html",
        context={
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code= exception.status_code
    )

#PROBLEM: WE HAVE A GENERAL EXCEPTION HANDLER THAT HANDLES HTTPEXCEPTION INSTANCES BUT IT DOESN'T CATCH VALIDATION ERRORS.
#VALIDATION ERRORS INCLUDE INSTANCES WHERE A CLIENT PASSES IN A STRING LIKE HELLO FOR AN EXPECTED INT TYPE FOR TRADE_ID VALUE.
#THIS IS BECAUSE VALIDATION ERRORS ARE A DIFFERENT EXCEPTION CLASS FROM HTTPEXCEPTION. THEY ARE RequestValidationError CLASS.
#NOW OUT HTML PAGE ROUTES ARE RETURNING JSON FOR VALIDATION ERRORS, SO WE NEED TO TURN THESE INTO HTML PAGE RESPONSES.

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    #VALIDATION EXCEPTIONS DON'T HAVE A SINGLE MESSAGE VALUE. IT'S A LIST OF ERROR DETAILS.
    #EXCEPTION.ERRORS() RETURNS THIS LIST OF ERROR DETAILS.
    #VALIDATION ERRORS DON'T HAVE A STATUS_CODE ATTRIBUTE SINCE THE CODE IS ALWAYS A HTTP_422_UNPROCESSABLE_CONTENT.

    if request.url.path.startswith("/api"):
        return JSONResponse(
            content={"details" : exception.errors()},
            status_code= status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    return templates.TemplateResponse(
        request= request,
        name= "error.html",
        context={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid inputs. Please check your input values and Try again!"
        },
        status_code= status.HTTP_422_UNPROCESSABLE_CONTENT
    )
