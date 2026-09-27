from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "handwriting-criteria-assessment-api"
    api_version: str = "v1"
    model_ready: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ProbabilityValue(BaseModel):
    label: str
    probability: float = Field(ge=0.0, le=1.0)


class AssessmentResult(BaseModel):
    criterion_id: str
    values: list[ProbabilityValue]


class AnalysisResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    analysis_id: str
    status: Literal["accepted", "processing", "completed", "failed"]
    model_version: str | None = None
    results: list[AssessmentResult] = []
    warnings: list[str] = []
