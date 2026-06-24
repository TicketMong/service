from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import Session, sessionmaker

SERVICE_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SERVICE_REPO_ROOT))

from tests.benchmarks.api_presets import ApiBenchmarkPreset, chunked, load_preset, user_id_for
from tests.benchmarks.query_analysis import explain_postgres_sql, percentile_interpretation

from app.database import Base, get_db
from app.main import create_app as create_auth_app
from app.models import AuditLog, RefreshToken, User
from app.security import create_access_token, hash_password, hash_refresh_token


auth_app = create_auth_app()

SERVICE_NAME = "auth-service"
BENCHMARK_PASSWORD = "benchmark-password-1234"


@dataclass(frozen=True)
class BenchmarkConfig:
    samples: int
    warmup: int
    artifact_dir: Path
    preset: ApiBenchmarkPreset


@dataclass(frozen=True)
class SeedTargets:
    customer_id: int
    customer_email: str
    admin_id: int
    admin_email: str
    access_token: str
    admin_access_token: str
    refresh_tokens: list[str]


@dataclass(frozen=True)
class EndpointCase:
    name: str
    method: str
    path: Callable[[int], str]
    status: int
    json_body: Callable[[int], dict[str, Any]] | None = None
    headers: Callable[[int], dict[str, str]] | None = None


def test_auth_api_benchmark_outputs_artifact(request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--run-auth-api-benchmark"):
        pytest.skip("use --run-auth-api-benchmark to run the isolated PostgreSQL benchmark")

    config = _benchmark_config(request)
    postgres = pytest.importorskip("testcontainers.postgres")
    docker = pytest.importorskip("docker")
    try:
        docker.from_env().ping()
    except Exception as exc:
        pytest.skip(f"Docker is not available for Testcontainers: {exc}")

    started_at = datetime.now(UTC)
    with postgres.PostgresContainer("postgres:16-alpine") as container:
        engine = create_engine(container.get_connection_url(driver="psycopg"))
        try:
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
            factory = sessionmaker(bind=engine)
            with factory() as session:
                targets = _seed_dataset(session, config)
                session.commit()
            with factory() as session:
                session.execute(text("ANALYZE"))
                session.commit()
            app = _benchmark_app(factory)
            with TestClient(app) as client:
                metrics = [
                    _measure_endpoint(client, endpoint, config)
                    for endpoint in _benchmark_endpoints(targets)
                ]
            with factory() as session:
                query_analysis = _query_analysis(session, targets, config)
            artifact = _artifact(started_at, config, metrics, query_analysis)
            _write_artifact(config.artifact_dir, artifact, started_at)
        finally:
            auth_app.dependency_overrides.clear()
            engine.dispose()


def _benchmark_config(request: pytest.FixtureRequest) -> BenchmarkConfig:
    try:
        preset = load_preset(request.config.getoption("--auth-benchmark-preset"))
    except ValueError as exc:
        pytest.fail(str(exc))
    config = BenchmarkConfig(
        samples=request.config.getoption("--auth-benchmark-samples"),
        warmup=request.config.getoption("--auth-benchmark-warmup"),
        artifact_dir=Path(request.config.getoption("--auth-benchmark-artifact-dir")),
        preset=preset,
    )
    if config.samples < 1:
        pytest.fail("auth benchmark samples must be a positive integer")
    if config.warmup < 0:
        pytest.fail("auth benchmark warmup must be zero or greater")
    return config


def _benchmark_app(factory: sessionmaker[Session]):
    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    auth_app.dependency_overrides[get_db] = override_get_db
    return auth_app


def _seed_dataset(session: Session, config: BenchmarkConfig) -> SeedTargets:
    tables = config.preset.service_tables(SERVICE_NAME)
    measured_total = config.samples + config.warmup
    if tables["users"] < 2:
        pytest.fail("auth benchmark preset must include at least two users")
    if tables["refresh_tokens"] < measured_total:
        pytest.fail("auth benchmark preset must include enough refresh_tokens for refresh-token measurements")

    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    password_hash = hash_password(BENCHMARK_PASSWORD)
    for rows in chunked(_user_rows(tables["users"], password_hash, now)):
        session.execute(insert(User), rows)
    for rows in chunked(_audit_log_rows(tables["audit_logs"], now)):
        session.execute(insert(AuditLog), rows)
    refresh_tokens = [f"bench-refresh-token-{index:06d}" for index in range(tables["refresh_tokens"])]
    for rows in chunked(_refresh_token_rows(refresh_tokens, now)):
        session.execute(insert(RefreshToken), rows)
    session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT max(id) FROM users))"))
    session.execute(text("SELECT setval(pg_get_serial_sequence('audit_logs', 'id'), (SELECT max(id) FROM audit_logs))"))
    session.execute(text("SELECT setval(pg_get_serial_sequence('refresh_tokens', 'id'), (SELECT max(id) FROM refresh_tokens))"))

    customer_id = 2
    admin_id = 1
    customer_email = _user_email(customer_id)
    admin_email = _user_email(admin_id)
    access_token, _token_id, _expires_at = create_access_token(
        user_id=customer_id,
        email=customer_email,
        role="CUSTOMER",
    )
    admin_access_token, _admin_token_id, _admin_expires_at = create_access_token(
        user_id=admin_id,
        email=admin_email,
        role="ADMIN",
    )
    return SeedTargets(
        customer_id=customer_id,
        customer_email=customer_email,
        admin_id=admin_id,
        admin_email=admin_email,
        access_token=access_token,
        admin_access_token=admin_access_token,
        refresh_tokens=refresh_tokens[:measured_total],
    )


