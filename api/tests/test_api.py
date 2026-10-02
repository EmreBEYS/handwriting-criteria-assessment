from collections.abc import Generator

import pytest
from app.database import Base, database_is_ready, get_db
from app.main import app
from app.models import Institution, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        session.add(Institution(name="Example University", code="EXAMPLE"))
        session.commit()

    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session_factory) -> Generator[TestClient, None, None]:
    def override_get_db():
        with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[database_is_ready] = lambda: True
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def registration_payload() -> dict[str, str]:
    return {
        "institution_code": "example",
        "email": "Instructor@Example.edu",
        "password": "a-strong-test-password",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }


def test_health_reports_model_as_not_ready(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["model_ready"] is False
    assert response.headers["X-Request-ID"]


def test_readiness_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_readiness_uses_standard_error_envelope(client: TestClient) -> None:
    app.dependency_overrides[database_is_ready] = lambda: False

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_analysis_rejects_non_image_upload(client: TestClient) -> None:
    response = client.post("/v1/analyses", files={"image": ("note.txt", b"text", "text/plain")})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MEDIA_TYPE"


def test_analysis_stays_disabled_before_model_decision(client: TestClient) -> None:
    response = client.post("/v1/analyses", files={"image": ("sample.png", b"png", "image/png")})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_NOT_CONFIGURED"


def test_register_hashes_password_and_returns_tokens(
    client: TestClient, db_session_factory
) -> None:
    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["user"]["email"] == "instructor@example.edu"
    assert body["user"]["role"] == "instructor"
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert "password" not in body["user"]

    with db_session_factory() as session:
        user = session.scalar(select(User))
        assert user is not None
        assert user.password_hash != registration_payload()["password"]
        assert user.password_hash.startswith("$argon2")


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    first = client.post("/api/v1/auth/register", json=registration_payload())
    second = client.post("/api/v1/auth/register", json=registration_payload())

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_and_protected_profile(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())

    login = client.post(
        "/api/v1/auth/login",
        json={
            "institution_code": "EXAMPLE",
            "email": "instructor@example.edu",
            "password": "a-strong-test-password",
        },
    )
    access_token = login.json()["data"]["tokens"]["access_token"]
    profile = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert login.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["data"]["first_name"] == "Ada"


def test_invalid_login_does_not_reveal_which_credential_failed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "institution_code": "UNKNOWN",
            "email": "nobody@example.edu",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_refresh_token_rotates_token_pair(client: TestClient) -> None:
    registration = client.post("/api/v1/auth/register", json=registration_payload())
    old_tokens = registration.json()["data"]["tokens"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_tokens["refresh_token"]},
    )

    assert response.status_code == 200
    new_tokens = response.json()["data"]["tokens"]
    assert new_tokens["access_token"] != old_tokens["access_token"]
    assert new_tokens["refresh_token"] != old_tokens["refresh_token"]


def test_refresh_token_cannot_be_used_as_access_token(client: TestClient) -> None:
    registration = client.post("/api/v1/auth/register", json=registration_payload())
    refresh_token = registration.json()["data"]["tokens"]["refresh_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN_TYPE"


def test_protected_profile_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_validation_errors_use_standard_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_route_uses_standard_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
