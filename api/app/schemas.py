from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class AcademicYearCreate(BaseModel):
    start_year: int = Field(ge=2000, le=2200)


class AcademicYearUpdate(BaseModel):
    start_year: int = Field(ge=2000, le=2200)


class AcademicYearResponse(BaseModel):
    id: UUID
    institution_id: UUID
    start_year: int
    end_year: int
    label: str
    created_at: datetime


class AcademicYearEnvelope(BaseModel):
    data: AcademicYearResponse


class AcademicYearListEnvelope(BaseModel):
    data: list[AcademicYearResponse]


class SemesterCreate(BaseModel):
    academic_year_id: UUID
    season: Literal["fall", "spring"]
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "SemesterCreate":
        if self.starts_on and self.ends_on and self.ends_on <= self.starts_on:
            raise ValueError("ends_on must be later than starts_on")
        return self


class SemesterUpdate(BaseModel):
    season: Literal["fall", "spring"] | None = None
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def reject_empty_update(self) -> "SemesterUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        if "season" in self.model_fields_set and self.season is None:
            raise ValueError("season cannot be null")
        return self


class SemesterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    academic_year_id: UUID
    start_year: int
    season: Literal["fall", "spring"]
    starts_on: date | None
    ends_on: date | None
    created_at: datetime


class SemesterEnvelope(BaseModel):
    data: SemesterResponse


class SemesterListEnvelope(BaseModel):
    data: list[SemesterResponse]


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class CourseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def reject_empty_update(self) -> "CourseUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        if "code" in self.model_fields_set and self.code is None:
            raise ValueError("code cannot be null")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    code: str
    name: str
    created_at: datetime
    updated_at: datetime


class CourseEnvelope(BaseModel):
    data: CourseResponse


class CourseListEnvelope(BaseModel):
    data: list[CourseResponse]


class CourseOfferingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    course_id: UUID
    semester_id: UUID
    program_id: UUID
    section_code: str = Field(default="1", min_length=1, max_length=64)


class CourseOfferingResponse(BaseModel):
    id: UUID
    course_id: UUID
    semester_id: UUID
    academic_year_id: UUID
    program_id: UUID
    section_code: str
    instructor_role: Literal["owner", "grader", "viewer"]
    created_at: datetime


class CourseOfferingEnvelope(BaseModel):
    data: CourseOfferingResponse


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
