from tools.performance_smoke import Measurement, percentile, summarize


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([10, 20, 30, 40, 50], 0.50) == 30
    assert percentile([10, 20, 30, 40, 50], 0.95) == 50


def test_performance_summary_keeps_errors_out_of_latency_percentiles() -> None:
    report = summarize(
        [Measurement(10, 200), Measurement(20, 204), Measurement(1, 500)]
    )

    assert report == {
        "request_count": 3,
        "success_count": 2,
        "error_count": 1,
        "p50_ms": 10,
        "p95_ms": 20,
        "max_ms": 20,
    }
