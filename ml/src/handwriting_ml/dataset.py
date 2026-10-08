import json
from dataclasses import dataclass
from pathlib import Path


class DatasetManifestError(ValueError):
    """Raised when a handwriting dataset manifest can produce invalid evaluation."""


@dataclass(frozen=True)
class HandwritingSample:
    image_path: str
    label: str
    field_type: str
    writer_id: str
    split: str


ALLOWED_FIELD_TYPES = {"name", "student_number", "score"}
ALLOWED_SPLITS = {"train", "validation", "test"}


def load_manifest(path: str | Path) -> list[HandwritingSample]:
    samples: list[HandwritingSample] = []
    seen_paths: set[str] = set()
    writer_splits: dict[str, set[str]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                sample = HandwritingSample(
                    image_path=str(record["image_path"]).strip(),
                    label=str(record["label"]).strip(),
                    field_type=str(record["field_type"]).strip(),
                    writer_id=str(record["writer_id"]).strip(),
                    split=str(record["split"]).strip(),
                )
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise DatasetManifestError(
                    f"Invalid manifest record on line {line_number}"
                ) from exc
            if not all((sample.image_path, sample.label, sample.writer_id)):
                raise DatasetManifestError(f"Empty required value on line {line_number}")
            if sample.field_type not in ALLOWED_FIELD_TYPES:
                raise DatasetManifestError(f"Unsupported field type on line {line_number}")
            if sample.split not in ALLOWED_SPLITS:
                raise DatasetManifestError(f"Unsupported split on line {line_number}")
            if sample.image_path in seen_paths:
                raise DatasetManifestError(f"Duplicate image path on line {line_number}")
            seen_paths.add(sample.image_path)
            writer_splits.setdefault(sample.writer_id, set()).add(sample.split)
            samples.append(sample)
    if not samples:
        raise DatasetManifestError("Manifest contains no samples")
    leaked_writers = sorted(writer for writer, splits in writer_splits.items() if len(splits) > 1)
    if leaked_writers:
        raise DatasetManifestError(
            "Writer IDs cannot cross train, validation and test splits: "
            + ", ".join(leaked_writers)
        )
    return samples
