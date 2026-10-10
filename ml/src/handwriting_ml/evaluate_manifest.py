from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from handwriting_ml.dataset import HandwritingSample, load_manifest
from handwriting_ml.evaluation import (
    EvaluationPrediction,
    review_outcomes,
    select_review_policy,
    summarize,
)
from handwriting_ml.recognition import HandwritingRecognizer

SUPPORTED_FIELDS = {"student_number", "score"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_path(sample: HandwritingSample, dataset_root: Path) -> Path:
    path = (dataset_root / sample.image_path).resolve()
    if not path.is_relative_to(dataset_root):
        raise ValueError("Manifest image path escapes the dataset root")
    if not path.is_file():
        raise FileNotFoundError("Manifest image is missing")
    return path


def _predict(
    samples: list[HandwritingSample], dataset_root: Path, recognizer: HandwritingRecognizer
) -> list[EvaluationPrediction]:
    results = []
    for sample in samples:
        try:
            with Image.open(_image_path(sample, dataset_root)) as source:
                prediction = recognizer.predict(source.copy(), sample.field_type)
            results.append(
                EvaluationPrediction(
                    field_type=sample.field_type,
                    expected=sample.label,
                    predicted=prediction.text,
                    confidence=prediction.confidence,
                )
            )
        except Exception as exc:  # A bad sample must be counted, not abort the benchmark.
            results.append(
                EvaluationPrediction(
                    field_type=sample.field_type,
                    expected=sample.label,
                    predicted=None,
                    confidence=None,
                    error_code=type(exc).__name__,
                )
            )
    return results


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    from handwriting_ml.digit_model import TorchDigitRecognizer

    if args.minimum_slice_size < 1:
        raise ValueError("Minimum slice size must be at least 1")
    if args.minimum_threshold_samples < 1:
        raise ValueError("Minimum threshold samples must be at least 1")
    manifest = args.manifest.resolve()
    model = args.model.resolve()
    dataset_root = (args.dataset_root or manifest.parent).resolve()
    samples = [
        sample
        for sample in load_manifest(manifest)
        if sample.field_type in args.field_types and sample.split in {"validation", "test"}
    ]
    if not samples:
        raise ValueError("Manifest has no selected validation or test samples")
    recognizer = TorchDigitRecognizer.load(model)
    predictions = _predict(samples, dataset_root, recognizer)
    fields = {}
    for field_type in sorted(args.field_types):
        validation = [
            item
            for item, sample in zip(predictions, samples, strict=True)
            if sample.field_type == field_type and sample.split == "validation"
        ]
        test = [
            item
            for item, sample in zip(predictions, samples, strict=True)
            if sample.field_type == field_type and sample.split == "test"
        ]
        if not validation and not test:
            continue
        policy = select_review_policy(
            validation,
            args.target_unflagged_accuracy,
            args.minimum_threshold_samples,
        )
        test_pairs = [
            (item, sample)
            for item, sample in zip(predictions, samples, strict=True)
            if sample.field_type == field_type and sample.split == "test"
        ]
        slices: dict[str, dict[str, object]] = {}
        for attribute in ("device_class", "capture_condition"):
            values = sorted(
                {
                    value
                    for _, sample in test_pairs
                    if (value := getattr(sample, attribute)) is not None
                }
            )
            groups = {
                value: summarize(
                    [item for item, sample in test_pairs if getattr(sample, attribute) == value]
                )
                for value in values
                if sum(getattr(sample, attribute) == value for _, sample in test_pairs)
                >= args.minimum_slice_size
            }
            if groups:
                slices[attribute] = groups
        fields[field_type] = {
            "validation": summarize(validation),
            "test": summarize(test),
            "review_policy_selected_on_validation": policy,
            "test_review_outcomes": review_outcomes(test, policy),
            "test_slices": slices,
        }
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": recognizer.model_version,
        "model_sha256": _sha256(model),
        "manifest_sha256": _sha256(manifest),
        "privacy": "aggregate_only_no_labels_paths_or_writer_ids",
        "fields": fields,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate an OCR checkpoint on writer-disjoint manifest splits"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--field-types",
        nargs="+",
        choices=sorted(SUPPORTED_FIELDS),
        default=sorted(SUPPORTED_FIELDS),
    )
    parser.add_argument("--target-unflagged-accuracy", type=float, default=0.98)
    parser.add_argument("--minimum-threshold-samples", type=int, default=30)
    parser.add_argument("--minimum-slice-size", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = evaluate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
