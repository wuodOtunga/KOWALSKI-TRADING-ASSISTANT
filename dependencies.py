from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from database import Database
from journal import Journal


@lru_cache
def get_db():
    return Database()


def get_journal(db: Annotated[Database, Depends(get_db)]):
    return Journal(db=db)

JournalDep = Annotated[Journal, Depends(get_journal)]
