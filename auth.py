from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from config import settings

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")

#creates a password hasher using argon2 with the recommended settings
#.recommended() gives us secure defaults so that we don't have to configure,
#anything ourselves.
def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expire_delta: timedelta | None = None) -> str:
    """CREATE A JWT ACCESS TOKEN"""
    to_encode = data.copy()

    if expire_delta:
        expire_minutes: datetime = datetime.now(tz=UTC) + expire_delta
    else:
        expire_minutes = datetime.now(tz=UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire_minutes})

    encoded_jwt = jwt.encode(
        payload=to_encode,
        key=settings.secret_str.get_secret_value(),
        algorithm=settings.algorithm
    )

    return encoded_jwt

def verify_access_token(token: str) -> str | None:
    """VERIFY A JWT ACCESS TOKEN AND RETURN THE SUBJECT (USER_ID) IF VALID"""
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.secret_str.get_secret_value(),
            algorithms=settings.algorithm,
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")


