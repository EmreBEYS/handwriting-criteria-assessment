import io
from collections.abc import Generator
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from app.database import Base, database_is_ready, get_db
from app.main import app
from app.models import Institution, Program, ProgramOutcome, ScanJob, Student, User
from app.processing import _unique_number_match, process_scan
from app.storage import get_object_storage
from fastapi.testclient import TestClient
from handwriting_ml.layout import ExamPaperLayout
from handwriting_ml.recognition import OCRPrediction, UnavailableRecognizer
from PIL import Image, ImageDraw
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


class MemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_put = False

    def put(self, key: str, content: bytes, content_type: str) -> None:
        if self.fail_put:
            raise RuntimeError("storage unavailable")
        self.objects[key] = (content, content_type)

    def get(self, key: str) -> bytes:
        return self.objects[key][0]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
def object_storage() -> MemoryObjectStorage:
    return MemoryObjectStorage()


@pytest.fixture
def client(db_session_factory, object_storage) -> Generator[TestClient, None, None]:
    def override_get_db():
        with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[database_is_ready] = lambda: True
    app.dependency_overrides[get_object_storage] = lambda: object_storage
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


def create_active_exam(client: TestClient, db_session_factory) -> tuple[dict[str, str], dict]:
    headers, offering = create_offering_context(client, db_session_factory)
    with db_session_factory() as session:
        outcome = ProgramOutcome(
            program_id=UUID(offering["program_id"]),
            code="PO1",
            description="Apply engineering knowledge",
        )
        session.add(outcome)
        session.commit()
        outcome_id = str(outcome.id)
    exam = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "midterm", "title": "Midterm", "total_score": "100"},
        headers=headers,
    ).json()["data"]
    question = client.post(
        f"/api/v1/exams/{exam['id']}/questions",
        json={"question_number": 1, "max_score": "100", "display_order": 1},
        headers=headers,
    ).json()["data"]
    client.put(
        f"/api/v1/questions/{question['id']}/program-outcomes",
        json={"outcomes": [{"program_outcome_id": outcome_id, "weight": "1"}]},
        headers=headers,
    )
    activated = client.post(f"/api/v1/exams/{exam['id']}/activate", headers=headers)
    return headers, activated.json()["data"]


def valid_exam_page() -> bytes:
    image = Image.new("RGB", (1654, 2339), "#F0F0F0")
    draw = ImageDraw.Draw(image)
    draw.rectangle((150, 100, 1500, 700), outline="black", width=5)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeRecognizer:
    model_version = "test-handwriting-v1"

    def predict(self, image, field: str) -> OCRPrediction:
        values = {
            "course": OCRPrediction("CENG301 Algorithms", 0.98),
            "name": OCRPrediction("Grace Hopper", 0.96),
            "student_number": OCRPrediction("2026001", 0.99),
            "score": OCRPrediction("100", 0.95),
        }
        return values[field]


def test_student_number_matching_corrects_only_unique_single_digit_error() -> None:
    students = [
        Student(student_number="2026001", first_name="Ada", last_name="Lovelace"),
        Student(student_number="2026123", first_name="Grace", last_name="Hopper"),
    ]

    assert _unique_number_match(students, "2026007") is students[0]

    students.append(Student(student_number="2026008", first_name="Alan", last_name="Turing"))
    assert _unique_number_match(students, "2026007") is None


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
    exams = client.get(f"/api/v1/course-offerings/{offering['id']}/exams", headers=headers)
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
    other_headers = {"Authorization": f"Bearer {other.json()['data']['tokens']['access_token']}"}
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


