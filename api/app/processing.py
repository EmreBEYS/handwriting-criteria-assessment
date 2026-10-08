import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from uuid import UUID

from handwriting_ml.layout import ExamPaperLayout, LayoutError
from handwriting_ml.recognition import (
    HandwritingRecognizer,
    ModelNotConfiguredError,
    UnavailableRecognizer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Course,
    CourseOffering,
    Enrollment,
    Exam,
    ExamPaper,
    ExamQuestion,
    PaperAnswer,
    PaperStatus,
    ScanJob,
    ScanStatus,
    Student,
)
from app.storage import ObjectStorage


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("ı", "i"))
    return "".join(
        character.upper()
        for character in decomposed
        if character.isalnum() and not unicodedata.combining(character)
    )


def _confidence(value: float) -> Decimal:
    return Decimal(str(round(value, 4)))


def _score(value: str, maximum: Decimal) -> Decimal | None:
    cleaned = re.sub(r"[^0-9,.-]", "", value).replace(",", ".")
    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        return None
    if parsed < 0 or parsed > maximum:
        return None
    return parsed.quantize(Decimal("0.001"))


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _unique_number_match(students: list[Student], predicted_number: str) -> Student | None:
    normalized_number = _normalized(predicted_number)
    if not normalized_number or not normalized_number.isdigit():
        return None
    exact = [
        student for student in students if _normalized(student.student_number) == normalized_number
    ]
    if len(exact) == 1:
        return exact[0]

    ranked = sorted(
        [
            (_edit_distance(normalized_number, _normalized(student.student_number)), student)
            for student in students
        ],
        key=lambda candidate: candidate[0],
    )
    if not ranked or ranked[0][0] > 1:
        return None
    if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
        return None
    return ranked[0][1]


def _match_student(db: Session, offering_id: UUID, predicted_number: str) -> Student | None:
    students = db.scalars(
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(
            Enrollment.course_offering_id == offering_id,
            Enrollment.is_active.is_(True),
            Student.is_active.is_(True),
        )
    ).all()
    return _unique_number_match(students, predicted_number)


