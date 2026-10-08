from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_assigned_offering
from app.models import Enrollment, Student
from app.schemas import (
    EnrollmentCreate,
    EnrollmentEnvelope,
    EnrollmentListEnvelope,
    EnrollmentResponse,
    StudentCreate,
    StudentEnvelope,
    StudentListEnvelope,
    StudentResponse,
    StudentUpdate,
)

router = APIRouter(prefix=settings.api_v1_prefix, tags=["students"])


def _get_student(db: DBSession, current_user: CurrentUser, student_id: UUID) -> Student:
    student = db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.institution_id == current_user.institution_id,
        )
    )
    if student is None:
        raise APIError(404, "STUDENT_NOT_FOUND", "Student was not found.")
    return student


def _enrollment_response(enrollment: Enrollment, student: Student) -> EnrollmentResponse:
    return EnrollmentResponse(
        course_offering_id=enrollment.course_offering_id,
        student=StudentResponse.model_validate(student),
        enrolled_at=enrollment.enrolled_at,
        is_active=enrollment.is_active,
    )


@router.post("/students", response_model=StudentEnvelope, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate, db: DBSession, current_user: CurrentUser
) -> StudentEnvelope:
    student = Student(institution_id=current_user.institution_id, **payload.model_dump())
    db.add(student)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "STUDENT_NUMBER_ALREADY_EXISTS", "Student number already exists."
        ) from exc
    db.refresh(student)
    return StudentEnvelope(data=StudentResponse.model_validate(student))


@router.get("/students", response_model=StudentListEnvelope)
def list_students(
    db: DBSession,
    current_user: CurrentUser,
    active_only: bool = Query(default=True),
) -> StudentListEnvelope:
    query = select(Student).where(Student.institution_id == current_user.institution_id)
    if active_only:
        query = query.where(Student.is_active.is_(True))
    students = db.scalars(query.order_by(Student.student_number)).all()
    return StudentListEnvelope(
        data=[StudentResponse.model_validate(student) for student in students]
    )


@router.get("/students/{student_id}", response_model=StudentEnvelope)
def read_student(
    student_id: UUID, db: DBSession, current_user: CurrentUser
) -> StudentEnvelope:
    return StudentEnvelope(
        data=StudentResponse.model_validate(_get_student(db, current_user, student_id))
    )


@router.patch("/students/{student_id}", response_model=StudentEnvelope)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> StudentEnvelope:
    student = _get_student(db, current_user, student_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "STUDENT_NUMBER_ALREADY_EXISTS", "Student number already exists."
        ) from exc
    db.refresh(student)
    return StudentEnvelope(data=StudentResponse.model_validate(student))


@router.post(
    "/course-offerings/{offering_id}/enrollments",
    response_model=EnrollmentEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    offering_id: UUID,
    payload: EnrollmentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> EnrollmentEnvelope:
    offering = _get_assigned_offering(db, current_user, offering_id)
    student = _get_student(db, current_user, payload.student_id)
    if not student.is_active:
        raise APIError(409, "STUDENT_INACTIVE", "An inactive student cannot be enrolled.")

    enrollment = db.get(Enrollment, (offering.id, student.id))
    if enrollment is None:
        enrollment = Enrollment(course_offering_id=offering.id, student_id=student.id)
        db.add(enrollment)
    elif enrollment.is_active:
        raise APIError(409, "ENROLLMENT_ALREADY_EXISTS", "Enrollment already exists.")
    else:
        enrollment.is_active = True

    db.commit()
    db.refresh(enrollment)
    return EnrollmentEnvelope(data=_enrollment_response(enrollment, student))


@router.get(
    "/course-offerings/{offering_id}/enrollments", response_model=EnrollmentListEnvelope
)
def list_enrollments(
    offering_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    active_only: bool = Query(default=True),
) -> EnrollmentListEnvelope:
    offering = _get_assigned_offering(db, current_user, offering_id)
    query = (
        select(Enrollment, Student)
        .join(Student, Enrollment.student_id == Student.id)
        .where(
            Enrollment.course_offering_id == offering.id,
            Student.institution_id == current_user.institution_id,
        )
    )
    if active_only:
        query = query.where(Enrollment.is_active.is_(True), Student.is_active.is_(True))
    rows = db.execute(query.order_by(Student.student_number)).all()
    return EnrollmentListEnvelope(
        data=[_enrollment_response(enrollment, student) for enrollment, student in rows]
    )


@router.delete(
    "/course-offerings/{offering_id}/enrollments/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_enrollment(
    offering_id: UUID,
    student_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    offering = _get_assigned_offering(db, current_user, offering_id)
    _get_student(db, current_user, student_id)
    enrollment = db.get(Enrollment, (offering.id, student_id))
    if enrollment is None or not enrollment.is_active:
        raise APIError(404, "ENROLLMENT_NOT_FOUND", "Enrollment was not found.")
    enrollment.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
