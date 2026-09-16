#HTTP REQUEST IN -> API.PY CALLS A SERVICES.PY FUNCTION -> SERVICERESULT OUT -> HTTP RESPONSE OUT!
#METHOD + PATH + REQUEST SHAPE + RESPONSE SHAPE + FAILURE MODE TO STATUS CODE MAPPING

#FASTAPI WILL AUTOMATICALLY HANDLE VALIDATION FOR PATH PARAMETERS.
#FASTAPI RETURNS HTTP_422_UNPROCESSABLE_CONTENT FOR PATH PARAMETERS TYPE VALIDATION ERRORS.
#422 IS ABOUT THE SHAPE OF THE REQUEST ITSELF BEING UNPROCESSABLE!
#FASTAPI AUTOMATICALLY THROWS THAT WHEN PATH/BODY PARAMETERS FAIL TYPE COERCION OR
#PYDANTIC VALIDATION BEFORE YOUR ENDPOINT CODE EVEN RUNS.
#HTTP_404_NOT_FOUND IS FOR THE REQUEST IS WELL FORMED BUT IT POINTS TO A RESOURCE THAT DOESN'T EXIST.


from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import services as s
from database import Database
from journal import Journal
from schemas import NewTrade, TradeResponse

db = Database()
journal = Journal(db= db)


app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

#HTML PAGE ROUTES FOR RENDERING PROPER HTML FOR BROWSER CONSUMER
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
    #SERVICE FUNCTION: FETCH_ALL_TRADES()
    #FAILURE MODE: TRADES_NOT_FOUND_ERROR
    #STATUS CODE MAPPING: HTTP_404_NOT_FOUND
    results = s.fetch_all_trades(journal= journal)

    if results.success:
        trades = results.data
    else:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "NO TRADES FOUND!")

    return trades

@app.post(
        path="/api/trades",
        response_model=TradeResponse,
        status_code= status.HTTP_201_CREATED
)
def create_new_trade(new_trade: NewTrade):
    #SERVICE FUNCTION: SUBMIT_TRADE()
    #FAILURE MODES: KEYERROR, VALUEERROR, TRADE_RECORDING_ERROR, TRADE_VALIDATION_ERROR
    #STATUS CODE MAPPING: {
    # TRADE_VALIDATION_ERROR == HTTP_422_UNPROCESSABLE_CONTENT
    # TRADE_RECORDING_ERROR == HTTP_500_INTERNAL_SERVER_ERROR
    # VALUEERROR == HTTP_422_UNPROCESSABLE_CONTENT
    # KEYERROR == HTTP_422_UNPROCESSABLE_CONTENT}
    #PYDANTIC SCHEMA MODELS AND FASTAPI HANDLE ALL HTTP 422 ERRORS BEFORE EXECUTING API FUNCTION
    #BY THE TIME SUBMIT_TRADE EXECUTES, THE REQUEST SHAPE IS VALID HENCE TRADE DATA IS VALID.
    #MEANING ONLY UNHANDLED FAILURE MODE IS TRADE_RECORDING_ERROR WHICH MAPS TO HTTP_500.  

    trade_details = new_trade.model_dump()
    results = s.submit_trade(trade_details= trade_details, journal= journal)

    if results.success:
        saved_trade = results.data
    else:
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "ERROR RECORDING NEW TRADE. TRY AGAIN")

    return saved_trade

@app.get(path="/api/trades/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int):
    #SERVICE FUNCTION: FETCH_TRADE()
    #FAILURE MODE: INVALID_TRADEID_ERROR
    #STATUS CODE MAPPING: HTTP_404_NOT_FOUND

    results = s.fetch_trade(trade_id= trade_id, journal= journal)

    if results.success:
        trade = results.data
    else:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "TRADE NOT FOUND: INVALID TRADE_ID")

    return trade


