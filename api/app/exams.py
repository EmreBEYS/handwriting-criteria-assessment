from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.models import (
    AcademicTerm,
    CourseInstructor,
    CourseOffering,
    Exam,
    ExamStatus,
    ExamType,
)
from app.schemas import (
    CourseOfferingEnvelope,
    CourseOfferingListEnvelope,
    CourseOfferingResponse,
    ExamCreate,
    ExamEnvelope,
    ExamListEnvelope,
    ExamResponse,
    ExamUpdate,
)

router = APIRouter(prefix=settings.api_v1_prefix, tags=["exams"])


def _offering_query(current_user: CurrentUser):
    return (
        select(CourseOffering, AcademicTerm, CourseInstructor.role)
        .join(AcademicTerm, CourseOffering.academic_term_id == AcademicTerm.id)
        .join(CourseInstructor, CourseInstructor.course_offering_id == CourseOffering.id)
        .where(
            CourseOffering.institution_id == current_user.institution_id,
            CourseInstructor.user_id == current_user.id,
        )
    )


def _offering_response(row) -> CourseOfferingResponse:
    offering, semester, instructor_role = row
    return CourseOfferingResponse(
        id=offering.id,
        course_id=offering.course_id,
        semester_id=offering.academic_term_id,
        academic_year_id=semester.academic_year_id,
        program_id=offering.program_id,
        section_code=offering.section_code,
        instructor_role=instructor_role,
        created_at=offering.created_at,
    )


def _get_assigned_offering(
    db: DBSession, current_user: CurrentUser, offering_id: UUID
) -> CourseOffering:
    row = db.execute(
        _offering_query(current_user).where(CourseOffering.id == offering_id)
    ).one_or_none()
    if row is None:
        raise APIError(404, "COURSE_OFFERING_NOT_FOUND", "Course offering was not found.")
    return row[0]


def _get_exam(db: DBSession, current_user: CurrentUser, exam_id: UUID) -> Exam:
    exam = db.scalar(
        select(Exam)
        .join(CourseOffering, Exam.course_offering_id == CourseOffering.id)
        .join(CourseInstructor, CourseInstructor.course_offering_id == CourseOffering.id)
        .where(
            Exam.id == exam_id,
            CourseOffering.institution_id == current_user.institution_id,
            CourseInstructor.user_id == current_user.id,
        )
    )
    if exam is None:
        raise APIError(404, "EXAM_NOT_FOUND", "Exam was not found.")
    return exam


@router.get("/course-offerings", response_model=CourseOfferingListEnvelope)
def list_course_offerings(
    db: DBSession, current_user: CurrentUser
) -> CourseOfferingListEnvelope:
    rows = db.execute(
        _offering_query(current_user).order_by(
            AcademicTerm.start_year.desc(), CourseOffering.section_code
        )
    ).all()
    return CourseOfferingListEnvelope(data=[_offering_response(row) for row in rows])


@router.get("/course-offerings/{offering_id}", response_model=CourseOfferingEnvelope)
def read_course_offering(
    offering_id: UUID, db: DBSession, current_user: CurrentUser
) -> CourseOfferingEnvelope:
    row = db.execute(
        _offering_query(current_user).where(CourseOffering.id == offering_id)
    ).one_or_none()
    if row is None:
        raise APIError(404, "COURSE_OFFERING_NOT_FOUND", "Course offering was not found.")
    return CourseOfferingEnvelope(data=_offering_response(row))


@router.post(
    "/course-offerings/{offering_id}/exams",
    response_model=ExamEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_exam(
    offering_id: UUID,
    payload: ExamCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamEnvelope:
    offering = _get_assigned_offering(db, current_user, offering_id)
    if payload.replaces_exam_id is not None:
        replaced_exam = _get_exam(db, current_user, payload.replaces_exam_id)
        if (
            replaced_exam.course_offering_id != offering.id
            or replaced_exam.type != ExamType.final
        ):
            raise APIError(
                422,
                "INVALID_REPLACEMENT_EXAM",
                "A makeup exam can only replace a final from the same course offering.",
            )

    exam = Exam(
        course_offering_id=offering.id,
        type=payload.type,
        title=payload.title,
        total_score=payload.total_score,
        held_at=payload.held_at,
        replaces_exam_id=payload.replaces_exam_id,
        created_by=current_user.id,
    )
    db.add(exam)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "EXAM_ALREADY_EXISTS", "Exam already exists.") from exc
    db.refresh(exam)
    return ExamEnvelope(data=ExamResponse.model_validate(exam))


@router.get(
    "/course-offerings/{offering_id}/exams", response_model=ExamListEnvelope
)
def list_exams(
    offering_id: UUID, db: DBSession, current_user: CurrentUser
) -> ExamListEnvelope:
    offering = _get_assigned_offering(db, current_user, offering_id)
    exams = db.scalars(
        select(Exam)
        .where(Exam.course_offering_id == offering.id)
        .order_by(Exam.held_at, Exam.created_at)
    ).all()
    return ExamListEnvelope(data=[ExamResponse.model_validate(exam) for exam in exams])


@router.get("/exams/{exam_id}", response_model=ExamEnvelope)
def read_exam(exam_id: UUID, db: DBSession, current_user: CurrentUser) -> ExamEnvelope:
    return ExamEnvelope(data=ExamResponse.model_validate(_get_exam(db, current_user, exam_id)))


@router.patch("/exams/{exam_id}", response_model=ExamEnvelope)
def update_exam(
    exam_id: UUID,
    payload: ExamUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    if exam.status != ExamStatus.draft:
        raise APIError(409, "EXAM_NOT_DRAFT", "Only a draft exam can be changed.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exam, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "EXAM_ALREADY_EXISTS", "Exam already exists.") from exc
    db.refresh(exam)
    return ExamEnvelope(data=ExamResponse.model_validate(exam))


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: UUID, db: DBSession, current_user: CurrentUser) -> Response:
    exam = _get_exam(db, current_user, exam_id)
    if exam.status != ExamStatus.draft:
        raise APIError(409, "EXAM_NOT_DRAFT", "Only a draft exam can be deleted.")
    db.delete(exam)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
