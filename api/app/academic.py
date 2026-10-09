from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.models import (
    AcademicTerm,
    AcademicYear,
    Course,
    CourseInstructor,
    CourseOffering,
    InstructorRole,
    Program,
)
from app.schemas import (
    AcademicYearCreate,
    AcademicYearEnvelope,
    AcademicYearListEnvelope,
    AcademicYearResponse,
    AcademicYearUpdate,
    CourseCreate,
    CourseEnvelope,
    CourseListEnvelope,
    CourseOfferingCreate,
    CourseOfferingEnvelope,
    CourseOfferingResponse,
    CourseResponse,
    CourseUpdate,
    SemesterCreate,
    SemesterEnvelope,
    SemesterListEnvelope,
    SemesterResponse,
    SemesterUpdate,
)

router = APIRouter(prefix=settings.api_v1_prefix, tags=["academic structure"])


def _academic_year_response(academic_year: AcademicYear) -> AcademicYearResponse:
    return AcademicYearResponse(
        id=academic_year.id,
        institution_id=academic_year.institution_id,
        start_year=academic_year.start_year,
        end_year=academic_year.start_year + 1,
        label=f"{academic_year.start_year}\N{EN DASH}{academic_year.start_year + 1}",
        created_at=academic_year.created_at,
    )


def _get_academic_year(db: DBSession, current_user: CurrentUser, year_id: UUID) -> AcademicYear:
    academic_year = db.scalar(
        select(AcademicYear).where(
            AcademicYear.id == year_id,
            AcademicYear.institution_id == current_user.institution_id,
        )
    )
    if academic_year is None:
        raise APIError(404, "ACADEMIC_YEAR_NOT_FOUND", "Academic year was not found.")
    return academic_year


def _get_semester(db: DBSession, current_user: CurrentUser, semester_id: UUID) -> AcademicTerm:
    semester = db.scalar(
        select(AcademicTerm).where(
            AcademicTerm.id == semester_id,
            AcademicTerm.institution_id == current_user.institution_id,
        )
    )
    if semester is None:
        raise APIError(404, "SEMESTER_NOT_FOUND", "Semester was not found.")
    return semester


def _get_course(db: DBSession, current_user: CurrentUser, course_id: UUID) -> Course:
    course = db.scalar(
        select(Course).where(
            Course.id == course_id,
            Course.institution_id == current_user.institution_id,
        )
    )
    if course is None:
        raise APIError(404, "COURSE_NOT_FOUND", "Course was not found.")
    return course


@router.post(
    "/academic-years",
    response_model=AcademicYearEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_academic_year(
    payload: AcademicYearCreate, db: DBSession, current_user: CurrentUser
) -> AcademicYearEnvelope:
    academic_year = AcademicYear(
        institution_id=current_user.institution_id,
        start_year=payload.start_year,
    )
    db.add(academic_year)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "ACADEMIC_YEAR_ALREADY_EXISTS", "Academic year already exists."
        ) from exc
    db.refresh(academic_year)
    return AcademicYearEnvelope(data=_academic_year_response(academic_year))


@router.get("/academic-years", response_model=AcademicYearListEnvelope)
def list_academic_years(db: DBSession, current_user: CurrentUser) -> AcademicYearListEnvelope:
    years = db.scalars(
        select(AcademicYear)
        .where(AcademicYear.institution_id == current_user.institution_id)
        .order_by(AcademicYear.start_year.desc())
    ).all()
    return AcademicYearListEnvelope(data=[_academic_year_response(year) for year in years])


@router.get("/academic-years/{year_id}", response_model=AcademicYearEnvelope)
def read_academic_year(
    year_id: UUID, db: DBSession, current_user: CurrentUser
) -> AcademicYearEnvelope:
    return AcademicYearEnvelope(
        data=_academic_year_response(_get_academic_year(db, current_user, year_id))
    )


@router.patch("/academic-years/{year_id}", response_model=AcademicYearEnvelope)
def update_academic_year(
    year_id: UUID,
    payload: AcademicYearUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AcademicYearEnvelope:
    academic_year = _get_academic_year(db, current_user, year_id)
    semesters = db.scalars(
        select(AcademicTerm).where(AcademicTerm.academic_year_id == academic_year.id)
    ).all()
    academic_year.start_year = payload.start_year
    for semester in semesters:
        semester.start_year = payload.start_year
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "ACADEMIC_YEAR_ALREADY_EXISTS", "Academic year already exists."
        ) from exc
    db.refresh(academic_year)
    return AcademicYearEnvelope(data=_academic_year_response(academic_year))


