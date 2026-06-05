import json
import logging

from errors import in_domain
from fastapi import FastAPI
from fastapi.testclient import TestClient
from middleware import install_runtime_middleware

from observability import error_context as error_context_module
from observability import exceptions as exceptions_module
from observability import fastapi as fastapi_module
from observability import kafka as kafka_module
from observability import (
    OBSERVABILITY_ENV_KEYS,
    ObservabilityConfig,
    build_producer_headers,
    configure_process_logging,
    configure_process_tracing,
    create_request_log_middleware,
    instrument_fastapi_app,
    observability_config_from_env,
    record_exception,
)
from observability import tracing as tracing_module
from observability.tracing import _otlp_trace_export_enabled


def test_observability_config_from_env_maps_explicit_otel_settings() -> None:
    config = observability_config_from_env(
        "test-service",
        env={
            "SERVICE_VERSION": "1.2.3",
            "SERVICE_ENVIRONMENT": "staging",
            "OTEL_SDK_DISABLED": "true",
            "OTEL_TRACES_EXPORTER": "none",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://collector:4318/v1/traces",
        },
    )

    assert config == ObservabilityConfig(
        service_name="test-service",
        service_version="1.2.3",
        service_environment="staging",
        otel_sdk_disabled=True,
        otel_traces_exporter="none",
        otlp_trace_exporter_endpoint="http://collector:4318/v1/traces",
    )
    assert set(OBSERVABILITY_ENV_KEYS) == {
        "SERVICE_VERSION",
        "SERVICE_ENVIRONMENT",
        "OTEL_SDK_DISABLED",
        "OTEL_TRACES_EXPORTER",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    }


def test_observability_config_from_env_falls_back_to_common_otlp_endpoint() -> None:
    config = observability_config_from_env(
        "test-service",
        env={"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317"},
    )

    assert config.otlp_trace_exporter_endpoint == "http://collector:4317"


def test_otlp_trace_export_enabled_only_accepts_otlp_with_endpoint() -> None:
    assert _otlp_trace_export_enabled(
        ObservabilityConfig(
            service_name="test-service",
            otel_traces_exporter="otlp",
            otlp_trace_exporter_endpoint="http://collector:4317",
        )
    )
    assert not _otlp_trace_export_enabled(
        ObservabilityConfig(
            service_name="test-service",
            otel_traces_exporter="none",
            otlp_trace_exporter_endpoint="http://collector:4317",
        )
    )
    assert not _otlp_trace_export_enabled(
        ObservabilityConfig(
            service_name="test-service",
            otel_traces_exporter="zipkin",
            otlp_trace_exporter_endpoint="http://collector:4317",
        )
    )
    assert not _otlp_trace_export_enabled(ObservabilityConfig(service_name="test-service", otel_traces_exporter="otlp"))


def test_configure_tracing_passes_explicit_otlp_trace_endpoint(monkeypatch) -> None:
    exporters: list[str | None] = []
    providers: list[object] = []

    class FakeBatchSpanProcessor:
        def __init__(self, exporter: object) -> None:
            self.exporter = exporter

    class FakeTracerProvider:
        def __init__(self, *, resource: object) -> None:
            self.resource = resource
            self.span_processors: list[FakeBatchSpanProcessor] = []

        def add_span_processor(self, processor: FakeBatchSpanProcessor) -> None:
            self.span_processors.append(processor)

    def fake_otlp_span_exporter(endpoint: str | None) -> object:
        exporters.append(endpoint)
        return object()

    monkeypatch.setattr(tracing_module, "_tracing_configured", False)
    monkeypatch.setattr(tracing_module, "BatchSpanProcessor", FakeBatchSpanProcessor)
    monkeypatch.setattr(tracing_module, "_otlp_span_exporter", fake_otlp_span_exporter)
    monkeypatch.setattr(tracing_module, "TracerProvider", FakeTracerProvider)
    monkeypatch.setattr(tracing_module.trace, "set_tracer_provider", providers.append)

    configure_process_tracing(
        ObservabilityConfig(
            service_name="test-service",
            otel_traces_exporter="otlp",
            otlp_trace_exporter_endpoint="http://collector:4318/v1/traces",
        )
    )

    assert exporters == ["http://collector:4318/v1/traces"]
    assert providers


def test_configure_tracing_skips_unsupported_trace_exporter(monkeypatch) -> None:
    exporters: list[str | None] = []

    def fake_otlp_span_exporter(endpoint: str | None) -> object:
        exporters.append(endpoint)
        return object()

    monkeypatch.setattr(tracing_module, "_tracing_configured", False)
    monkeypatch.setattr(tracing_module, "_otlp_span_exporter", fake_otlp_span_exporter)
    monkeypatch.setattr(tracing_module.trace, "set_tracer_provider", lambda provider: None)

    configure_process_tracing(
        ObservabilityConfig(
            service_name="test-service",
            otel_traces_exporter="zipkin",
            otlp_trace_exporter_endpoint="http://collector:4317",
        )
    )

    assert exporters == []


