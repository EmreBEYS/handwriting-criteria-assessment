from collections.abc import Generator

import pytest
from app.database import Base, database_is_ready, get_db
from app.main import app
from app.models import Institution, Program, User
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


def authenticated_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json=registration_payload())
    token = response.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_offering_context(client: TestClient, db_session_factory) -> tuple[dict[str, str], dict]:
    headers = authenticated_headers(client)
    year = client.post(
        "/api/v1/academic-years", json={"start_year": 2026}, headers=headers
    ).json()["data"]
    semester = client.post(
        "/api/v1/semesters",
        json={"academic_year_id": year["id"], "season": "fall"},
        headers=headers,
    ).json()["data"]
    with db_session_factory() as session:
        institution = session.scalar(select(Institution).where(Institution.code == "EXAMPLE"))
        program = Program(
            institution_id=institution.id,
            code="CENG",
            name="Computer Engineering",
        )
        session.add(program)
        session.commit()
        program_id = program.id
    course = client.post(
        "/api/v1/courses",
        json={"code": "CENG301", "name": "Algorithms"},
        headers=headers,
    ).json()["data"]
    offering = client.post(
        "/api/v1/course-offerings",
        json={
            "course_id": course["id"],
            "semester_id": semester["id"],
            "program_id": str(program_id),
            "section_code": "1",
        },
        headers=headers,
    ).json()["data"]
    return headers, offering


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


