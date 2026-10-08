import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


class LayoutError(ValueError):
    """Raised when an uploaded page cannot be normalized or segmented safely."""


@dataclass(frozen=True)
class NormalizedBox:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if any(value < 0 or value > 1 for value in values):
            raise LayoutError("Normalized box coordinates must be between 0 and 1")
        if self.left >= self.right or self.top >= self.bottom:
            raise LayoutError("Normalized box must have positive width and height")

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "NormalizedBox":
        return cls(
            left=float(value["left"]),
            top=float(value["top"]),
            right=float(value["right"]),
            bottom=float(value["bottom"]),
        )

    def pixels(self, size: tuple[int, int]) -> tuple[int, int, int, int]:
        width, height = size
        return (
            round(self.left * width),
            round(self.top * height),
            round(self.right * width),
            round(self.bottom * height),
        )

    def crop(self, image: Image.Image) -> Image.Image:
        return image.crop(self.pixels(image.size))


@dataclass(frozen=True)
class LayoutExtraction:
    normalized_page: Image.Image
    regions: dict[str, Image.Image]
    warnings: tuple[str, ...]
    brightness: float
    edge_variance: float


class ExamPaperLayout:
    def __init__(
        self,
        *,
        template_id: str,
        canonical_size: tuple[int, int],
        fields: dict[str, NormalizedBox],
        score_row: NormalizedBox,
        max_questions: int = 30,
    ) -> None:
        required = {"course", "student_name", "student_number", "outcome_header"}
        missing = required.difference(fields)
        if missing:
            raise LayoutError(f"Template is missing fields: {', '.join(sorted(missing))}")
        if canonical_size[0] <= 0 or canonical_size[1] <= 0:
            raise LayoutError("Canonical size must be positive")
        self.template_id = template_id
        self.canonical_size = canonical_size
        self.fields = fields
        self.score_row = score_row
        self.max_questions = max_questions

    @classmethod
    def from_json(cls, path: str | Path) -> "ExamPaperLayout":
        with Path(path).open(encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schema_version") != "1.0":
            raise LayoutError("Unsupported layout schema version")
        return cls(
            template_id=data["template_id"],
            canonical_size=(data["canonical_width"], data["canonical_height"]),
            fields={
                name: NormalizedBox.from_mapping(box) for name, box in data["fields"].items()
            },
            score_row=NormalizedBox.from_mapping(data["score_row"]),
            max_questions=int(data.get("max_questions", 30)),
        )

    def extract(self, image_bytes: bytes, question_count: int) -> LayoutExtraction:
        if not 1 <= question_count <= self.max_questions:
            raise LayoutError(f"Question count must be between 1 and {self.max_questions}")
        page = self._normalize(image_bytes)
        regions = {name: box.crop(page) for name, box in self.fields.items()}
        regions.update(self._score_cells(page, question_count))

        grayscale = ImageOps.grayscale(page)
        brightness = ImageStat.Stat(grayscale).mean[0]
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        edge_variance = ImageStat.Stat(edges).var[0]
        warnings: list[str] = []
        if brightness < 70:
            warnings.append("IMAGE_TOO_DARK")
        elif brightness > 250:
            warnings.append("IMAGE_OVEREXPOSED")
        if edge_variance < 100:
            warnings.append("IMAGE_LOW_DETAIL")
        return LayoutExtraction(
            normalized_page=page,
            regions=regions,
            warnings=tuple(warnings),
            brightness=brightness,
            edge_variance=edge_variance,
        )

    def _normalize(self, image_bytes: bytes) -> Image.Image:
        try:
            with Image.open(io.BytesIO(image_bytes)) as uploaded:
                uploaded.verify()
            with Image.open(io.BytesIO(image_bytes)) as uploaded:
                page = ImageOps.exif_transpose(uploaded).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise LayoutError("Uploaded content is not a decodable image") from exc
        if min(page.size) < 600:
            raise LayoutError("Image resolution is too small for field extraction")
        if page.width > page.height:
            page = page.rotate(90, expand=True)
        page = self._crop_light_page(page)
        return page.resize(self.canonical_size, Image.Resampling.LANCZOS)

    @staticmethod
    def _crop_light_page(image: Image.Image) -> Image.Image:
        grayscale = ImageOps.grayscale(image)
        light_mask = grayscale.point(lambda pixel: 255 if pixel >= 175 else 0)
        bounds = light_mask.getbbox()
        if bounds is None:
            return image
        left, top, right, bottom = bounds
        area_ratio = ((right - left) * (bottom - top)) / (image.width * image.height)
        if 0.45 <= area_ratio < 0.98:
            return image.crop(bounds)
        return image

    def _score_cells(self, page: Image.Image, question_count: int) -> dict[str, Image.Image]:
        row = self.score_row
        cell_width = (row.right - row.left) / question_count
        return {
            f"score_{index + 1}": NormalizedBox(
                left=row.left + index * cell_width,
                top=row.top,
                right=row.left + (index + 1) * cell_width,
                bottom=row.bottom,
            ).crop(page)
            for index in range(question_count)
        }
