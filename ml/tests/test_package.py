import io
import json

import handwriting_ml
import pytest
from handwriting_ml.layout import ExamPaperLayout, LayoutError
from PIL import Image, ImageDraw


def test_package_has_version() -> None:
    assert handwriting_ml.__version__ == "0.1.0"


def make_layout(tmp_path) -> ExamPaperLayout:
    config = {
        "schema_version": "1.0",
        "template_id": "test-template",
        "canonical_width": 1000,
        "canonical_height": 1400,
        "fields": {
            "course": {"left": 0.1, "top": 0.1, "right": 0.5, "bottom": 0.2},
            "student_name": {"left": 0.5, "top": 0.1, "right": 0.9, "bottom": 0.15},
            "student_number": {"left": 0.5, "top": 0.15, "right": 0.9, "bottom": 0.2},
            "outcome_header": {"left": 0.1, "top": 0.2, "right": 0.9, "bottom": 0.25},
        },
        "score_row": {"left": 0.1, "top": 0.25, "right": 0.9, "bottom": 0.35},
        "max_questions": 10,
    }
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return ExamPaperLayout.from_json(path)


def image_bytes(size: tuple[int, int] = (1000, 1400)) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 100, 900, 490), outline="black", width=5)
    draw.text((120, 120), "BILM374 YAPAY ZEKA", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_layout_extracts_identity_course_and_dynamic_score_cells(tmp_path) -> None:
    extraction = make_layout(tmp_path).extract(image_bytes(), question_count=4)

    assert extraction.normalized_page.size == (1000, 1400)
    assert set(extraction.regions) == {
        "course",
        "student_name",
        "student_number",
        "outcome_header",
        "score_1",
        "score_2",
        "score_3",
        "score_4",
    }
    assert extraction.regions["score_1"].size == (200, 140)
    assert extraction.regions["score_4"].size == (200, 140)


def test_layout_rotates_landscape_capture_and_rejects_invalid_input(tmp_path) -> None:
    layout = make_layout(tmp_path)
    extraction = layout.extract(image_bytes((1400, 1000)), question_count=2)
    assert extraction.normalized_page.size == (1000, 1400)

    with pytest.raises(LayoutError, match="decodable image"):
        layout.extract(b"not-an-image", question_count=2)
    with pytest.raises(LayoutError, match="Question count"):
        layout.extract(image_bytes(), question_count=0)