def _user_rows(total: int, password_hash: str, now: datetime):
    for index in range(total):
        user_id = index + 1
        role = "ADMIN" if user_id == 1 else "CUSTOMER"
        yield {
            "id": user_id,
            "email": _user_email(user_id),
            "password_hash": password_hash,
            "display_name": f"Benchmark User {user_id:06d}",
            "role": role,
            "is_active": True,
            "created_at": now - timedelta(seconds=index),
        }


def _audit_log_rows(total: int, now: datetime):
    for index in range(total):
        user_id = 1 if index % 25 == 0 else (index % 9999) + 2
        yield {
            "event_type": "LOGIN_SUCCEEDED" if index % 3 else "ME_VIEWED",
            "outcome": "ALLOW",
            "user_id": user_id,
            "user_email": _user_email(user_id),
            "role": "ADMIN" if user_id == 1 else "CUSTOMER",
            "request_id": f"bench-request-{index:06d}",
            "method": "GET",
            "path": "/auth/me",
            "client_ip": "127.0.0.1",
            "user_agent": "api-benchmark",
            "details": None,
            "created_at": now - timedelta(seconds=index),
        }


def _refresh_token_rows(tokens: list[str], now: datetime):
    for index, token in enumerate(tokens):
        yield {
            "token_hash": hash_refresh_token(token),
            "user_id": 2,
            "expires_at": now + timedelta(days=7, seconds=index),
            "revoked_at": None,
            "created_at": now - timedelta(seconds=index),
        }


def _user_email(user_id: int) -> str:
    if user_id == 1:
        return "bench-admin@example.test"
    return f"bench-user-{user_id:06d}@example.test"


