from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_assigned_offering, _get_exam
from app.models import (
    CourseOffering,
    ExamQuestion,
    ExamStatus,
    ProgramOutcome,
    QuestionProgramOutcome,
)
from app.schemas import (
    ExamEnvelope,
    ExamQuestionCreate,
    ExamQuestionEnvelope,
    ExamQuestionListEnvelope,
    ExamQuestionResponse,
    ExamQuestionUpdate,
    ExamResponse,
    ProgramOutcomeListEnvelope,
    ProgramOutcomeResponse,
    QuestionOutcomeResponse,
    QuestionOutcomeSet,
)

router = APIRouter(prefix=settings.api_v1_prefix, tags=["exam questions"])


def _require_draft(exam) -> None:
    if exam.status != ExamStatus.draft:
        raise APIError(409, "EXAM_NOT_DRAFT", "Only a draft exam can be configured.")


def _get_question(
    db: DBSession, current_user: CurrentUser, question_id: UUID
) -> ExamQuestion:
    question = db.scalar(select(ExamQuestion).where(ExamQuestion.id == question_id))
    if question is None:
        raise APIError(404, "EXAM_QUESTION_NOT_FOUND", "Exam question was not found.")
    _get_exam(db, current_user, question.exam_id)
    return question


def _question_response(db: DBSession, question: ExamQuestion) -> ExamQuestionResponse:
    outcome_rows = db.execute(
        select(QuestionProgramOutcome, ProgramOutcome)
        .join(
            ProgramOutcome,
            QuestionProgramOutcome.program_outcome_id == ProgramOutcome.id,
        )
        .where(QuestionProgramOutcome.exam_question_id == question.id)
        .order_by(ProgramOutcome.code)
    ).all()
    return ExamQuestionResponse(
        id=question.id,
        exam_id=question.exam_id,
        question_number=question.question_number,
        label=question.label,
        max_score=question.max_score,
        display_order=question.display_order,
        program_outcomes=[
            QuestionOutcomeResponse(
                program_outcome_id=outcome.id,
                code=outcome.code,
                description=outcome.description,
                weight=mapping.weight,
            )
            for mapping, outcome in outcome_rows
        ],
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.get(
    "/course-offerings/{offering_id}/program-outcomes",
    response_model=ProgramOutcomeListEnvelope,
)
def list_program_outcomes(
    offering_id: UUID, db: DBSession, current_user: CurrentUser
) -> ProgramOutcomeListEnvelope:
    offering = _get_assigned_offering(db, current_user, offering_id)
    outcomes = db.scalars(
        select(ProgramOutcome)
        .where(
            ProgramOutcome.program_id == offering.program_id,
            ProgramOutcome.is_active.is_(True),
        )
        .order_by(ProgramOutcome.code)
    ).all()
    return ProgramOutcomeListEnvelope(
        data=[ProgramOutcomeResponse.model_validate(outcome) for outcome in outcomes]
    )


@router.post(
    "/exams/{exam_id}/questions",
    response_model=ExamQuestionEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    exam_id: UUID,
    payload: ExamQuestionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamQuestionEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    _require_draft(exam)
    if payload.max_score > exam.total_score:
        raise APIError(
            422,
            "QUESTION_SCORE_EXCEEDS_EXAM_TOTAL",
            "Question score cannot exceed the exam total.",
        )
    question = ExamQuestion(exam_id=exam.id, **payload.model_dump())
    db.add(question)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409,
            "EXAM_QUESTION_ALREADY_EXISTS",
            "Question number and display order must be unique within the exam.",
        ) from exc
    db.refresh(question)
    return ExamQuestionEnvelope(data=_question_response(db, question))


@router.get("/exams/{exam_id}/questions", response_model=ExamQuestionListEnvelope)
def list_questions(
    exam_id: UUID, db: DBSession, current_user: CurrentUser
) -> ExamQuestionListEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    questions = db.scalars(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == exam.id)
        .order_by(ExamQuestion.display_order)
    ).all()
    return ExamQuestionListEnvelope(
        data=[_question_response(db, question) for question in questions]
    )


