from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "handwriting-criteria-assessment-api"
    api_version: str = "v1"
    model_ready: bool = False


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    service: str = "handwriting-criteria-assessment-api"
    database: Literal["connected"] = "connected"


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution_code: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.casefold()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized

    @field_validator("institution_code")
    @classmethod
    def normalize_institution_code(cls, value: str) -> str:
        return value.upper()


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution_code: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.casefold()

    @field_validator("institution_code")
    @classmethod
    def normalize_institution_code(cls, value: str) -> str:
        return value.upper()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    email: str
    first_name: str
    last_name: str
    role: Literal["admin", "instructor"]
    is_active: bool
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AuthData(BaseModel):
    user: UserResponse
    tokens: TokenPair


class AuthResponse(BaseModel):
    data: AuthData


class UserEnvelope(BaseModel):
    data: UserResponse


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
