from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.models import Institution, RefreshSession, User, UserRole
from app.schemas import (
    AuthData,
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserEnvelope,
    UserResponse,
)
from app.security import create_token_pair, decode_token, hash_password, verify_password

router = APIRouter(prefix=settings.api_v1_prefix, tags=["authentication"])
_dummy_password_hash = hash_password("not-a-real-password-for-timing-only")


def _auth_response(db: DBSession, user: User) -> tuple[AuthResponse, RefreshSession]:
    access_token, refresh_token, refresh_jti, refresh_expires_at = create_token_pair(user)
    refresh_session = RefreshSession(
        jti=refresh_jti,
        user_id=user.id,
        expires_at=refresh_expires_at,
    )
    db.add(refresh_session)
    response = AuthResponse(
        data=AuthData(
            user=UserResponse.model_validate(user),
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.access_token_expire_minutes * 60,
            ),
        )
    )
    return response, refresh_session


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Institution not found"}, 409: {"description": "Conflict"}},
)
def register(payload: RegisterRequest, db: DBSession) -> AuthResponse:
    institution = db.scalar(
        select(Institution).where(
            func.lower(Institution.code) == payload.institution_code.casefold()
        )
    )
    if institution is None:
        raise APIError(404, "INSTITUTION_NOT_FOUND", "Institution was not found.")

    existing = db.scalar(
        select(User).where(
            User.institution_id == institution.id,
            func.lower(User.email) == payload.email,
        )
    )
    if existing is not None:
        raise APIError(409, "EMAIL_ALREADY_REGISTERED", "Email is already registered.")

    user = User(
        institution_id=institution.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=UserRole.instructor,
    )
    db.add(user)
    try:
        db.flush()
        response, _ = _auth_response(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "EMAIL_ALREADY_REGISTERED", "Email is already registered.") from exc
    return response


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DBSession) -> AuthResponse:
    user = db.scalar(
        select(User)
        .join(Institution)
        .where(
            func.lower(Institution.code) == payload.institution_code.casefold(),
            func.lower(User.email) == payload.email,
        )
    )

    password_matches = verify_password(
        payload.password,
        user.password_hash if user is not None else _dummy_password_hash,
    )
    if user is None or not password_matches or not user.is_active:
        raise APIError(401, "INVALID_CREDENTIALS", "Email, password, or institution is invalid.")

    user.last_login_at = datetime.now(UTC)
    response, _ = _auth_response(db, user)
    db.commit()
    return response


@router.post("/auth/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, db: DBSession) -> AuthResponse:
    claims = decode_token(payload.refresh_token, "refresh")
    refresh_jti = UUID(claims["jti"])
    refresh_session = db.scalar(
        select(RefreshSession).where(RefreshSession.jti == refresh_jti).with_for_update()
    )
    user = db.scalar(select(User).where(User.id == UUID(claims["sub"])))
    now = datetime.now(UTC)
    expires_at = refresh_session.expires_at if refresh_session is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        user is None
        or not user.is_active
        or str(user.institution_id) != claims["institution_id"]
        or refresh_session is None
        or refresh_session.user_id != user.id
        or refresh_session.revoked_at is not None
        or expires_at is None
        or expires_at <= now
    ):
        raise APIError(401, "INVALID_TOKEN", "Authentication token is invalid or expired.")
    response, replacement = _auth_response(db, user)
    refresh_session.revoked_at = now
    refresh_session.replaced_by_jti = replacement.jti
    db.commit()
    return response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DBSession) -> Response:
    claims = decode_token(payload.refresh_token, "refresh")
    refresh_session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.jti == UUID(claims["jti"]))
        .with_for_update()
    )
    if refresh_session is not None and refresh_session.revoked_at is None:
        refresh_session.revoked_at = datetime.now(UTC)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me", response_model=UserEnvelope, tags=["users"])
def read_current_user(current_user: CurrentUser) -> UserEnvelope:
    return UserEnvelope(data=UserResponse.model_validate(current_user))
