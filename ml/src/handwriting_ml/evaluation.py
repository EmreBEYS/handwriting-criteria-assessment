from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class EvaluationPrediction:
    field_type: str
    expected: str
    predicted: str | None
    confidence: float | None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


def _normalize(value: str, field_type: str) -> str:
    normalized = "".join(value.split())
    if field_type != "score":
        return normalized
    try:
        number = Decimal(normalized.replace(",", "."))
    except InvalidOperation:
        return normalized.replace(",", ".")
    return format(number.normalize(), "f")


def _edit_distance(expected: str, predicted: str) -> int:
    previous = list(range(len(predicted) + 1))
    for expected_index, expected_character in enumerate(expected, start=1):
        current = [expected_index]
        for predicted_index, predicted_character in enumerate(predicted, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[predicted_index] + 1,
                    previous[predicted_index - 1]
                    + (expected_character != predicted_character),
                )
            )
        previous = current
    return previous[-1]


def _correct(item: EvaluationPrediction) -> bool:
    return item.predicted is not None and _normalize(
        item.expected, item.field_type
    ) == _normalize(item.predicted, item.field_type)


def _calibration(items: list[EvaluationPrediction], bin_count: int = 10) -> dict[str, object]:
    predicted = [
        item for item in items if item.predicted is not None and item.confidence is not None
    ]
    if not predicted:
        return {"sample_count": 0, "expected_calibration_error": None, "bins": []}
    bins = []
    weighted_error = 0.0
    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        members = [
            item
            for item in predicted
            if lower <= item.confidence < upper
            or (index == bin_count - 1 and item.confidence == 1)
        ]
        if not members:
            continue
        mean_confidence = sum(item.confidence or 0 for item in members) / len(members)
        accuracy = sum(_correct(item) for item in members) / len(members)
        weighted_error += len(members) * abs(accuracy - mean_confidence)
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "sample_count": len(members),
                "mean_confidence": round(mean_confidence, 6),
                "exact_match_rate": round(accuracy, 6),
            }
        )
    return {
        "sample_count": len(predicted),
        "expected_calibration_error": round(weighted_error / len(predicted), 6),
        "bins": bins,
    }


def summarize(items: list[EvaluationPrediction]) -> dict[str, object]:
    if not items:
        return {
            "sample_count": 0,
            "inference_failure_count": 0,
            "exact_match_rate": None,
            "character_error_rate": None,
            "numeric_mean_absolute_error": None,
            "calibration": _calibration([]),
            "error_categories": {},
        }
    exact = sum(_correct(item) for item in items)
    edits = 0
    expected_characters = 0
    absolute_errors: list[Decimal] = []
    categories: dict[str, int] = {}
    for item in items:
        expected = _normalize(item.expected, item.field_type)
        predicted = _normalize(item.predicted or "", item.field_type)
        edits += _edit_distance(expected, predicted)
        expected_characters += len(expected)
        if item.error_code:
            category = "inference_error"
        elif expected == predicted:
            category = "exact"
        elif len(expected) == len(predicted):
            category = "substitution"
        elif len(expected) < len(predicted):
            category = "insertion"
        else:
            category = "deletion"
        categories[category] = categories.get(category, 0) + 1
        if item.field_type == "score" and item.predicted is not None:
            try:
                absolute_errors.append(abs(Decimal(expected) - Decimal(predicted)))
            except InvalidOperation:
                pass
    numeric_mae = None
    if absolute_errors:
        numeric_mae = float(sum(absolute_errors, Decimal("0")) / len(absolute_errors))
    return {
        "sample_count": len(items),
        "inference_failure_count": sum(item.error_code is not None for item in items),
        "exact_match_rate": round(exact / len(items), 6),
        "character_error_rate": round(edits / max(1, expected_characters), 6),
        "numeric_mean_absolute_error": numeric_mae,
        "calibration": _calibration(items),
        "error_categories": categories,
    }


def select_review_policy(
    validation_items: list[EvaluationPrediction],
    target_accuracy: float,
    minimum_unflagged_samples: int = 30,
) -> dict[str, object]:
    if not 0 < target_accuracy <= 1:
        raise ValueError("Target accuracy must be greater than 0 and at most 1")
    if minimum_unflagged_samples < 1:
        raise ValueError("Minimum unflagged samples must be at least 1")
    candidates = sorted(
        {
            item.confidence
            for item in validation_items
            if item.predicted is not None and item.confidence is not None
        }
    )
    choices = []
    for threshold in candidates:
        accepted = [
            item
            for item in validation_items
            if item.predicted is not None
            and item.confidence is not None
            and item.confidence >= threshold
        ]
        accuracy = sum(_correct(item) for item in accepted) / len(accepted)
        if len(accepted) >= minimum_unflagged_samples and accuracy >= target_accuracy:
            choices.append((len(accepted), -threshold, threshold, accuracy))
    if not choices:
        return {
            "field_pass_enabled": False,
            "threshold": None,
            "target_accuracy": target_accuracy,
            "minimum_unflagged_samples": minimum_unflagged_samples,
            "reason": "no_validation_threshold_met_target",
        }
    accepted_count, _, threshold, accuracy = max(choices)
    return {
        "field_pass_enabled": True,
        "threshold": threshold,
        "target_accuracy": target_accuracy,
        "minimum_unflagged_samples": minimum_unflagged_samples,
        "validation_unflagged_count": accepted_count,
        "validation_unflagged_rate": round(
            accepted_count / max(1, len(validation_items)),
            6,
        ),
        "validation_unflagged_accuracy": round(accuracy, 6),
    }


def review_outcomes(
    items: list[EvaluationPrediction], policy: dict[str, object]
) -> dict[str, object]:
    threshold = policy.get("threshold") if policy.get("field_pass_enabled") else None
    accepted = []
    if isinstance(threshold, (int, float)):
        accepted = [
            item
            for item in items
            if item.predicted is not None
            and item.confidence is not None
            and item.confidence >= threshold
        ]
    correct = sum(_correct(item) for item in accepted)
    return {
        "unflagged_count": len(accepted),
        "review_flag_count": len(items) - len(accepted),
        "review_flag_rate": round((len(items) - len(accepted)) / max(1, len(items)), 6),
        "unflagged_accuracy": round(correct / len(accepted), 6) if accepted else None,
        "unflagged_error_count": len(accepted) - correct,
    }
