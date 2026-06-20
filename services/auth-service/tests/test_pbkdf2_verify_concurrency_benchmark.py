from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import platform
import statistics
import time

import pytest

from app.security import hash_password_legacy_pbkdf2, verify_password


def test_pbkdf2_verify_concurrency_benchmark() -> None:
    if os.getenv("AUTH_PBKDF2_CONCURRENCY_BENCHMARK") != "1":
        pytest.skip("set AUTH_PBKDF2_CONCURRENCY_BENCHMARK=1 to run the PBKDF2 concurrency benchmark")

    concurrencies = _parse_concurrency_values(os.getenv("AUTH_PBKDF2_BENCHMARK_CONCURRENCY", "1,2,4,8,16"))
    requests_per_level = int(os.getenv("AUTH_PBKDF2_BENCHMARK_REQUESTS", "120"))
    if requests_per_level < 100:
        raise ValueError("AUTH_PBKDF2_BENCHMARK_REQUESTS must be at least 100 for p99")

    password = "benchmark-password-1234"
    password_hash = hash_password_legacy_pbkdf2(password)
    rows = [_measure_concurrency(password, password_hash, concurrency, requests_per_level) for concurrency in concurrencies]

    print(
        json.dumps(
            {
                "environment": {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "requests_per_concurrency": requests_per_level,
                },
                "scheme": "pbkdf2_sha256",
                "results": rows,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_concurrency_values(raw_value: str) -> list[int]:
    values = [int(item.strip()) for item in raw_value.split(",") if item.strip()]
    if not values or any(value < 1 for value in values):
        raise ValueError("AUTH_PBKDF2_BENCHMARK_CONCURRENCY must contain positive integers")
    return values


def _measure_concurrency(password: str, password_hash: str, concurrency: int, requests: int) -> dict[str, float | int]:
    durations_ms: list[float] = []
    started_at = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_verify_once, password, password_hash) for _ in range(requests)]
        for future in as_completed(futures):
            durations_ms.append(future.result())
    elapsed_seconds = time.perf_counter() - started_at
    sorted_durations = sorted(durations_ms)

    return {
        "concurrency": concurrency,
        "requests": requests,
        "throughput_rps": round(requests / elapsed_seconds, 2),
        "mean_ms": round(statistics.fmean(sorted_durations), 2),
        "p50_ms": round(_percentile(sorted_durations, 0.50), 2),
        "p95_ms": round(_percentile(sorted_durations, 0.95), 2),
        "p99_ms": round(_percentile(sorted_durations, 0.99), 2),
        "max_ms": round(sorted_durations[-1], 2),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }


def _verify_once(password: str, password_hash: str) -> float:
    started_at = time.perf_counter_ns()
    verified = verify_password(password, password_hash)
    elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
    if not verified:
        raise AssertionError("PBKDF2 benchmark password verification failed")
    return elapsed_ms


def _percentile(sorted_values: list[float], percentile: float) -> float:
    index = max(0, min(len(sorted_values) - 1, int(len(sorted_values) * percentile + 0.999999) - 1))
    return sorted_values[index]
