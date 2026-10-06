from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(StrEnum):
    admin = "admin"
    instructor = "instructor"


class TermSeason(StrEnum):
    fall = "fall"
    spring = "spring"


class InstructorRole(StrEnum):
    owner = "owner"
    grader = "grader"
    viewer = "viewer"


class ExamType(StrEnum):
    midterm = "midterm"
    final = "final"
    makeup = "makeup"


class ExamStatus(StrEnum):
    draft = "draft"
    active = "active"
    closed = "closed"
    archived = "archived"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="institution")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("institution_id", "email"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.instructor, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    institution: Mapped[Institution] = relationship(back_populates="users")


class AcademicYear(Base):
    __tablename__ = "academic_years"
    __table_args__ = (UniqueConstraint("institution_id", "start_year"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("institution_id", "start_year", "season"),
        UniqueConstraint("academic_year_id", "season"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    academic_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[TermSeason] = mapped_column(Enum(TermSeason, name="term_season"), nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("institution_id", "code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProgramOutcome(Base):
    __tablename__ = "program_outcomes"
    __table_args__ = (UniqueConstraint("program_id", "code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("institution_id", "code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("academic_term_id", "program_id", "course_id", "section_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    academic_term_id: Mapped[UUID] = mapped_column(ForeignKey("academic_terms.id"), nullable=False)
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    section_code: Mapped[str] = mapped_column(String, default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CourseInstructor(Base):
    __tablename__ = "course_instructors"

    course_offering_id: Mapped[UUID] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[InstructorRole] = mapped_column(
        Enum(InstructorRole, name="instructor_role"),
        default=InstructorRole.grader,
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (UniqueConstraint("course_offering_id", "type", "title"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    course_offering_id: Mapped[UUID] = mapped_column(
        ForeignKey("course_offerings.id"), nullable=False
    )
    type: Mapped[ExamType] = mapped_column(Enum(ExamType, name="exam_type"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=100, nullable=False)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_status"), default=ExamStatus.draft, nullable=False
    )
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaces_exam_id: Mapped[UUID | None] = mapped_column(ForeignKey("exams.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_number"),
        UniqueConstraint("exam_id", "display_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exam_id: Mapped[UUID] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String)
    max_score: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class QuestionProgramOutcome(Base):
    __tablename__ = "question_program_outcomes"

    exam_question_id: Mapped[UUID] = mapped_column(
        ForeignKey("exam_questions.id", ondelete="CASCADE"), primary_key=True
    )
    program_outcome_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_outcomes.id"), primary_key=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
