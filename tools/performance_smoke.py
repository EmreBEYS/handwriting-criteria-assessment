from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Measurement:
    latency_ms: float
    status_code: int


def percentile(values: list[float], percentage: float) -> float:
    if not values:
        raise ValueError("At least one value is required")
    ordered = sorted(values)
    index = max(0, math.ceil(percentage * len(ordered)) - 1)
    return ordered[index]


def summarize(measurements: list[Measurement]) -> dict[str, object]:
    successful = [item.latency_ms for item in measurements if 200 <= item.status_code < 300]
    errors = len(measurements) - len(successful)
    return {
        "request_count": len(measurements),
        "success_count": len(successful),
        "error_count": errors,
        "p50_ms": round(percentile(successful, 0.50), 2) if successful else None,
        "p95_ms": round(percentile(successful, 0.95), 2) if successful else None,
        "max_ms": round(max(successful), 2) if successful else None,
    }


def _request(url: str, token: str | None, timeout_seconds: float) -> Measurement:
    headers = {"Accept": "application/json", "X-Request-ID": os.urandom(16).hex()}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read()
            status_code = response.status
    except urllib.error.HTTPError as exc:
        exc.read()
        status_code = exc.code
    except (OSError, TimeoutError):
        status_code = 0
    return Measurement((time.perf_counter() - started) * 1000, status_code)


def run(args: argparse.Namespace) -> tuple[dict[str, object], bool]:
    base_url = args.base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Performance checks require HTTPS except on localhost")
    token = os.environ.get(args.access_token_env) if args.access_token_env else None
    url = f"{base_url}/{args.path.lstrip('/')}"
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        measurements = list(
            executor.map(
                lambda _: _request(url, token, args.timeout_seconds),
                range(args.requests),
            )
        )
    report = summarize(measurements) | {
        "path": args.path,
        "concurrency": args.concurrency,
        "p95_target_ms": args.p95_target_ms,
    }
    passed = report["error_count"] == 0 and (
        report["p95_ms"] is not None and report["p95_ms"] <= args.p95_target_ms
    )
    report["passed"] = passed
    return report, passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a bounded HTTP latency smoke check")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", default="/health/live")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--p95-target-ms", type=float, default=500)
    parser.add_argument("--access-token-env", default=None)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.concurrency > args.requests:
        raise SystemExit(
            "requests and concurrency must be positive; concurrency cannot exceed requests"
        )
    report, passed = run(args)
    content = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content, end="")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
