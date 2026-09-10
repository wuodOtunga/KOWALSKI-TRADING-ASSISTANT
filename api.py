#HTTP REQUEST IN -> API.PY CALLS A SERVICES.PY FUNCTION -> SERVICERESULT OUT -> HTTP RESPONSE OUT!
#METHOD + PATH + REQUEST SHAPE + RESPONSE SHAPE + FAILURE MODE TO STATUS CODE MAPPING

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, status

import services as s
from database import Database
from journal import Journal

app = FastAPI()
db = Database()
journal = Journal(db= db)

@app.get("/api/trades/{trade_id}")
def get_trade(trade_id: int):
    results = s.fetch_trade(trade_id= trade_id, journal= journal)

    if results.success:
        trade = results.data
        return asdict(trade) # type: ignore
    else:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= results.message)
