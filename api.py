from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.templating import _TemplateResponse

import services as s
from dependencies import JournalDep
from routers import accounts, notes, parameters, trades, trading_models
from schemas import TradeResponse

#HTTP REQUEST IN -> API.PY CALLS A SERVICES.PY FUNCTION -> SERVICERESULT OUT -> HTTP RESPONSE OUT!
#METHOD + PATH + REQUEST SHAPE + RESPONSE SHAPE + FAILURE MODE TO STATUS CODE MAPPING

#BASIC DATA FLOW: A REQUEST COMES IN VIA OUR API ENDPOINTS, PYDANTIC VALIDATES THE REQUEST,
#SQLALCHEMY STORES/RETRIEVES THE DATA, PYDANTIC FORMATS THE RESPONSE AND THE RESPONSE GOES OUT.
#/api/trades/{trade_id}/notes


app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(router=trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(router=notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(router=parameters.router, prefix="/api/parameters", tags=["parameters"])
app.include_router(router=accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(router=trading_models.router, prefix="/api/static_models", tags=["static_models"])


#HTML PAGE ROUTES FOR RENDERING PROPER HTML FOR BROWSER CONSUMER
#SET UP HREF PAGE LINKS TO INDIVIDUAL PAGES FROM HOME.LAYOUT USING URL_FOR("trade_page", trade_id=trade.trade_id)
#ASK CLAUDE WHY WE NEED BOTH FROM FASTAPI.EXCEPTIONS IMPORT HTTPEXCEPTIONS AND ALSO FROM STARLETTE.EXCEPTIONS IMPORT HTTPEXCEPTIONS
@app.get(path="/", include_in_schema=False)
def home(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse(request= request, name="index.html")

@app.get(path="/trades", include_in_schema=False)
def trades_page(request: Request, journal: JournalDep) -> _TemplateResponse:
    results = s.fetch_all_trades(journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "NO TRADES FOUND!")

    trades = results.data
    trade_responses = [TradeResponse.model_validate(trade, from_attributes=True) for trade in trades] # type: ignore

    return templates.TemplateResponse(request= request, name="trades_list.html", context={"trades": trade_responses})


@app.get(path="/trades/{trade_id}", include_in_schema=False)
def trade_page(trade_id: int, request: Request, journal: JournalDep) -> _TemplateResponse:
    results = s.fetch_trade(trade_id= trade_id, journal= journal)

    if not results.success:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "TRADE NOT FOUND!")

    trade_response: TradeResponse = TradeResponse.model_validate(results.data, from_attributes=True)

    return templates.TemplateResponse(request= request, name="trade_detail.html", context={"trade": trade_response})

#SET UP HREF PAGE LINKS TO INDIVIDUAL PAGES FROM HOME.LAYOUT USING URL_FOR("trade_page", trade_id=trade.trade_id)

#PROBLEM: CURRENTLY, A HTTP 404 RESPONSE FOR A TRADE THAT DOESN'T EXIST RETURNS JSON FOR BOTH THE API ENDPOINT AND HTML PAGE ROUTES.
#WE NEED TO RETURN AN ERROR HTML PAGE FOR TRADE NOT FOUND WHILE STILL RETURNING JSON FOR THE API ENDPOINT.
#YOU NEED TO DIFFERENTIATE BETWEEN THE TWO SO WE NEED AN EXCEPTION HANDLER FUNCTION THAT DIFFERENTIATES BETWEEN THE TWO AND
#RETURNS THE APPROPRIATE RESPONSE FOR THE CLIENT WHETHER IT'S AN API CLIENT OR HTML BROWSER CLIENT.

#SOME QUESTIONS: WHY DO WE NEED TO IMPORT REQUESTVALIDATIONERROR IF FASTAPI THROUGH PYDANTIC HANDLES VALIDATION ERRORS BEFORE CALLING THE ENDPOINT FUNCTION?
#WHY DO WE NEED BOTH HTTPEXCEPTION FROM STARTLETTE AND FASTAPI, WHAT'S THE DIFFERENCE?
#THIS FUNCTION HANDLES THE QUESTION: WHAT DOES FASTAPI RETURN FOR A 404 WHEN THE CLIENT WANTS EITHER HTML OR JSON?

@app.exception_handler(exc_class_or_status_code=StarletteHTTPException)
def general_exception_handler(request: Request, exception: StarletteHTTPException) -> JSONResponse | _TemplateResponse:
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

@app.exception_handler(exc_class_or_status_code=RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError) -> JSONResponse | _TemplateResponse:
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
