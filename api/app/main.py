from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import ErrorDetail, ErrorResponse, HealthResponse

app = FastAPI(
    title="Handwriting Criteria Assessment API",
    version="0.1.0",
    description="Criterion-independent API scaffold. No inference model is configured yet.",
)


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = ErrorResponse(
        error=ErrorDetail(code=exc.code, message=exc.message, request_id=request_id)
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse()


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