@router.get("/questions/{question_id}", response_model=ExamQuestionEnvelope)
def read_question(
    question_id: UUID, db: DBSession, current_user: CurrentUser
) -> ExamQuestionEnvelope:
    return ExamQuestionEnvelope(
        data=_question_response(db, _get_question(db, current_user, question_id))
    )


@router.patch("/questions/{question_id}", response_model=ExamQuestionEnvelope)
def update_question(
    question_id: UUID,
    payload: ExamQuestionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamQuestionEnvelope:
    question = _get_question(db, current_user, question_id)
    exam = _get_exam(db, current_user, question.exam_id)
    _require_draft(exam)
    values = payload.model_dump(exclude_unset=True)
    if values.get("max_score", question.max_score) > exam.total_score:
        raise APIError(
            422,
            "QUESTION_SCORE_EXCEEDS_EXAM_TOTAL",
            "Question score cannot exceed the exam total.",
        )
    for field, value in values.items():
        setattr(question, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409,
            "EXAM_QUESTION_ALREADY_EXISTS",
            "Question number and display order must be unique within the exam.",
        ) from exc
    db.refresh(question)
    return ExamQuestionEnvelope(data=_question_response(db, question))


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: UUID, db: DBSession, current_user: CurrentUser
) -> Response:
    question = _get_question(db, current_user, question_id)
    exam = _get_exam(db, current_user, question.exam_id)
    _require_draft(exam)
    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/questions/{question_id}/program-outcomes",
    response_model=ExamQuestionEnvelope,
)
def replace_question_outcomes(
    question_id: UUID,
    payload: QuestionOutcomeSet,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamQuestionEnvelope:
    question = _get_question(db, current_user, question_id)
    exam = _get_exam(db, current_user, question.exam_id)
    _require_draft(exam)
    offering = db.get(CourseOffering, exam.course_offering_id)
    requested_ids = {item.program_outcome_id for item in payload.outcomes}
    valid_ids = set(
        db.scalars(
            select(ProgramOutcome.id).where(
                ProgramOutcome.id.in_(requested_ids),
                ProgramOutcome.program_id == offering.program_id,
                ProgramOutcome.is_active.is_(True),
            )
        ).all()
    )
    if valid_ids != requested_ids:
        raise APIError(
            422,
            "INVALID_PROGRAM_OUTCOME",
            "Every program outcome must be active and belong to the course program.",
        )

    db.execute(
        delete(QuestionProgramOutcome).where(
            QuestionProgramOutcome.exam_question_id == question.id
        )
    )
    db.add_all(
        [
            QuestionProgramOutcome(
                exam_question_id=question.id,
                program_outcome_id=item.program_outcome_id,
                weight=item.weight,
            )
            for item in payload.outcomes
        ]
    )
    db.commit()
    return ExamQuestionEnvelope(data=_question_response(db, question))


@router.post("/exams/{exam_id}/activate", response_model=ExamEnvelope)
def activate_exam(
    exam_id: UUID, db: DBSession, current_user: CurrentUser
) -> ExamEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    _require_draft(exam)
    questions = db.scalars(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)
    ).all()
    if not questions:
        raise APIError(409, "EXAM_HAS_NO_QUESTIONS", "Exam must have at least one question.")

    question_total = sum((question.max_score for question in questions), Decimal("0"))
    if question_total != exam.total_score:
        raise APIError(
            409,
            "QUESTION_TOTAL_MISMATCH",
            "Question maximum scores must total the exam score.",
        )
    for question in questions:
        outcome_total = db.scalar(
            select(func.coalesce(func.sum(QuestionProgramOutcome.weight), 0)).where(
                QuestionProgramOutcome.exam_question_id == question.id
            )
        )
        if Decimal(outcome_total) != Decimal("1"):
            raise APIError(
                409,
                "QUESTION_OUTCOMES_INCOMPLETE",
                "Every question must have program outcome weights totaling 1.",
            )

    exam.status = ExamStatus.active
    db.commit()
    db.refresh(exam)
    return ExamEnvelope(data=ExamResponse.model_validate(exam))