def test_academic_structure_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/academic-years")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_academic_year_and_semester_crud(client: TestClient) -> None:
    headers = authenticated_headers(client)
    year_response = client.post(
        "/api/v1/academic-years", json={"start_year": 2026}, headers=headers
    )

    assert year_response.status_code == 201
    year = year_response.json()["data"]
    assert year["label"] == "2026–2027"

    semester_response = client.post(
        "/api/v1/semesters",
        json={
            "academic_year_id": year["id"],
            "season": "fall",
            "starts_on": "2026-09-21",
            "ends_on": "2027-01-15",
        },
        headers=headers,
    )
    assert semester_response.status_code == 201
    semester = semester_response.json()["data"]
    assert semester["start_year"] == 2026

    semesters = client.get(
        "/api/v1/semesters",
        params={"academic_year_id": year["id"]},
        headers=headers,
    )
    assert [item["id"] for item in semesters.json()["data"]] == [semester["id"]]

    update = client.patch(
        f"/api/v1/semesters/{semester['id']}",
        json={"ends_on": "2027-01-22"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["data"]["ends_on"] == "2027-01-22"

    assert client.delete(f"/api/v1/semesters/{semester['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/academic-years/{year['id']}", headers=headers).status_code == 204


def test_academic_structure_validates_duplicates_and_date_ranges(client: TestClient) -> None:
    headers = authenticated_headers(client)
    first = client.post("/api/v1/academic-years", json={"start_year": 2026}, headers=headers)
    duplicate = client.post("/api/v1/academic-years", json={"start_year": 2026}, headers=headers)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ACADEMIC_YEAR_ALREADY_EXISTS"

    invalid_semester = client.post(
        "/api/v1/semesters",
        json={
            "academic_year_id": first.json()["data"]["id"],
            "season": "fall",
            "starts_on": "2027-01-01",
            "ends_on": "2026-09-01",
        },
        headers=headers,
    )
    assert invalid_semester.status_code == 422
    assert invalid_semester.json()["error"]["code"] == "VALIDATION_ERROR"


def test_academic_resources_are_isolated_by_institution(
    client: TestClient, db_session_factory
) -> None:
    first_headers = authenticated_headers(client)
    year = client.post(
        "/api/v1/academic-years", json={"start_year": 2026}, headers=first_headers
    ).json()["data"]

    with db_session_factory() as session:
        session.add(Institution(name="Other University", code="OTHER"))
        session.commit()

    second_registration = registration_payload() | {
        "institution_code": "OTHER",
        "email": "instructor@other.edu",
    }
    second_response = client.post("/api/v1/auth/register", json=second_registration)
    second_headers = {
        "Authorization": f"Bearer {second_response.json()['data']['tokens']['access_token']}"
    }

    response = client.get(f"/api/v1/academic-years/{year['id']}", headers=second_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACADEMIC_YEAR_NOT_FOUND"


def test_courses_can_be_filtered_by_academic_year_and_semester(
    client: TestClient, db_session_factory
) -> None:
    headers = authenticated_headers(client)
    year = client.post("/api/v1/academic-years", json={"start_year": 2026}, headers=headers).json()[
        "data"
    ]
    semester = client.post(
        "/api/v1/semesters",
        json={"academic_year_id": year["id"], "season": "fall"},
        headers=headers,
    ).json()["data"]

    with db_session_factory() as session:
        institution = session.scalar(select(Institution).where(Institution.code == "EXAMPLE"))
        program = Program(
            institution_id=institution.id,
            code="CENG",
            name="Computer Engineering",
        )
        session.add(program)
        session.commit()
        program_id = program.id

    algorithms = client.post(
        "/api/v1/courses",
        json={"code": "ceng301", "name": "Algorithms"},
        headers=headers,
    )
    databases = client.post(
        "/api/v1/courses",
        json={"code": "CENG302", "name": "Databases"},
        headers=headers,
    )
    assert algorithms.status_code == 201
    assert algorithms.json()["data"]["code"] == "CENG301"
    assert databases.status_code == 201

    offering = client.post(
        "/api/v1/course-offerings",
        json={
            "course_id": algorithms.json()["data"]["id"],
            "semester_id": semester["id"],
            "program_id": str(program_id),
            "section_code": "1",
        },
        headers=headers,
    )
    assert offering.status_code == 201
    assert offering.json()["data"]["instructor_role"] == "owner"

    by_year = client.get(
        "/api/v1/courses", params={"academic_year_id": year["id"]}, headers=headers
    )
    by_semester = client.get(
        "/api/v1/courses", params={"semester_id": semester["id"]}, headers=headers
    )
    assert [course["code"] for course in by_year.json()["data"]] == ["CENG301"]
    assert [course["code"] for course in by_semester.json()["data"]] == ["CENG301"]

    other_registration = registration_payload() | {"email": "grace@example.edu"}
    other_response = client.post("/api/v1/auth/register", json=other_registration)
    other_headers = {
        "Authorization": f"Bearer {other_response.json()['data']['tokens']['access_token']}"
    }
    other_instructor_courses = client.get(
        "/api/v1/courses",
        params={"semester_id": semester["id"]},
        headers=other_headers,
    )
    assert other_instructor_courses.json()["data"] == []

    delete_course = client.delete(
        f"/api/v1/courses/{algorithms.json()['data']['id']}", headers=headers
    )
    delete_semester = client.delete(f"/api/v1/semesters/{semester['id']}", headers=headers)
    assert delete_course.status_code == 409
    assert delete_course.json()["error"]["code"] == "COURSE_IN_USE"
    assert delete_semester.status_code == 409
    assert delete_semester.json()["error"]["code"] == "SEMESTER_IN_USE"


def test_exam_crud_for_assigned_course_offering(client: TestClient, db_session_factory) -> None:
    headers, offering = create_offering_context(client, db_session_factory)

    created = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={
            "type": "midterm",
            "title": "Midterm 1",
            "total_score": "100.000",
            "held_at": "2026-11-09T10:00:00Z",
        },
        headers=headers,
    )
    assert created.status_code == 201
    exam = created.json()["data"]
    assert exam["status"] == "draft"
    assert exam["total_score"] == "100.000"

    offerings = client.get("/api/v1/course-offerings", headers=headers)
    exams = client.get(
        f"/api/v1/course-offerings/{offering['id']}/exams", headers=headers
    )
    assert [item["id"] for item in offerings.json()["data"]] == [offering["id"]]
    assert [item["id"] for item in exams.json()["data"]] == [exam["id"]]

    updated = client.patch(
        f"/api/v1/exams/{exam['id']}",
        json={"title": "First Midterm", "total_score": "80"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "First Midterm"
    assert updated.json()["data"]["total_score"] == "80.000"
    assert client.delete(f"/api/v1/exams/{exam['id']}", headers=headers).status_code == 204


def test_exams_are_hidden_from_unassigned_instructors(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    exam = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "final", "title": "Final"},
        headers=headers,
    ).json()["data"]

    other = client.post(
        "/api/v1/auth/register",
        json=registration_payload() | {"email": "grace@example.edu"},
    )
    other_headers = {
        "Authorization": f"Bearer {other.json()['data']['tokens']['access_token']}"
    }
    offering_response = client.get(
        f"/api/v1/course-offerings/{offering['id']}", headers=other_headers
    )
    exam_response = client.get(f"/api/v1/exams/{exam['id']}", headers=other_headers)

    assert offering_response.status_code == 404
    assert exam_response.status_code == 404
    assert exam_response.json()["error"]["code"] == "EXAM_NOT_FOUND"


def test_makeup_exam_can_only_replace_final_in_same_offering(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    midterm = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "midterm", "title": "Midterm"},
        headers=headers,
    ).json()["data"]
    final = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "final", "title": "Final"},
        headers=headers,
    ).json()["data"]

    invalid = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "makeup", "title": "Invalid Makeup", "replaces_exam_id": midterm["id"]},
        headers=headers,
    )
    valid = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "makeup", "title": "Makeup", "replaces_exam_id": final["id"]},
        headers=headers,
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_REPLACEMENT_EXAM"
    assert valid.status_code == 201
    assert valid.json()["data"]["replaces_exam_id"] == final["id"]
