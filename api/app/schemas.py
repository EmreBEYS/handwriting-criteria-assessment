from datetime import date, datetime
from decimal import Decimal
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


class CourseOfferingListEnvelope(BaseModel):
    data: list[CourseOfferingResponse]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    student_number: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("student_number")
    @classmethod
    def normalize_student_number(cls, value: str) -> str:
        return value.upper()


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    student_number: str | None = Field(default=None, min_length=1, max_length=64)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

    @field_validator("student_number")
    @classmethod
    def normalize_student_number(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def reject_empty_or_null_update(self) -> "StudentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    student_number: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentEnvelope(BaseModel):
    data: StudentResponse


class StudentListEnvelope(BaseModel):
    data: list[StudentResponse]


class EnrollmentCreate(BaseModel):
    student_id: UUID


class EnrollmentResponse(BaseModel):
    course_offering_id: UUID
    student: StudentResponse
    enrolled_at: datetime
    is_active: bool


class EnrollmentEnvelope(BaseModel):
    data: EnrollmentResponse


class EnrollmentListEnvelope(BaseModel):
    data: list[EnrollmentResponse]


class ExamCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: Literal["midterm", "final", "makeup"]
    title: str = Field(min_length=1, max_length=255)
    total_score: Decimal = Field(default=Decimal("100"), gt=0, max_digits=8, decimal_places=3)
    held_at: datetime | None = None
    replaces_exam_id: UUID | None = None

    @model_validator(mode="after")
    def validate_replacement(self) -> "ExamCreate":
        if self.replaces_exam_id is not None and self.type != "makeup":
            raise ValueError("Only a makeup exam can replace another exam")
        return self


class ExamUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    total_score: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
    held_at: datetime | None = None

    @model_validator(mode="after")
    def reject_empty_or_null_update(self) -> "ExamUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        for field in ("title", "total_score"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_offering_id: UUID
    type: Literal["midterm", "final", "makeup"]
    title: str
    total_score: Decimal
    status: Literal["draft", "active", "closed", "archived"]
    held_at: datetime | None
    replaces_exam_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ExamEnvelope(BaseModel):
    data: ExamResponse


class ExamListEnvelope(BaseModel):
    data: list[ExamResponse]


class ProgramOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    code: str
    description: str
    is_active: bool


class ProgramOutcomeListEnvelope(BaseModel):
    data: list[ProgramOutcomeResponse]


class QuestionOutcomeWeight(BaseModel):
    program_outcome_id: UUID
    weight: Decimal = Field(gt=0, le=1, max_digits=7, decimal_places=6)


class QuestionOutcomeSet(BaseModel):
    outcomes: list[QuestionOutcomeWeight] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_outcomes(self) -> "QuestionOutcomeSet":
        outcome_ids = [item.program_outcome_id for item in self.outcomes]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("Program outcomes must be unique")
        if sum((item.weight for item in self.outcomes), Decimal("0")) != Decimal("1"):
            raise ValueError("Program outcome weights must total 1")
        return self


class QuestionOutcomeResponse(BaseModel):
    program_outcome_id: UUID
    code: str
    description: str
    weight: Decimal


class ExamQuestionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question_number: int = Field(gt=0)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    max_score: Decimal = Field(gt=0, max_digits=8, decimal_places=3)
    display_order: int = Field(gt=0)


class ExamQuestionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question_number: int | None = Field(default=None, gt=0)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    max_score: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
    display_order: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def reject_empty_or_null_update(self) -> "ExamQuestionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        for field in ("question_number", "max_score", "display_order"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ExamQuestionResponse(BaseModel):
    id: UUID
    exam_id: UUID
    question_number: int
    label: str | None
    max_score: Decimal
    display_order: int
    program_outcomes: list[QuestionOutcomeResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ExamQuestionEnvelope(BaseModel):
    data: ExamQuestionResponse


class ExamQuestionListEnvelope(BaseModel):
    data: list[ExamQuestionResponse]


class ScanJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exam_id: UUID
    requested_by: UUID
    client_request_id: UUID
    status: Literal["queued", "processing", "needs_review", "saved", "failed", "cancelled"]
    image_sha256: str | None
    model_version: str | None
    attempt_count: int
    error_code: str | None
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    saved_at: datetime | None
    updated_at: datetime


class ScanJobEnvelope(BaseModel):
    data: ScanJobResponse


class ScanJobListEnvelope(BaseModel):
    data: list[ScanJobResponse]


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