def _benchmark_endpoints(targets: SeedTargets) -> list[EndpointCase]:
    return [
        EndpointCase(
            name="login-customer",
            method="POST",
            path=lambda _: "/auth/login",
            status=200,
            json_body=lambda _: {"email": targets.customer_email, "password": BENCHMARK_PASSWORD},
        ),
        EndpointCase(
            name="signup-customer",
            method="POST",
            path=lambda index: "/auth/signup",
            status=201,
            json_body=lambda index: {
                "email": f"bench-signup-{index:06d}@example.test",
                "password": BENCHMARK_PASSWORD,
                "displayName": f"Benchmark Signup {index:06d}",
            },
        ),
        EndpointCase(
            name="me-customer",
            method="GET",
            path=lambda _: "/auth/me",
            status=200,
            headers=lambda _: _bearer_headers(targets.access_token),
        ),
        EndpointCase(
            name="refresh-token",
            method="POST",
            path=lambda _: "/auth/refresh",
            status=200,
            json_body=lambda index: {"refreshToken": targets.refresh_tokens[index]},
        ),
        EndpointCase(
            name="audit-logs-admin",
            method="GET",
            path=lambda _: "/auth/audit-logs",
            status=200,
            headers=lambda _: _bearer_headers(targets.admin_access_token),
        ),
    ]


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _measure_endpoint(client: TestClient, endpoint: EndpointCase, config: BenchmarkConfig) -> dict[str, Any]:
    durations: list[float] = []
    total = config.warmup + config.samples
    for iteration in range(total):
        started = time.perf_counter_ns()
        response = client.request(
            endpoint.method,
            endpoint.path(iteration),
            json=endpoint.json_body(iteration) if endpoint.json_body else None,
            headers=endpoint.headers(iteration) if endpoint.headers else None,
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if response.status_code != endpoint.status:
            pytest.fail(f"{endpoint.name} returned HTTP {response.status_code}: {response.text}")
        if iteration >= config.warmup:
            durations.append(elapsed_ms)
    return _metric(endpoint, durations, config)


def _metric(endpoint: EndpointCase, durations: list[float], config: BenchmarkConfig) -> dict[str, Any]:
    return {
        "serviceName": SERVICE_NAME,
        "datasetPreset": config.preset.name,
        "seedRows": config.preset.service_tables(SERVICE_NAME),
        "endpoint": endpoint.name,
        "method": endpoint.method,
        "status": endpoint.status,
        "samples": len(durations),
        "warmup": config.warmup,
        "minMs": round(min(durations), 3),
        "p50Ms": round(_percentile(durations, 50), 3),
        "p95Ms": round(_percentile(durations, 95), 3),
        "p99Ms": round(_percentile(durations, 99), 3),
        "maxMs": round(max(durations), 3),
    }


def _query_analysis(session: Session, targets: SeedTargets, config: BenchmarkConfig) -> list[dict[str, Any]]:
    sample_note = percentile_interpretation(config.samples)
    tables = config.preset.service_tables(SERVICE_NAME)
    return [
        {
            "endpoint": "login-customer",
            "queries": [
                explain_postgres_sql(
                    session,
                    label="user-by-email",
                    sql="SELECT id, email, password_hash FROM users WHERE email = :email LIMIT 1",
                    params={"email": targets.customer_email},
                    query_shape="SELECT users WHERE email",
                    index_decision="email unique index 유지. 추가 인덱스보다 password verify 비용을 분리해서 본다.",
                    data_analysis=f"users={tables['users']:,}. 로그인 p50/p95는 DB보다 password hash 검증 영향이 크다.",
                )
            ],
            "sampleInterpretation": sample_note,
        },
        {
            "endpoint": "signup-customer",
            "queries": [
                explain_postgres_sql(
                    session,
                    label="signup-email-duplicate-check",
                    sql="SELECT id FROM users WHERE email = :email LIMIT 1",
                    params={"email": "bench-signup-explain@example.test"},
                    query_shape="SELECT users WHERE email, INSERT users",
                    index_decision="중복 이메일 방어에는 현재 unique index가 맞다.",
                    data_analysis="신규 email은 miss path라 table 규모 영향은 작고 password hash + insert 비용이 중심이다.",
                )
            ],
            "sampleInterpretation": sample_note,
        },
        {
            "endpoint": "me-customer",
            "queries": [
                explain_postgres_sql(
                    session,
                    label="user-by-id",
                    sql="SELECT id, email, role FROM users WHERE id = :id",
                    params={"id": targets.customer_id},
                    query_shape="SELECT users WHERE id",
                    index_decision="PK 조회 유지. 감사 로그 insert가 같이 붙는다.",
                    data_analysis=f"단일 사용자 조회라 users={tables['users']:,} 규모보다 JWT 검증과 audit insert 변동을 본다.",
                )
            ],
            "sampleInterpretation": sample_note,
        },
        {
            "endpoint": "refresh-token",
            "queries": [
                explain_postgres_sql(
                    session,
                    label="refresh-token-by-hash",
                    sql="SELECT id, user_id, revoked_at FROM refresh_tokens WHERE token_hash = :token_hash LIMIT 1",
                    params={"token_hash": hash_refresh_token(targets.refresh_tokens[0])},
                    query_shape="SELECT refresh_tokens WHERE token_hash",
                    index_decision="refresh token lookup은 unique index로 충분하다.",
                    data_analysis=f"refresh_tokens={tables['refresh_tokens']:,}. token hash 계산, revoke update, token 재발급 비용을 함께 본다.",
                )
            ],
            "sampleInterpretation": sample_note,
        },
        {
            "endpoint": "audit-logs-admin",
            "queries": [
                explain_postgres_sql(
                    session,
                    label="audit-logs-latest",
                    sql="SELECT id, event_type, created_at FROM audit_logs ORDER BY id DESC LIMIT 100",
                    params={},
                    query_shape="SELECT audit_logs ORDER BY id DESC LIMIT 100",
                    index_decision="최근 100건 조회는 id index 역순 scan으로 유지한다.",
                    data_analysis=f"audit_logs={tables['audit_logs']:,}. 응답 100건 직렬화 비용이 함께 포함된다.",
                )
            ],
            "sampleInterpretation": sample_note,
        },
    ]


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = max(math.ceil(len(ordered) * percentile / 100) - 1, 0)
    return ordered[index]


def _artifact(
    started_at: datetime,
    config: BenchmarkConfig,
    metrics: list[dict[str, Any]],
    query_analysis: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generatedAt": started_at.isoformat(),
        "finishedAt": datetime.now(UTC).isoformat(),
        "serviceName": SERVICE_NAME,
        "datasetPreset": config.preset.name,
        "datasetPresetPath": str(config.preset.path.relative_to(SERVICE_REPO_ROOT)),
        "seed": config.preset.seed_summary(SERVICE_NAME),
        "service": _git_info(SERVICE_REPO_ROOT),
        "benchmark": {
            "samplesPerEndpoint": config.samples,
            "warmup": config.warmup,
            "endpoints": metrics,
        },
        "queryAnalysis": query_analysis,
        "constraints": [
            "FastAPI TestClient measures router, dependency, service, and repository code paths together.",
            "PostgreSQL runs in testcontainers postgres:16-alpine and is removed when the test ends.",
            "Seed/setup work runs before the measured loop.",
            "Tokens and passwords are used only inside the benchmark process and are not written to artifacts.",
            "This benchmark measures one API request at a time against a seeded database; it is not a concurrent load test.",
        ],
    }


def _write_artifact(directory: Path, artifact: dict[str, Any], started_at: datetime) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    output = json.dumps(artifact, indent=2, sort_keys=True)
    (directory / f"{timestamp}.json").write_text(output + "\n", encoding="utf-8")
    (directory / "latest.json").write_text(output + "\n", encoding="utf-8")


def _git_info(repo_root: Path) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "head": head.stdout.strip(),
        "dirty": bool(status.stdout.strip()),
        "statusShort": status.stdout.splitlines(),
        "servicePath": os.getcwd(),
    }
