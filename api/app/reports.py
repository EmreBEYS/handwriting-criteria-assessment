from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import APIError
from app.exams import _get_exam
from app.models import (
    AcademicTerm,
    Course,
    CourseOffering,
    ExamPaper,
    ExamQuestion,
    ExportJob,
    ExportStatus,
    PaperAnswer,
    PaperStatus,
    ProgramOutcome,
    QuestionProgramOutcome,
    Student,
)
from app.schemas import (
    ExamAnalysisEnvelope,
    ExamAnalysisResponse,
    ExportJobEnvelope,
    ExportJobResponse,
    ProgramOutcomeAnalysisResponse,
    QuestionAnalysisResponse,
)
from app.storage import ObjectStorage, get_object_storage
from app.xlsx import build_workbook

router = APIRouter(prefix=settings.api_v1_prefix, tags=["reports"])
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
Storage = Annotated[ObjectStorage, Depends(get_object_storage)]


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0.00")
    return (numerator * Decimal("100") / denominator).quantize(Decimal("0.01"))


def _analysis(db: DBSession, exam_id: UUID) -> ExamAnalysisResponse:
    answer_rows = db.execute(
        select(PaperAnswer, ExamQuestion)
        .join(ExamPaper, PaperAnswer.exam_paper_id == ExamPaper.id)
        .join(ExamQuestion, PaperAnswer.exam_question_id == ExamQuestion.id)
        .where(
            ExamPaper.exam_id == exam_id,
            ExamPaper.status == PaperStatus.confirmed,
            PaperAnswer.final_score.is_not(None),
        )
        .order_by(ExamQuestion.display_order)
    ).all()
    confirmed_count = len(
        db.scalars(
            select(ExamPaper.id).where(
                ExamPaper.exam_id == exam_id, ExamPaper.status == PaperStatus.confirmed
            )
        ).all()
    )

    question_scores: dict[UUID, list[Decimal]] = defaultdict(list)
    questions: dict[UUID, ExamQuestion] = {}
    for answer, question in answer_rows:
        questions[question.id] = question
        question_scores[question.id].append(answer.final_score)
    question_analysis = []
    for question in sorted(questions.values(), key=lambda item: item.display_order):
        scores = question_scores[question.id]
        total = sum(scores, Decimal("0"))
        average = (total / len(scores)).quantize(Decimal("0.001"))
        question_analysis.append(
            QuestionAnalysisResponse(
                question_id=question.id,
                question_number=question.question_number,
                maximum_score=question.max_score,
                average_score=average,
                success_percentage=_percentage(total, question.max_score * len(scores)),
                response_count=len(scores),
            )
        )

    mappings = db.execute(
        select(QuestionProgramOutcome, ProgramOutcome)
        .join(ExamQuestion, QuestionProgramOutcome.exam_question_id == ExamQuestion.id)
        .join(ProgramOutcome, QuestionProgramOutcome.program_outcome_id == ProgramOutcome.id)
        .where(ExamQuestion.exam_id == exam_id)
    ).all()
    mapping_by_question = defaultdict(list)
    outcomes: dict[UUID, ProgramOutcome] = {}
    for mapping, outcome in mappings:
        mapping_by_question[mapping.exam_question_id].append(mapping)
        outcomes[outcome.id] = outcome
    achieved = defaultdict(lambda: Decimal("0"))
    maximum = defaultdict(lambda: Decimal("0"))
    for answer, question in answer_rows:
        for mapping in mapping_by_question[question.id]:
            achieved[mapping.program_outcome_id] += answer.final_score * mapping.weight
            maximum[mapping.program_outcome_id] += question.max_score * mapping.weight
    outcome_analysis = [
        ProgramOutcomeAnalysisResponse(
            program_outcome_id=outcome.id,
            code=outcome.code,
            description=outcome.description,
            achieved_score=achieved[outcome.id].quantize(Decimal("0.001")),
            maximum_score=maximum[outcome.id].quantize(Decimal("0.001")),
            success_percentage=_percentage(achieved[outcome.id], maximum[outcome.id]),
        )
        for outcome in sorted(outcomes.values(), key=lambda item: item.code)
    ]
    return ExamAnalysisResponse(
        exam_id=exam_id,
        confirmed_paper_count=confirmed_count,
        questions=question_analysis,
        program_outcomes=outcome_analysis,
    )


