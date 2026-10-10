import hashlib
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_exam
from app.models import (
    Exam,
    ExamPaper,
    ExamQuestion,
    ExamStatus,
    PaperAnswer,
    ScanJob,
    ScanStatus,
    Student,
)
from app.schemas import (
    ExamPaperPredictionResponse,
    PaperAnswerPredictionResponse,
    ScanJobEnvelope,
    ScanJobListEnvelope,
    ScanJobResponse,
)
from app.storage import ObjectStorage, get_object_storage

router = APIRouter(prefix=settings.api_v1_prefix, tags=["scans"])
Storage = Annotated[ObjectStorage, Depends(get_object_storage)]

ALLOWED_IMAGE_TYPES = {
    "image/heic": "heic",
    "image/heif": "heif",
    "image/jpeg": "jpg",
    "image/png": "png",
}


def _has_valid_image_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type in {"image/heic", "image/heif"}:
        return (
            len(content) >= 12
            and content[4:8] == b"ftyp"
            and content[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
        )
    return False


def _get_scan(db: DBSession, current_user: CurrentUser, scan_id: UUID) -> ScanJob:
    scan = db.scalar(select(ScanJob).where(ScanJob.id == scan_id))
    if scan is None:
        raise APIError(404, "SCAN_NOT_FOUND", "Scan job was not found.")
    _get_exam(db, current_user, scan.exam_id)
    return scan


def _scan_response(db: DBSession, scan: ScanJob) -> ScanJobResponse:
    response = ScanJobResponse.model_validate(scan)
    paper = db.scalar(select(ExamPaper).where(ExamPaper.scan_job_id == scan.id))
    if paper is None:
        return response
    matched_student = db.get(Student, paper.student_id) if paper.student_id else None
    exam = db.get(Exam, paper.exam_id)
    if exam is None:
        raise RuntimeError("Exam paper references a missing exam")
    answer_rows = db.execute(
        select(PaperAnswer, ExamQuestion)
        .join(ExamQuestion, PaperAnswer.exam_question_id == ExamQuestion.id)
        .where(PaperAnswer.exam_paper_id == paper.id)
        .order_by(ExamQuestion.display_order)
    ).all()
    predicted_total = (
        sum((answer.predicted_score for answer, _ in answer_rows), start=0)
        if answer_rows and all(answer.predicted_score is not None for answer, _ in answer_rows)
        else None
    )
    paper_response = ExamPaperPredictionResponse(
        id=paper.id,
        matched_student_id=paper.student_id,
        resolved_student_name=(
            f"{matched_student.first_name} {matched_student.last_name}"
            if matched_student is not None
            else None
        ),
        predicted_student_number=paper.predicted_student_number,
        student_number_confidence=paper.student_number_confidence,
        predicted_student_name=paper.predicted_student_name,
        student_name_confidence=paper.student_name_confidence,
        predicted_course_text=paper.predicted_course_text,
        course_confidence=paper.course_confidence,
        review_reasons=paper.review_reasons,
        status=paper.status,
        predicted_total_score=predicted_total,
        maximum_total_score=exam.total_score,
        answers=[
            PaperAnswerPredictionResponse(
                question_id=question.id,
                question_number=question.question_number,
                maximum_score=question.max_score,
                predicted_score=answer.predicted_score,
                confidence=answer.prediction_confidence,
                requires_review=answer.requires_review,
            )
            for answer, question in answer_rows
        ],
    )
    return response.model_copy(update={"paper": paper_response})


@router.post(
    "/exams/{exam_id}/scans",
    response_model=ScanJobEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_scan(
    exam_id: UUID,
    response: Response,
    db: DBSession,
    current_user: CurrentUser,
    storage: Storage,
    client_request_id: UUID = Form(...),
    image: UploadFile = File(...),
) -> ScanJobEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    existing = db.scalar(
        select(ScanJob).where(
            ScanJob.requested_by == current_user.id,
            ScanJob.client_request_id == client_request_id,
        )
    )
    if existing is not None:
        if existing.exam_id != exam.id:
            raise APIError(
                409,
                "CLIENT_REQUEST_ID_REUSED",
                "Client request ID was already used for another exam.",
            )
        response.status_code = status.HTTP_200_OK
        return ScanJobEnvelope(data=_scan_response(db, existing))

    if exam.status != ExamStatus.active:
        raise APIError(409, "EXAM_NOT_ACTIVE", "Scans can only be added to an active exam.")

    active_scan_count = db.scalar(
        select(func.count(ScanJob.id)).where(
            ScanJob.requested_by == current_user.id,
            ScanJob.status.in_([ScanStatus.queued, ScanStatus.processing]),
        )
    )
    if (active_scan_count or 0) >= settings.max_active_scans_per_user:
        raise APIError(
            429,
            "SCAN_QUEUE_LIMIT_REACHED",
            "Too many scans are already queued or processing.",
        )

    content_type = (image.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise APIError(400, "INVALID_MEDIA_TYPE", "Upload must be a PNG, JPEG, HEIC or HEIF image.")
    content = await image.read(settings.max_upload_bytes + 1)
    if not content:
        raise APIError(400, "EMPTY_UPLOAD", "Uploaded image is empty.")
    if len(content) > settings.max_upload_bytes:
        raise APIError(413, "UPLOAD_TOO_LARGE", "Uploaded image exceeds the configured limit.")
    if not _has_valid_image_signature(content, content_type):
        raise APIError(
            400,
            "INVALID_IMAGE_SIGNATURE",
            "Upload content does not match its media type.",
        )

    job_id = uuid4()
    object_key = f"{current_user.institution_id}/{exam.id}/{job_id}.{extension}"
    try:
        storage.put(object_key, content, content_type)
    except Exception as exc:
        raise APIError(
            503, "OBJECT_STORAGE_UNAVAILABLE", "Image storage is temporarily unavailable."
        ) from exc

    scan = ScanJob(
        id=job_id,
        exam_id=exam.id,
        requested_by=current_user.id,
        client_request_id=client_request_id,
        image_object_key=object_key,
        image_sha256=hashlib.sha256(content).hexdigest(),
    )
    db.add(scan)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        try:
            storage.delete(object_key)
        except Exception:
            pass
        duplicate = db.scalar(
            select(ScanJob).where(
                ScanJob.requested_by == current_user.id,
                ScanJob.client_request_id == client_request_id,
            )
        )
        if duplicate is not None and duplicate.exam_id == exam.id:
            response.status_code = status.HTTP_200_OK
            return ScanJobEnvelope(data=_scan_response(db, duplicate))
        raise APIError(
            409, "CLIENT_REQUEST_ID_REUSED", "Client request ID has already been used."
        ) from exc
    except Exception:
        db.rollback()
        try:
            storage.delete(object_key)
        except Exception:
            pass
        raise
    db.refresh(scan)
    return ScanJobEnvelope(data=_scan_response(db, scan))


@router.get("/exams/{exam_id}/scans", response_model=ScanJobListEnvelope)
def list_scans(
    exam_id: UUID, db: DBSession, current_user: CurrentUser
) -> ScanJobListEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    scans = db.scalars(
        select(ScanJob).where(ScanJob.exam_id == exam.id).order_by(ScanJob.queued_at, ScanJob.id)
    ).all()
    return ScanJobListEnvelope(
        data=[_scan_response(db, scan) for scan in scans]
    )


@router.get("/scans/{scan_id}", response_model=ScanJobEnvelope)
def read_scan(scan_id: UUID, db: DBSession, current_user: CurrentUser) -> ScanJobEnvelope:
    scan = _get_scan(db, current_user, scan_id)
    return ScanJobEnvelope(data=_scan_response(db, scan))