def test_dynamic_questions_outcome_mapping_and_exam_activation(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    with db_session_factory() as session:
        outcomes = [
            ProgramOutcome(
                program_id=UUID(offering["program_id"]),
                code="PO1",
                description="Apply engineering knowledge",
            ),
            ProgramOutcome(
                program_id=UUID(offering["program_id"]),
                code="PO2",
                description="Design solutions",
            ),
        ]
        session.add_all(outcomes)
        session.commit()
        outcome_ids = [str(outcome.id) for outcome in outcomes]

    available = client.get(
        f"/api/v1/course-offerings/{offering['id']}/program-outcomes",
        headers=headers,
    )
    assert [item["code"] for item in available.json()["data"]] == ["PO1", "PO2"]

    exam = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "midterm", "title": "Midterm", "total_score": "100"},
        headers=headers,
    ).json()["data"]
    first = client.post(
        f"/api/v1/exams/{exam['id']}/questions",
        json={"question_number": 1, "label": "Q1", "max_score": "40", "display_order": 1},
        headers=headers,
    ).json()["data"]
    second = client.post(
        f"/api/v1/exams/{exam['id']}/questions",
        json={"question_number": 2, "label": "Q2", "max_score": "60", "display_order": 2},
        headers=headers,
    ).json()["data"]

    first_mapping = client.put(
        f"/api/v1/questions/{first['id']}/program-outcomes",
        json={
            "outcomes": [
                {"program_outcome_id": outcome_ids[0], "weight": "0.4"},
                {"program_outcome_id": outcome_ids[1], "weight": "0.6"},
            ]
        },
        headers=headers,
    )
    second_mapping = client.put(
        f"/api/v1/questions/{second['id']}/program-outcomes",
        json={"outcomes": [{"program_outcome_id": outcome_ids[1], "weight": "1"}]},
        headers=headers,
    )
    assert first_mapping.status_code == 200
    assert [item["code"] for item in first_mapping.json()["data"]["program_outcomes"]] == [
        "PO1",
        "PO2",
    ]
    assert second_mapping.status_code == 200

    questions = client.get(f"/api/v1/exams/{exam['id']}/questions", headers=headers)
    activated = client.post(f"/api/v1/exams/{exam['id']}/activate", headers=headers)
    assert [item["question_number"] for item in questions.json()["data"]] == [1, 2]
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "active"

    locked_exam = client.patch(
        f"/api/v1/exams/{exam['id']}", json={"title": "Changed"}, headers=headers
    )
    locked_question = client.patch(
        f"/api/v1/questions/{first['id']}", json={"max_score": "30"}, headers=headers
    )
    assert locked_exam.status_code == 409
    assert locked_question.status_code == 409


def test_exam_activation_validates_score_total_and_outcome_weights(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    with db_session_factory() as session:
        institution = session.scalar(select(Institution).where(Institution.code == "EXAMPLE"))
        outcome = ProgramOutcome(
            program_id=UUID(offering["program_id"]),
            code="PO1",
            description="Apply engineering knowledge",
        )
        other_program = Program(
            institution_id=institution.id,
            code="EE",
            name="Electrical Engineering",
        )
        session.add_all([outcome, other_program])
        session.flush()
        foreign_outcome = ProgramOutcome(
            program_id=other_program.id,
            code="PO1",
            description="Apply electrical engineering knowledge",
        )
        session.add(foreign_outcome)
        session.commit()
        outcome_id = str(outcome.id)
        foreign_outcome_id = str(foreign_outcome.id)

    exam = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "final", "title": "Final", "total_score": "100"},
        headers=headers,
    ).json()["data"]
    question = client.post(
        f"/api/v1/exams/{exam['id']}/questions",
        json={"question_number": 1, "max_score": "80", "display_order": 1},
        headers=headers,
    ).json()["data"]

    foreign_mapping = client.put(
        f"/api/v1/questions/{question['id']}/program-outcomes",
        json={"outcomes": [{"program_outcome_id": foreign_outcome_id, "weight": "1"}]},
        headers=headers,
    )
    incomplete_weight = client.put(
        f"/api/v1/questions/{question['id']}/program-outcomes",
        json={"outcomes": [{"program_outcome_id": outcome_id, "weight": "0.5"}]},
        headers=headers,
    )
    total_mismatch = client.post(f"/api/v1/exams/{exam['id']}/activate", headers=headers)
    assert foreign_mapping.status_code == 422
    assert foreign_mapping.json()["error"]["code"] == "INVALID_PROGRAM_OUTCOME"
    assert incomplete_weight.status_code == 422
    assert incomplete_weight.json()["error"]["code"] == "VALIDATION_ERROR"
    assert total_mismatch.status_code == 409
    assert total_mismatch.json()["error"]["code"] == "QUESTION_TOTAL_MISMATCH"

    client.patch(f"/api/v1/questions/{question['id']}", json={"max_score": "100"}, headers=headers)
    missing_mapping = client.post(f"/api/v1/exams/{exam['id']}/activate", headers=headers)
    assert missing_mapping.status_code == 409
    assert missing_mapping.json()["error"]["code"] == "QUESTION_OUTCOMES_INCOMPLETE"