def test_request_observability_emits_single_line_json_log(caplog, monkeypatch) -> None:
    span_attributes: dict[str, object] = {}
    monkeypatch.setattr(fastapi_module, "set_current_span_attributes", span_attributes.update)
    app = _observed_app(ObservabilityConfig(service_name="test-service"))

    @app.get("/items/{item_id}")
    def get_item(item_id: str) -> dict[str, str]:
        return {"itemId": item_id}

    caplog.set_level(logging.INFO)
    client = TestClient(app)

    response = client.get(
        "/items/item-1",
        headers={"X-Request-Id": "req-test", "X-Client-Action-Id": "act-test"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-test"
    log = _request_log(caplog.records)
    assert log["service.name"] == "test-service"
    assert log["severity"] == "INFO"
    assert log["severity_text"] == "INFO"
    assert log["request_id"] == "req-test"
    assert log["client_action_id"] == "act-test"
    assert log["trace_id"]
    assert log["span_id"]
    assert log["http.method"] == "GET"
    assert log["http.route"] == "/items/{item_id}"
    assert log["http.status_code"] == 200
    assert isinstance(log["duration_ms"], int)
    assert span_attributes["request_id"] == "req-test"
    assert span_attributes["http.route"] == "/items/{item_id}"


def test_request_observability_logs_failed_request_fields(caplog) -> None:
    app = _observed_app(ObservabilityConfig(service_name="test-service"))
    caplog.set_level(logging.INFO)
    client = TestClient(app)

    response = client.get("/missing", headers={"X-Request-Id": "req-missing"})

    assert response.status_code == 404
    log = _request_log(caplog.records)
    assert log["request_id"] == "req-missing"
    assert log["trace_id"]
    assert log["span_id"]
    assert log["service.name"] == "test-service"
    assert log["severity"] == "INFO"
    assert log["http.status_code"] == 404
    assert isinstance(log["duration_ms"], int)


def test_error_context_reads_errors_package_context() -> None:
    exc = RuntimeError("seat already reserved")
    in_domain("reservation").code("reservation.conflict").with_attr("seat_id", "seat-A1").attach(exc)

    context = error_context_module.extract_error_context(exc)

    assert context["error.code"] == "reservation.conflict"
    assert context["error.domain"] == "reservation"
    assert context["error.attr.seat_id"] == "seat-A1"
    assert context["error.occurred_at"]


def test_record_exception_marks_span_and_deduplicates(monkeypatch) -> None:
    span = FakeSpan()
    monkeypatch.setattr(exceptions_module.trace, "get_current_span", lambda: span)
    monkeypatch.setattr(exceptions_module, "current_trace_context", lambda: ("trace-1", "span-1"))

    exc = RuntimeError("boom")
    first = record_exception(exc, service_name="test-service", attributes={"error.domain": "test"})
    second = record_exception(exc, service_name="test-service")

    assert first is True
    assert second is False
    assert span.recorded_exception is exc
    assert span.status_code == "ERROR"
    assert span.attributes["error.type"] == "RuntimeError"
    assert span.attributes["error.domain"] == "test"


def test_kafka_producer_headers_use_protocol_headers(monkeypatch) -> None:
    def fake_inject(carrier: dict[str, str]) -> None:
        carrier["traceparent"] = "00-trace-span-01"
        carrier["tracestate"] = "vendor=value"

    monkeypatch.setattr(kafka_module.propagate, "inject", fake_inject)

    headers = dict(build_producer_headers({"eventId": "evt-1", "correlationId": "req-1"}))

    assert headers[b"traceparent".decode()] == b"00-trace-span-01"
    assert headers[b"tracestate".decode()] == b"vendor=value"
    assert headers[b"correlation_id".decode()] == b"req-1"


def _observed_app(config: ObservabilityConfig) -> FastAPI:
    app = FastAPI()
    configure_process_logging()
    configure_process_tracing(config)
    instrument_fastapi_app(app)
    app.middleware("http")(create_request_log_middleware(config))
    install_runtime_middleware(app)
    return app


def _request_log(records: list[logging.LogRecord]) -> dict[str, object]:
    for record in reversed(records):
        if record.name == "test-service" and record.message.startswith("{"):
            payload = json.loads(record.message)
            if payload.get("event") == "http.request.completed":
                return payload
    raise AssertionError("request JSON log was not emitted")


class FakeSpanContext:
    is_valid = True


class FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.recorded_exception: BaseException | None = None
        self.status_code: str | None = None

    def get_span_context(self) -> FakeSpanContext:
        return FakeSpanContext()

    def record_exception(self, exc: BaseException) -> None:
        self.recorded_exception = exc

    def set_status(self, status: object) -> None:
        self.status_code = getattr(getattr(status, "status_code", None), "name", None)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value
