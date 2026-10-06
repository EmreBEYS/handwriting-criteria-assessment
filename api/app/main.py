from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.academic import router as academic_router
from app.auth import router as auth_router
from app.config import settings
from app.database import database_is_ready
from app.errors import APIError, exception_handlers
from app.schemas import ErrorResponse, HealthResponse, ReadinessResponse

app = FastAPI(
    title="Handwriting Criteria Assessment API",
    version="0.2.0",
    description="Shared API for exam-paper assessment and program-outcome analysis.",
    exception_handlers=exception_handlers,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(auth_router)
app.include_router(academic_router)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID")
    try:
        request_id = str(UUID(supplied_id)) if supplied_id else str(uuid4())
    except ValueError:
        request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", response_model=HealthResponse, tags=["system"])
@app.get("/health/live", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/health/ready", response_model=ReadinessResponse, tags=["system"])
def readiness(ready: bool = Depends(database_is_ready)) -> ReadinessResponse:
    if not ready:
        raise APIError(503, "DATABASE_UNAVAILABLE", "Database connection is unavailable.")
    return ReadinessResponse()


@app.post(
    "/v1/analyses",
    status_code=503,
    response_model=ErrorResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    tags=["analysis"],
)
async def create_analysis(image: UploadFile = File(...)) -> ErrorResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise APIError(400, "INVALID_MEDIA_TYPE", "Upload must use an image media type.")

    content = await image.read(settings.max_upload_bytes + 1)
    if not content:
        raise APIError(400, "EMPTY_UPLOAD", "Uploaded image is empty.")
    if len(content) > settings.max_upload_bytes:
        raise APIError(413, "UPLOAD_TOO_LARGE", "Uploaded image exceeds the configured limit.")

    raise APIError(
        503,
        "MODEL_NOT_CONFIGURED",
        "Analysis is unavailable until the approved criteria and model are configured.",
    )