def process_scan(
    db: Session,
    scan_id: UUID,
    storage: ObjectStorage,
    recognizer: HandwritingRecognizer,
    layout: ExamPaperLayout,
) -> ScanJob:
    scan = db.get(ScanJob, scan_id)
    if scan is None:
        raise LookupError("Scan job was not found")
    if scan.status != ScanStatus.queued:
        raise ValueError("Only queued scan jobs can be processed")
    scan.status = ScanStatus.processing
    scan.attempt_count += 1
    scan.started_at = datetime.now(UTC)
    scan.model_version = recognizer.model_version
    db.commit()

    try:
        exam = db.get(Exam, scan.exam_id)
        questions = db.scalars(
            select(ExamQuestion)
            .where(ExamQuestion.exam_id == scan.exam_id)
            .order_by(ExamQuestion.display_order)
        ).all()
        if exam is None or not questions:
            raise ValueError("Exam configuration is incomplete")
        offering = db.get(CourseOffering, exam.course_offering_id)
        course = db.get(Course, offering.course_id) if offering else None
        if offering is None or course is None:
            raise ValueError("Course configuration is incomplete")

        source = storage.get(scan.image_object_key)
        extraction = layout.extract(source, len(questions))
        number_prediction = recognizer.predict(
            extraction.regions["student_number"], "student_number"
        )
        matched_student = _match_student(db, offering.id, number_prediction.text)
        course_prediction = recognizer.predict(extraction.regions["course"], "course")

        threshold = settings.review_confidence_threshold
        expected_course = _normalized(f"{course.code} {course.name}")
        course_match = SequenceMatcher(
            None, expected_course, _normalized(course_prediction.text)
        ).ratio()
        review_reasons = list(extraction.warnings)
        if course_prediction.confidence < threshold or course_match < 0.75:
            review_reasons.append("COURSE_MISMATCH")
        if number_prediction.confidence < threshold:
            review_reasons.append("LOW_STUDENT_NUMBER_CONFIDENCE")
        if matched_student is None:
            review_reasons.append("STUDENT_NOT_MATCHED")
        elif _normalized(matched_student.student_number) != _normalized(number_prediction.text):
            review_reasons.append("STUDENT_NUMBER_MISMATCH")
        if matched_student is not None:
            existing_paper = db.scalar(
                select(ExamPaper.id).where(
                    ExamPaper.exam_id == exam.id,
                    ExamPaper.student_id == matched_student.id,
                    ExamPaper.status.in_(
                        [
                            PaperStatus.processing,
                            PaperStatus.needs_review,
                            PaperStatus.confirmed,
                        ]
                    ),
                )
            )
            if existing_paper is not None:
                review_reasons.append("DUPLICATE_STUDENT_PAPER")
                matched_student = None

        paper = ExamPaper(
            scan_job_id=scan.id,
            exam_id=exam.id,
            student_id=matched_student.id if matched_student else None,
            predicted_student_number=number_prediction.text.strip() or None,
            student_number_confidence=_confidence(number_prediction.confidence),
            predicted_student_name=None,
            student_name_confidence=None,
            predicted_course_text=course_prediction.text.strip() or None,
            course_confidence=_confidence(course_prediction.confidence),
            review_reasons=review_reasons,
            status=PaperStatus.needs_review,
        )
        db.add(paper)
        db.flush()
        for index, question in enumerate(questions, start=1):
            prediction = recognizer.predict(extraction.regions[f"score_{index}"], "score")
            predicted_score = _score(prediction.text, question.max_score)
            requires_review = prediction.confidence < threshold or predicted_score is None
            if predicted_score is None:
                review_reasons.append(f"INVALID_SCORE_{question.question_number}")
            elif prediction.confidence < threshold:
                review_reasons.append(f"LOW_SCORE_CONFIDENCE_{question.question_number}")
            db.add(
                PaperAnswer(
                    exam_paper_id=paper.id,
                    exam_question_id=question.id,
                    predicted_score=predicted_score,
                    prediction_confidence=_confidence(prediction.confidence),
                    requires_review=requires_review,
                )
            )
        paper.review_reasons = list(dict.fromkeys(review_reasons))
        scan.status = ScanStatus.needs_review
        scan.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(scan)
        return scan
    except ModelNotConfiguredError as exc:
        _fail_scan(db, scan, "MODEL_NOT_CONFIGURED", str(exc))
        return scan
    except LayoutError as exc:
        _fail_scan(db, scan, "LAYOUT_EXTRACTION_FAILED", str(exc))
        return scan
    except Exception:
        _fail_scan(db, scan, "PROCESSING_FAILED", "Scan processing failed.")
        return scan


def _fail_scan(db: Session, scan: ScanJob, code: str, message: str) -> None:
    db.rollback()
    scan = db.get(ScanJob, scan.id)
    scan.status = ScanStatus.failed
    scan.error_code = code
    scan.error_message = message
    scan.completed_at = datetime.now(UTC)
    db.commit()


def process_next_scan(
    db: Session,
    storage: ObjectStorage,
    recognizer: HandwritingRecognizer | None = None,
    layout_path: str | Path | None = None,
) -> ScanJob | None:
    scan_id = db.scalar(
        select(ScanJob.id)
        .where(ScanJob.status == ScanStatus.queued)
        .order_by(ScanJob.queued_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if scan_id is None:
        return None
    selected_recognizer = recognizer or UnavailableRecognizer(settings.model_version)
    selected_layout_path = Path(layout_path or settings.exam_layout_path)
    if not selected_layout_path.is_absolute():
        selected_layout_path = Path(__file__).resolve().parents[2] / selected_layout_path
    selected_layout = ExamPaperLayout.from_json(selected_layout_path)
    return process_scan(db, scan_id, storage, selected_recognizer, selected_layout)