@router.delete("/academic-years/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_academic_year(year_id: UUID, db: DBSession, current_user: CurrentUser) -> Response:
    academic_year = _get_academic_year(db, current_user, year_id)
    offering_exists = db.scalar(
        select(CourseOffering.id)
        .join(AcademicTerm, CourseOffering.academic_term_id == AcademicTerm.id)
        .where(AcademicTerm.academic_year_id == academic_year.id)
        .limit(1)
    )
    if offering_exists is not None:
        raise APIError(409, "ACADEMIC_YEAR_IN_USE", "Academic year has course offerings.")
    db.execute(delete(AcademicTerm).where(AcademicTerm.academic_year_id == academic_year.id))
    db.delete(academic_year)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/semesters", response_model=SemesterEnvelope, status_code=status.HTTP_201_CREATED)
def create_semester(
    payload: SemesterCreate, db: DBSession, current_user: CurrentUser
) -> SemesterEnvelope:
    academic_year = _get_academic_year(db, current_user, payload.academic_year_id)
    semester = AcademicTerm(
        institution_id=current_user.institution_id,
        academic_year_id=academic_year.id,
        start_year=academic_year.start_year,
        season=payload.season,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
    )
    db.add(semester)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "SEMESTER_ALREADY_EXISTS", "Semester already exists.") from exc
    db.refresh(semester)
    return SemesterEnvelope(data=SemesterResponse.model_validate(semester))


@router.get("/semesters", response_model=SemesterListEnvelope)
def list_semesters(
    db: DBSession,
    current_user: CurrentUser,
    academic_year_id: UUID | None = Query(default=None),
) -> SemesterListEnvelope:
    query = select(AcademicTerm).where(AcademicTerm.institution_id == current_user.institution_id)
    if academic_year_id is not None:
        _get_academic_year(db, current_user, academic_year_id)
        query = query.where(AcademicTerm.academic_year_id == academic_year_id)
    semesters = db.scalars(
        query.order_by(AcademicTerm.start_year.desc(), AcademicTerm.season)
    ).all()
    return SemesterListEnvelope(
        data=[SemesterResponse.model_validate(semester) for semester in semesters]
    )


@router.get("/semesters/{semester_id}", response_model=SemesterEnvelope)
def read_semester(semester_id: UUID, db: DBSession, current_user: CurrentUser) -> SemesterEnvelope:
    semester = _get_semester(db, current_user, semester_id)
    return SemesterEnvelope(data=SemesterResponse.model_validate(semester))


@router.patch("/semesters/{semester_id}", response_model=SemesterEnvelope)
def update_semester(
    semester_id: UUID,
    payload: SemesterUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> SemesterEnvelope:
    semester = _get_semester(db, current_user, semester_id)
    values = payload.model_dump(exclude_unset=True)
    starts_on = values.get("starts_on", semester.starts_on)
    ends_on = values.get("ends_on", semester.ends_on)
    if starts_on and ends_on and ends_on <= starts_on:
        raise APIError(422, "INVALID_DATE_RANGE", "ends_on must be later than starts_on.")
    for field, value in values.items():
        setattr(semester, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "SEMESTER_ALREADY_EXISTS", "Semester already exists.") from exc
    db.refresh(semester)
    return SemesterEnvelope(data=SemesterResponse.model_validate(semester))


@router.delete("/semesters/{semester_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_semester(semester_id: UUID, db: DBSession, current_user: CurrentUser) -> Response:
    semester = _get_semester(db, current_user, semester_id)
    offering_exists = db.scalar(
        select(CourseOffering.id).where(CourseOffering.academic_term_id == semester.id).limit(1)
    )
    if offering_exists is not None:
        raise APIError(409, "SEMESTER_IN_USE", "Semester has course offerings.")
    db.delete(semester)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/courses", response_model=CourseEnvelope, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate, db: DBSession, current_user: CurrentUser
) -> CourseEnvelope:
    course = Course(
        institution_id=current_user.institution_id,
        code=payload.code,
        name=payload.name,
    )
    db.add(course)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "COURSE_CODE_ALREADY_EXISTS", "Course code already exists.") from exc
    db.refresh(course)
    return CourseEnvelope(data=CourseResponse.model_validate(course))


