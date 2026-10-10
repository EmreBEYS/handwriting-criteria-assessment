from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.config import settings
from app.errors import APIError
from app.models import User

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def create_token(
    user: User,
    token_type: Literal["access", "refresh"],
    *,
    now: datetime | None = None,
    jti: UUID | None = None,
) -> str:
    now = now or datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    claims = {
        "sub": str(user.id),
        "institution_id": str(user.institution_id),
        "role": user.role.value,
        "type": token_type,
        "jti": str(jti or uuid4()),
        "iat": now,
        "exp": now + lifetime,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(user: User) -> tuple[str, str, UUID, datetime]:
    now = datetime.now(UTC)
    refresh_jti = uuid4()
    refresh_expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    return (
        create_token(user, "access", now=now),
        create_token(user, "refresh", now=now, jti=refresh_jti),
        refresh_jti,
        refresh_expires_at,
    )


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "institution_id", "type", "exp", "iat", "jti"]},
        )
        UUID(payload["sub"])
        UUID(payload["institution_id"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise APIError(401, "INVALID_TOKEN", "Authentication token is invalid or expired.") from exc

    if payload["type"] != expected_type:
        raise APIError(401, "INVALID_TOKEN_TYPE", "Authentication token type is invalid.")
    return payload
