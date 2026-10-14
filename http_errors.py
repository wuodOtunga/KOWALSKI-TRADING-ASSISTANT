import logging
from typing import Literal

from fastapi import HTTPException, status

import exceptions as t

logger: logging.Logger = logging.getLogger(name=__name__)


#The core idea: look up by class, walking the MRO
#The exceptions taxonomy is a tree, so the mapping can be too.
#We map a few parent classes to a status code, and let subclasses inherit it unless you override them.
#Pythons __mro__ lists a class, then its parents in order, so the first hit is always the most specific match.

_DEFAULT_STATUS: dict[type[t.KowalskiError], int] = {
    t.KowalskiError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    t.InternalDomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    t.GradingError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    t.TradeValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    t.ConflictError: status.HTTP_409_CONFLICT,
    t.NotFoundError: status.HTTP_404_NOT_FOUND,
    t.InvalidIdentifierError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    t.UniqueViolationError: status.HTTP_409_CONFLICT,
    t.CheckViolationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    t.NotNullViolationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def status_for(exc: BaseException | None, overrides: dict | None) -> int | Literal[500]:
    table = {**_DEFAULT_STATUS, **(overrides or {})}
    for cls in type(exc).__mro__:
        if cls in table:
            return table[cls]

    return status.HTTP_500_INTERNAL_SERVER_ERROR

#The helper returns an HTTPException rather than raising one,
#so the endpoint writes raise to_http_error(...).
#The existing StarletteHTTPException handler then does the /api vs HTML split for free.
# A separate KowalskiError handler would have to duplicate that branch.

#InvalidIdentifierError depends on where the ID came from.
#A bad model_id in a POST body isnt a missing resource, because the URL is fine and the payload is wrong,
#so 422 is honest. A bad account_id in DELETE /accounts/{account_id} is a 404.
#Thats why overrides exists:
#raise to_http_error(results.error, overrides={t.InvalidIdentifierError: 404})
#Overrides must name the exact class.
#A parent-class override like NotFoundError loses to a more specific default entry,
#because the MRO walk finds the subclass first.

#Status codes for the constraint errors.
#Unique violations are a 409 because the clients data conflicts with existing state.
#Check and not-null violations are 422.
#FK violations stay 500 because your _check_foreign_keys pre-check should catch them first.
#If one reaches the client, thats your bug.
def to_http_error(exc: t.KowalskiError | None, overrides: dict | None = None) -> HTTPException:
    if exc is None:
        logger.error(msg="SERVICE FAILED WITHOUT AN EXCEPTION ATTACHED")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AN INTERNAL ERROR OCCURRED"
        )

    code: int | Literal[500] = status_for(exc, overrides)
    if code >= 500:  # noqa: PLR2004
        logger.error(msg="AN UNHANDLED DOMAIN FAILURE", exc_info=exc)
        detail = "AN INTERNAL ERROR OCCURRED"
    else:
        detail = str(object=exc)

    return HTTPException(status_code=code, detail=detail)
