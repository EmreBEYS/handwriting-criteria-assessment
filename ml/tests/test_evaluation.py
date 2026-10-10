from handwriting_ml.evaluation import (
    EvaluationPrediction,
    review_outcomes,
    select_review_policy,
    summarize,
)


def prediction(expected: str, predicted: str, confidence: float) -> EvaluationPrediction:
    return EvaluationPrediction("student_number", expected, predicted, confidence)


def test_summary_reports_exact_match_cer_and_calibration_without_sample_data() -> None:
    report = summarize(
        [
            prediction("123", "123", 0.9),
            prediction("456", "457", 0.8),
            EvaluationPrediction("student_number", "999", None, None, "ValueError"),
        ]
    )

    assert report["sample_count"] == 3
    assert report["inference_failure_count"] == 1
    assert report["exact_match_rate"] == 0.333333
    assert report["character_error_rate"] == 0.444444
    assert report["error_categories"] == {
        "exact": 1,
        "substitution": 1,
        "inference_error": 1,
    }
    assert "123" not in str(report)


def test_score_summary_treats_decimal_formats_as_equivalent_and_computes_mae() -> None:
    report = summarize(
        [
            EvaluationPrediction("score", "10,0", "10", 0.9),
            EvaluationPrediction("score", "7.5", "6.5", 0.8),
        ]
    )

    assert report["exact_match_rate"] == 0.5
    assert report["numeric_mean_absolute_error"] == 0.5


def test_threshold_is_selected_on_validation_and_applied_to_test() -> None:
    validation = [
        prediction("1", "1", 0.95),
        prediction("2", "2", 0.90),
        prediction("3", "8", 0.70),
    ]
    policy = select_review_policy(
        validation, target_accuracy=1.0, minimum_unflagged_samples=1
    )

    assert policy["threshold"] == 0.9
    outcomes = review_outcomes(
        [prediction("4", "4", 0.92), prediction("5", "6", 0.85)], policy
    )
    assert outcomes == {
        "unflagged_count": 1,
        "review_flag_count": 1,
        "review_flag_rate": 0.5,
        "unflagged_accuracy": 1.0,
        "unflagged_error_count": 0,
    }


def test_field_pass_is_disabled_when_validation_cannot_meet_target() -> None:
    policy = select_review_policy(
        [prediction("1", "7", 0.9)],
        target_accuracy=0.98,
        minimum_unflagged_samples=1,
    )

    assert policy["field_pass_enabled"] is False
    outcomes = review_outcomes([prediction("2", "2", 0.99)], policy)
    assert outcomes["review_flag_rate"] == 1.0