def _workbook(db: DBSession, exam, analysis: ExamAnalysisResponse, current_user) -> bytes:
    context = db.execute(
        select(CourseOffering, Course, AcademicTerm)
        .join(Course, CourseOffering.course_id == Course.id)
        .join(AcademicTerm, CourseOffering.academic_term_id == AcademicTerm.id)
        .where(CourseOffering.id == exam.course_offering_id)
    ).one()
    offering, course, term = context
    questions = db.scalars(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == exam.id)
        .order_by(ExamQuestion.display_order)
    ).all()
    papers = db.execute(
        select(ExamPaper, Student)
        .join(Student, ExamPaper.student_id == Student.id)
        .where(ExamPaper.exam_id == exam.id, ExamPaper.status == PaperStatus.confirmed)
        .order_by(Student.student_number)
    ).all()
    student_rows: list[list[object]] = [
        ["Öğrenci No", "Ad Soyad", *[f"S{q.question_number}" for q in questions], "Toplam", "Durum"]
    ]
    for paper, student in papers:
        scores = {
            answer.exam_question_id: answer.final_score
            for answer in db.scalars(
                select(PaperAnswer).where(PaperAnswer.exam_paper_id == paper.id)
            ).all()
        }
        ordered_scores = [scores.get(question.id, Decimal("0")) for question in questions]
        student_rows.append(
            [
                student.student_number,
                f"{student.first_name} {student.last_name}",
                *[float(score) for score in ordered_scores],
                float(sum(ordered_scores, Decimal("0"))),
                "Onaylandı",
            ]
        )
    question_rows: list[list[object]] = [
        ["Soru", "Azami Puan", "Ortalama Puan", "Başarı %", "Yanıt Sayısı"]
    ] + [
        [
            item.question_number,
            float(item.maximum_score),
            float(item.average_score),
            float(item.success_percentage),
            item.response_count,
        ]
        for item in analysis.questions
    ]
    outcome_rows: list[list[object]] = [
        ["PÇ Kodu", "Açıklama", "Elde Edilen", "Ağırlıklı Azami", "Başarı %"]
    ] + [
        [
            item.code,
            item.description,
            float(item.achieved_score),
            float(item.maximum_score),
            float(item.success_percentage),
        ]
        for item in analysis.program_outcomes
    ]
    metadata_rows = [
        ["Alan", "Değer"],
        ["Üretim Zamanı", datetime.now(UTC).isoformat()],
        ["Akademik Yıl", f"{term.start_year}–{term.start_year + 1}"],
        ["Dönem", term.season.value],
        ["Ders", f"{course.code} - {course.name}"],
        ["Şube", offering.section_code],
        ["Sınav", exam.title],
        ["Raporu Üreten", f"{current_user.first_name} {current_user.last_name}"],
    ]
    return build_workbook(
        [
            ("Öğrenci Puanları", student_rows),
            ("Soru Analizi", question_rows),
            ("PÇ Analizi", outcome_rows),
            ("Metadata", metadata_rows),
        ]
    )


@router.get("/exams/{exam_id}/po-analysis", response_model=ExamAnalysisEnvelope)
def read_po_analysis(
    exam_id: UUID, db: DBSession, current_user: CurrentUser
) -> ExamAnalysisEnvelope:
    _get_exam(db, current_user, exam_id)
    return ExamAnalysisEnvelope(data=_analysis(db, exam_id))


@router.post(
    "/exams/{exam_id}/exports",
    response_model=ExportJobEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    exam_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    storage: Storage,
) -> ExportJobEnvelope:
    exam = _get_exam(db, current_user, exam_id)
    analysis = _analysis(db, exam.id)
    now = datetime.now(UTC)
    export_id = uuid4()
    object_key = f"{current_user.institution_id}/{exam.id}/exports/{export_id}.xlsx"
    content = _workbook(db, exam, analysis, current_user)
    try:
        storage.put(object_key, content, XLSX_MEDIA_TYPE)
    except Exception as exc:
        raise APIError(503, "OBJECT_STORAGE_UNAVAILABLE", "Report storage is unavailable.") from exc
    export = ExportJob(
        id=export_id,
        exam_id=exam.id,
        requested_by=current_user.id,
        status=ExportStatus.ready,
        object_key=object_key,
        completed_at=now,
        expires_at=now + timedelta(days=7),
    )
    db.add(export)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.delete(object_key)
        except Exception:
            pass
        raise
    db.refresh(export)
    response = ExportJobResponse.model_validate(export).model_copy(
        update={"download_url": f"{settings.api_v1_prefix}/exports/{export.id}/download"}
    )
    return ExportJobEnvelope(data=response)


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    storage: Storage,
) -> Response:
    export = db.get(ExportJob, export_id)
    if export is None or export.requested_by != current_user.id:
        raise APIError(404, "EXPORT_NOT_FOUND", "Export was not found.")
    _get_exam(db, current_user, export.exam_id)
    if export.status != ExportStatus.ready or not export.object_key:
        raise APIError(409, "EXPORT_NOT_READY", "Export is not ready for download.")
    expires_at = export.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and expires_at < datetime.now(UTC):
        export.status = ExportStatus.expired
        db.commit()
        raise APIError(410, "EXPORT_EXPIRED", "Export has expired.")
    try:
        content = storage.get(export.object_key)
    except Exception as exc:
        raise APIError(503, "OBJECT_STORAGE_UNAVAILABLE", "Report storage is unavailable.") from exc
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="exam-{export.exam_id}.xlsx"'},
    )
