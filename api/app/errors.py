import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request.state.request_id,
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return error_response(request, exc.status_code, exc.code, exc.message)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.")


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    message = "Resource not found." if exc.status_code == 404 else str(exc.detail)
    return error_response(request, exc.status_code, code, message)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled API exception",
        exc_info=exc,
        extra={"request_id": request.state.request_id},
    )
    return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")


exception_handlers: dict[Any, Any] = {
    APIError: api_error_handler,
    RequestValidationError: validation_error_handler,
    StarletteHTTPException: http_error_handler,
    Exception: unexpected_error_handler,
}
