import hashlib
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_exam
from app.models import ExamStatus, ScanJob
from app.schemas import ScanJobEnvelope, ScanJobListEnvelope, ScanJobResponse
from app.storage import ObjectStorage, get_object_storage

router = APIRouter(prefix=settings.api_v1_prefix, tags=["scans"])
Storage = Annotated[ObjectStorage, Depends(get_object_storage)]

ALLOWED_IMAGE_TYPES = {
    "image/heic": "heic",
    "image/heif": "heif",
    "image/jpeg": "jpg",
    "image/png": "png",
}


def _get_scan(db: DBSession, current_user: CurrentUser, scan_id: UUID) -> ScanJob:
    scan = db.scalar(select(ScanJob).where(ScanJob.id == scan_id))
    if scan is None:
        raise APIError(404, "SCAN_NOT_FOUND", "Scan job was not found.")
    _get_exam(db, current_user, scan.exam_id)
    return scan


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
        return ScanJobEnvelope(data=ScanJobResponse.model_validate(existing))

    if exam.status != ExamStatus.active:
        raise APIError(409, "EXAM_NOT_ACTIVE", "Scans can only be added to an active exam.")

    content_type = (image.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise APIError(400, "INVALID_MEDIA_TYPE", "Upload must be a PNG, JPEG, HEIC or HEIF image.")
    content = await image.read(settings.max_upload_bytes + 1)
    if not content:
        raise APIError(400, "EMPTY_UPLOAD", "Uploaded image is empty.")
    if len(content) > settings.max_upload_bytes:
        raise APIError(413, "UPLOAD_TOO_LARGE", "Uploaded image exceeds the configured limit.")

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
            return ScanJobEnvelope(data=ScanJobResponse.model_validate(duplicate))
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
    return ScanJobEnvelope(data=ScanJobResponse.model_validate(scan))


@router.get("/exams/{exam_id}/scans", response_model=ScanJobListEnvelope)
def list_scans(
    exam_id: UUID, db: DBSession, current_user: CurrentUser
) -> ScanJobListEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    scans = db.scalars(
        select(ScanJob).where(ScanJob.exam_id == exam.id).order_by(ScanJob.queued_at, ScanJob.id)
    ).all()
    return ScanJobListEnvelope(
        data=[ScanJobResponse.model_validate(scan) for scan in scans]
    )


@router.get("/scans/{scan_id}", response_model=ScanJobEnvelope)
def read_scan(scan_id: UUID, db: DBSession, current_user: CurrentUser) -> ScanJobEnvelope:
    scan = _get_scan(db, current_user, scan_id)
    return ScanJobEnvelope(data=ScanJobResponse.model_validate(scan))