def test_student_crud_normalizes_number_and_supports_deactivation(client: TestClient) -> None:
    headers = authenticated_headers(client)
    created = client.post(
        "/api/v1/students",
        json={"student_number": " 2026abc ", "first_name": "Alan", "last_name": "Turing"},
        headers=headers,
    )

    assert created.status_code == 201
    student = created.json()["data"]
    assert student["student_number"] == "2026ABC"

    duplicate = client.post(
        "/api/v1/students",
        json={"student_number": "2026abc", "first_name": "Other", "last_name": "Student"},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "STUDENT_NUMBER_ALREADY_EXISTS"

    updated = client.patch(
        f"/api/v1/students/{student['id']}",
        json={"last_name": "Mathison", "is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["last_name"] == "Mathison"
    assert updated.json()["data"]["is_active"] is False
    assert client.get("/api/v1/students", headers=headers).json()["data"] == []
    assert (
        len(
            client.get("/api/v1/students", params={"active_only": False}, headers=headers).json()[
                "data"
            ]
        )
        == 1
    )


def test_assigned_instructor_can_manage_course_enrollments(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    student = client.post(
        "/api/v1/students",
        json={"student_number": "2026001", "first_name": "Grace", "last_name": "Hopper"},
        headers=headers,
    ).json()["data"]

    enrolled = client.post(
        f"/api/v1/course-offerings/{offering['id']}/enrollments",
        json={"student_id": student["id"]},
        headers=headers,
    )
    assert enrolled.status_code == 201
    assert enrolled.json()["data"]["student"]["student_number"] == "2026001"

    duplicate = client.post(
        f"/api/v1/course-offerings/{offering['id']}/enrollments",
        json={"student_id": student["id"]},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ENROLLMENT_ALREADY_EXISTS"

    roster = client.get(f"/api/v1/course-offerings/{offering['id']}/enrollments", headers=headers)
    assert [item["student"]["id"] for item in roster.json()["data"]] == [student["id"]]

    removed = client.delete(
        f"/api/v1/course-offerings/{offering['id']}/enrollments/{student['id']}",
        headers=headers,
    )
    assert removed.status_code == 204
    assert (
        client.get(
            f"/api/v1/course-offerings/{offering['id']}/enrollments", headers=headers
        ).json()["data"]
        == []
    )


def test_inactive_student_cannot_be_enrolled(client: TestClient, db_session_factory) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    student = client.post(
        "/api/v1/students",
        json={"student_number": "2026002", "first_name": "Katherine", "last_name": "Johnson"},
        headers=headers,
    ).json()["data"]
    client.patch(f"/api/v1/students/{student['id']}", json={"is_active": False}, headers=headers)

    response = client.post(
        f"/api/v1/course-offerings/{offering['id']}/enrollments",
        json={"student_id": student["id"]},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STUDENT_INACTIVE"


def test_students_and_enrollments_are_isolated_by_institution(
    client: TestClient, db_session_factory
) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    student = client.post(
        "/api/v1/students",
        json={"student_number": "2026003", "first_name": "Edsger", "last_name": "Dijkstra"},
        headers=headers,
    ).json()["data"]

    with db_session_factory() as session:
        session.add(Institution(name="Other University", code="OTHER"))
        session.commit()
    other = client.post(
        "/api/v1/auth/register",
        json=registration_payload()
        | {"institution_code": "OTHER", "email": "instructor@other.edu"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['data']['tokens']['access_token']}"}

    assert client.get(f"/api/v1/students/{student['id']}", headers=other_headers).status_code == 404
    assert (
        client.get(
            f"/api/v1/course-offerings/{offering['id']}/enrollments", headers=other_headers
        ).status_code
        == 404
    )

    with db_session_factory() as session:
        assert session.scalar(select(Student).where(Student.id == UUID(student["id"]))) is not None


def test_active_exam_accepts_idempotent_scan_upload(
    client: TestClient, db_session_factory, object_storage: MemoryObjectStorage
) -> None:
    headers, exam = create_active_exam(client, db_session_factory)
    request_id = "d9766a76-77df-4af6-a0f7-a9f24341c662"
    first = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": request_id},
        files={"image": ("paper.png", b"png-paper-content", "image/png")},
        headers=headers,
    )
    duplicate = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": request_id},
        files={"image": ("retry.png", b"different-content", "image/png")},
        headers=headers,
    )

    assert first.status_code == 202
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["id"] == first.json()["data"]["id"]
    assert first.json()["data"]["status"] == "queued"
    assert first.json()["data"]["image_sha256"]
    assert "image_object_key" not in first.json()["data"]
    assert len(object_storage.objects) == 1

    listed = client.get(f"/api/v1/exams/{exam['id']}/scans", headers=headers)
    fetched = client.get(f"/api/v1/scans/{first.json()['data']['id']}", headers=headers)
    assert [item["id"] for item in listed.json()["data"]] == [first.json()["data"]["id"]]
    assert fetched.json()["data"]["client_request_id"] == request_id


def test_scan_upload_requires_active_assigned_exam(client: TestClient, db_session_factory) -> None:
    headers, offering = create_offering_context(client, db_session_factory)
    exam = client.post(
        f"/api/v1/course-offerings/{offering['id']}/exams",
        json={"type": "midterm", "title": "Draft"},
        headers=headers,
    ).json()["data"]

    draft_response = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": "c91fc6f2-5796-483d-8103-e2e4cbde9b6a"},
        files={"image": ("paper.jpg", b"jpeg", "image/jpeg")},
        headers=headers,
    )
    assert draft_response.status_code == 409
    assert draft_response.json()["error"]["code"] == "EXAM_NOT_ACTIVE"

    other = client.post(
        "/api/v1/auth/register",
        json=registration_payload() | {"email": "grace@example.edu"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['data']['tokens']['access_token']}"}
    hidden = client.get(f"/api/v1/exams/{exam['id']}/scans", headers=other_headers)
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "EXAM_NOT_FOUND"


def test_scan_upload_validates_media_and_storage_availability(
    client: TestClient, db_session_factory, object_storage: MemoryObjectStorage
) -> None:
    headers, exam = create_active_exam(client, db_session_factory)
    invalid = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": "5e43b388-b70b-4508-9fae-ee601f5c9a03"},
        files={"image": ("paper.txt", b"not-an-image", "text/plain")},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_MEDIA_TYPE"

    object_storage.fail_put = True
    unavailable = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": "e599e678-b95f-4e1e-8c98-a860b35e0ebd"},
        files={"image": ("paper.png", b"png", "image/png")},
        headers=headers,
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "OBJECT_STORAGE_UNAVAILABLE"


def test_worker_extracts_predictions_and_matches_enrolled_student(
    client: TestClient, db_session_factory, object_storage: MemoryObjectStorage
) -> None:
    headers, exam = create_active_exam(client, db_session_factory)
    offering_id = exam["course_offering_id"]
    student = client.post(
        "/api/v1/students",
        json={"student_number": "2026001", "first_name": "Grace", "last_name": "Hopper"},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        json={"student_id": student["id"]},
        headers=headers,
    )
    uploaded = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": "f297cb47-f7d1-49e9-b123-1ae12024c6ee"},
        files={"image": ("paper.png", valid_exam_page(), "image/png")},
        headers=headers,
    ).json()["data"]

    layout = ExamPaperLayout.from_json(Path("ml/configs/inonu-engineering-exam-v1.json"))
    with db_session_factory() as session:
        processed = process_scan(
            session, UUID(uploaded["id"]), object_storage, FakeRecognizer(), layout
        )
        assert processed.status == "needs_review"

    result = client.get(f"/api/v1/scans/{uploaded['id']}", headers=headers).json()["data"]
    assert result["status"] == "needs_review"
    assert result["model_version"] == "test-handwriting-v1"
    assert result["paper"]["matched_student_id"] == student["id"]
    assert result["paper"]["resolved_student_name"] == "Grace Hopper"
    assert result["paper"]["predicted_student_name"] is None
    assert result["paper"]["student_name_confidence"] is None
    assert result["paper"]["predicted_course_text"] == "CENG301 Algorithms"
    assert result["paper"]["predicted_total_score"] == "100.000"
    assert result["paper"]["maximum_total_score"] == "100.000"
    assert result["paper"]["review_reasons"] == []
    assert result["paper"]["answers"] == [
        {
            "question_id": result["paper"]["answers"][0]["question_id"],
            "question_number": 1,
            "predicted_score": "100.000",
            "confidence": "0.9500",
            "requires_review": False,
        }
    ]


def test_worker_fails_explicitly_without_model_weights(
    client: TestClient, db_session_factory, object_storage: MemoryObjectStorage
) -> None:
    headers, exam = create_active_exam(client, db_session_factory)
    uploaded = client.post(
        f"/api/v1/exams/{exam['id']}/scans",
        data={"client_request_id": "5a64969c-4df3-49ed-944c-82c310d6ed67"},
        files={"image": ("paper.png", valid_exam_page(), "image/png")},
        headers=headers,
    ).json()["data"]
    layout = ExamPaperLayout.from_json("ml/configs/inonu-engineering-exam-v1.json")

    with db_session_factory() as session:
        process_scan(
            session,
            UUID(uploaded["id"]),
            object_storage,
            UnavailableRecognizer(),
            layout,
        )
        failed = session.get(ScanJob, UUID(uploaded["id"]))
        assert failed.status == "failed"
        assert failed.error_code == "MODEL_NOT_CONFIGURED"


def test_score_parser_rejects_out_of_range_value() -> None:
    from app.processing import _score

    assert _score("7,5", Decimal("10")) == Decimal("7.500")
    assert _score("11", Decimal("10")) is None
