from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Database
from journal import Journal
from routers import accounts, notes, parameters, trades

#HTTP REQUEST IN -> API.PY CALLS A SERVICES.PY FUNCTION -> SERVICERESULT OUT -> HTTP RESPONSE OUT!
#METHOD + PATH + REQUEST SHAPE + RESPONSE SHAPE + FAILURE MODE TO STATUS CODE MAPPING

#BASIC DATA FLOW: A REQUEST COMES IN VIA OUR API ENDPOINTS, PYDANTIC VALIDATES THE REQUEST,
#SQLALCHEMY STORES/RETRIEVES THE DATA, PYDANTIC FORMATS THE RESPONSE AND THE RESPONSE GOES OUT.
#/api/trades/{trade_id}/notes

db = Database()
journal = Journal(db= db)

app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(trades.router, prefix="api/trades", tags=["trades"])
app.include_router(notes.router, prefix="api/notes", tags=["notes"])
app.include_router(parameters.router, prefix="api/parameters", tags=["parameters"])
app.include_router(accounts.router, prefix="api/accounts", tags=["accounts"])

#SET UP HREF PAGE LINKS TO INDIVIDUAL PAGES FROM HOME.LAYOUT USING URL_FOR("trade_page", trade_id=trade.trade_id)
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
