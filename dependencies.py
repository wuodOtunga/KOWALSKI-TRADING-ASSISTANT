from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from journal import Journal
from repository import Repository


@lru_cache
def get_db() -> Repository:
    return Repository()

def get_journal(db: Annotated[Repository, Depends(dependency=get_db)]) -> Journal:
    return Journal(db=db)

JournalDep = Annotated[Journal, Depends(dependency=get_journal)]
