import json
import os
import platform
import statistics
import time

from app.security import hash_password_argon2id, hash_password_legacy_pbkdf2, verify_password


def test_password_verify_benchmark_outputs_summary() -> None:
    samples = int(os.getenv("AUTH_PASSWORD_BENCHMARK_SAMPLES", "7"))
    if samples < 3:
        raise ValueError("AUTH_PASSWORD_BENCHMARK_SAMPLES must be at least 3")

    argon2id_hash = hash_password_argon2id("benchmark-password-1234")
    legacy_hash = hash_password_legacy_pbkdf2("benchmark-password-1234")

    results = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "samples": samples,
        },
        "schemes": {
            "pbkdf2_sha256": _measure_verify(legacy_hash, samples),
            "argon2id": _measure_verify(argon2id_hash, samples),
        },
    }

    print(json.dumps(results, indent=2, sort_keys=True))


def _measure_verify(password_hash: str, samples: int) -> dict[str, float]:
    durations_ms: list[float] = []
    for _ in range(samples):
        started_at = time.perf_counter_ns()
        verified = verify_password("benchmark-password-1234", password_hash)
        elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
        if not verified:
            raise AssertionError("benchmark password verification failed")
        durations_ms.append(elapsed_ms)

    return {
        "mean_ms": round(statistics.fmean(durations_ms), 3),
        "median_ms": round(statistics.median(durations_ms), 3),
        "min_ms": round(min(durations_ms), 3),
        "max_ms": round(max(durations_ms), 3),
    }
