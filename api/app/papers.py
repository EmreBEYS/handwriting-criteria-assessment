from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_exam
from app.models import (
    AuditEvent,
    Enrollment,
    ExamPaper,
    ExamQuestion,
    PaperAnswer,
    PaperStatus,
    ScanJob,
    ScanStatus,
    Student,
)
from app.schemas import (
    ConfirmedAnswerResponse,
    ExamPaperConfirmation,
    ExamPaperConfirmationEnvelope,
    ExamPaperConfirmationResponse,
)

router = APIRouter(prefix=settings.api_v1_prefix, tags=["papers"])


@router.post("/papers/{paper_id}/confirm", response_model=ExamPaperConfirmationEnvelope)
def confirm_paper(
    paper_id: UUID,
    payload: ExamPaperConfirmation,
    db: DBSession,
    current_user: CurrentUser,
) -> ExamPaperConfirmationEnvelope:
    paper = db.get(ExamPaper, paper_id)
    if paper is None:
        raise APIError(404, "PAPER_NOT_FOUND", "Exam paper was not found.")
    exam = _get_exam(db, current_user, paper.exam_id)
    if paper.status != PaperStatus.needs_review:
        raise APIError(
            409, "PAPER_NOT_REVIEWABLE", "Only a paper awaiting review can be confirmed."
        )

    student = db.scalar(
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(
            Student.id == payload.student_id,
            Student.institution_id == current_user.institution_id,
            Student.is_active.is_(True),
            Enrollment.course_offering_id == exam.course_offering_id,
            Enrollment.is_active.is_(True),
        )
    )
    if student is None:
        raise APIError(
            422, "STUDENT_NOT_ENROLLED", "Student is not active in this course offering."
        )

    existing = db.scalar(
        select(ExamPaper.id).where(
            ExamPaper.exam_id == exam.id,
            ExamPaper.student_id == student.id,
            ExamPaper.id != paper.id,
            ExamPaper.status.in_([PaperStatus.needs_review, PaperStatus.confirmed]),
        )
    )
    if existing is not None:
        raise APIError(409, "DUPLICATE_STUDENT_PAPER", "Student already has a paper for this exam.")

    rows = db.execute(
        select(PaperAnswer, ExamQuestion)
        .join(ExamQuestion, PaperAnswer.exam_question_id == ExamQuestion.id)
        .where(PaperAnswer.exam_paper_id == paper.id, ExamQuestion.exam_id == exam.id)
        .order_by(ExamQuestion.display_order)
    ).all()
    supplied = {
        answer.question_id: answer.final_score.quantize(Decimal("0.001"))
        for answer in payload.answers
    }
    expected = {question.id for _, question in rows}
    if set(supplied) != expected:
        raise APIError(
            422,
            "INCOMPLETE_ANSWERS",
            "A final score must be supplied exactly once for every exam question.",
        )
    for _, question in rows:
        if supplied[question.id] > question.max_score:
            raise APIError(
                422,
                "SCORE_EXCEEDS_MAXIMUM",
                f"Question {question.question_number} score exceeds its maximum.",
            )

    now = datetime.now(UTC)
    changes: list[dict[str, str | int | None]] = []
    for answer, question in rows:
        final_score = supplied[question.id]
        predicted = answer.predicted_score
        if predicted != final_score:
            changes.append(
                {
                    "question_number": question.question_number,
                    "predicted_score": str(predicted) if predicted is not None else None,
                    "final_score": str(final_score),
                }
            )
        answer.final_score = final_score
        answer.requires_review = False
        answer.reviewed_by = current_user.id
        answer.reviewed_at = now

    previous_student_id = paper.student_id
    paper.student_id = student.id
    paper.status = PaperStatus.confirmed
    paper.confirmed_by = current_user.id
    paper.confirmed_at = now
    scan = db.get(ScanJob, paper.scan_job_id)
    if scan is None:
        raise APIError(409, "SCAN_NOT_FOUND", "Paper does not have a scan job.")
    scan.status = ScanStatus.saved
    scan.saved_at = now
    db.add(
        AuditEvent(
            institution_id=current_user.institution_id,
            actor_user_id=current_user.id,
            event_type="exam_paper.confirmed",
            entity_type="exam_paper",
            entity_id=paper.id,
            payload={
                "previous_student_id": str(previous_student_id) if previous_student_id else None,
                "student_id": str(student.id),
                "answer_changes": changes,
                "correction_reason": payload.correction_reason,
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "DUPLICATE_STUDENT_PAPER", "Student already has a paper for this exam."
        ) from exc

    answer_responses = [
        ConfirmedAnswerResponse(
            question_id=question.id,
            question_number=question.question_number,
            final_score=supplied[question.id],
            maximum_score=question.max_score,
        )
        for _, question in rows
    ]
    return ExamPaperConfirmationEnvelope(
        data=ExamPaperConfirmationResponse(
            paper_id=paper.id,
            scan_id=scan.id,
            status="saved",
            student_id=student.id,
            total_score=sum((item.final_score for item in answer_responses), Decimal("0")),
            maximum_total_score=exam.total_score,
            saved_at=now,
            answers=answer_responses,
        )
    )