@router.get("/courses", response_model=CourseListEnvelope)
def list_courses(
    db: DBSession,
    current_user: CurrentUser,
    academic_year_id: UUID | None = Query(default=None),
    semester_id: UUID | None = Query(default=None),
) -> CourseListEnvelope:
    query = select(Course).where(Course.institution_id == current_user.institution_id)
    if academic_year_id is not None or semester_id is not None:
        query = (
            query.join(CourseOffering, CourseOffering.course_id == Course.id)
            .join(
                CourseInstructor,
                CourseInstructor.course_offering_id == CourseOffering.id,
            )
            .join(AcademicTerm, CourseOffering.academic_term_id == AcademicTerm.id)
            .where(CourseInstructor.user_id == current_user.id)
        )
        if academic_year_id is not None:
            _get_academic_year(db, current_user, academic_year_id)
            query = query.where(AcademicTerm.academic_year_id == academic_year_id)
        if semester_id is not None:
            semester = _get_semester(db, current_user, semester_id)
            if academic_year_id is not None and semester.academic_year_id != academic_year_id:
                raise APIError(
                    422,
                    "SEMESTER_YEAR_MISMATCH",
                    "Semester does not belong to the selected academic year.",
                )
            query = query.where(AcademicTerm.id == semester_id)
    courses = db.scalars(query.distinct().order_by(Course.code)).all()
    return CourseListEnvelope(data=[CourseResponse.model_validate(course) for course in courses])


@router.get("/courses/{course_id}", response_model=CourseEnvelope)
def read_course(course_id: UUID, db: DBSession, current_user: CurrentUser) -> CourseEnvelope:
    return CourseEnvelope(
        data=CourseResponse.model_validate(_get_course(db, current_user, course_id))
    )


@router.patch("/courses/{course_id}", response_model=CourseEnvelope)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> CourseEnvelope:
    course = _get_course(db, current_user, course_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "COURSE_CODE_ALREADY_EXISTS", "Course code already exists.") from exc
    db.refresh(course)
    return CourseEnvelope(data=CourseResponse.model_validate(course))


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: DBSession, current_user: CurrentUser) -> Response:
    course = _get_course(db, current_user, course_id)
    offering_exists = db.scalar(
        select(CourseOffering.id).where(CourseOffering.course_id == course.id).limit(1)
    )
    if offering_exists is not None:
        raise APIError(409, "COURSE_IN_USE", "Course has course offerings.")
    db.delete(course)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/course-offerings",
    response_model=CourseOfferingEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_course_offering(
    payload: CourseOfferingCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CourseOfferingEnvelope:
    course = _get_course(db, current_user, payload.course_id)
    semester = _get_semester(db, current_user, payload.semester_id)
    program = db.scalar(
        select(Program).where(
            Program.id == payload.program_id,
            Program.institution_id == current_user.institution_id,
        )
    )
    if program is None:
        raise APIError(404, "PROGRAM_NOT_FOUND", "Program was not found.")

    offering = CourseOffering(
        institution_id=current_user.institution_id,
        academic_term_id=semester.id,
        program_id=program.id,
        course_id=course.id,
        section_code=payload.section_code,
    )
    db.add(offering)
    try:
        db.flush()
        db.add(
            CourseInstructor(
                course_offering_id=offering.id,
                user_id=current_user.id,
                role=InstructorRole.owner,
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409, "COURSE_OFFERING_ALREADY_EXISTS", "Course offering already exists."
        ) from exc
    db.refresh(offering)
    return CourseOfferingEnvelope(
        data=CourseOfferingResponse(
            id=offering.id,
            course_id=offering.course_id,
            semester_id=offering.academic_term_id,
            academic_year_id=semester.academic_year_id,
            program_id=offering.program_id,
            section_code=offering.section_code,
            course_code=course.code,
            course_name=course.name,
            academic_year_label=f"{semester.start_year}–{semester.start_year + 1}",
            season=semester.season,
            instructor_role=InstructorRole.owner,
            created_at=offering.created_at,
        )
    )
