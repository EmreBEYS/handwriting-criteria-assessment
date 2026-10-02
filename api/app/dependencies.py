from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import APIError
from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)
DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise APIError(401, "AUTHENTICATION_REQUIRED", "A bearer access token is required.")

    payload = decode_token(credentials.credentials, "access")
    user = db.scalar(select(User).where(User.id == UUID(payload["sub"])))
    if (
        user is None
        or not user.is_active
        or str(user.institution_id) != payload["institution_id"]
    ):
        raise APIError(401, "INVALID_TOKEN", "Authentication token is invalid or expired.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
