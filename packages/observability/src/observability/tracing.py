from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Protocol

from opentelemetry import propagate, trace
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.util.types import AttributeValue

from observability.callsite import find_application_callsite
from observability.config import DEFAULT_CALLSITE_MODULE_PREFIXES, ObservabilityConfig


_tracing_configured = False
_MANUAL_TRACER_NAME = "observability.manual"

TraceScalarValue = str | int | float | bool
TraceAttributeValue = TraceScalarValue | Sequence[TraceScalarValue]


@dataclass(frozen=True)
class TraceContext:
    """비동기 경계에 보관할 수 있는 trace 전파 값."""

    carrier: dict[str, str]
    trace_id: str | None = None
    span_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "carrier": dict(self.carrier),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }


class TraceRecorder(Protocol):
    """서비스 코드에서 허용하는 제한된 수동 trace 포트."""

    def attribute(self, key: str, value: TraceAttributeValue) -> None:
        """현재 span에 안전한 attribute를 기록한다."""

    def event(self, name: str, attributes: Mapping[str, TraceAttributeValue] | None = None) -> None:
        """현재 span에 중요한 처리 event를 기록한다."""

    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceAttributeValue] | None = None,
    ) -> AbstractContextManager[None]:
        """주요 단계를 child span으로 측정한다."""


class OpenTelemetryTraceRecorder:
    """OpenTelemetry current span을 매 호출 시점에 조회하는 수동 trace facade."""

    def attribute(self, key: str, value: TraceAttributeValue) -> None:
        span = _current_valid_span()
        if span is None:
            return
        span.set_attribute(_require_trace_name(key, "attribute key"), _safe_attribute_value(value))

    def event(self, name: str, attributes: Mapping[str, TraceAttributeValue] | None = None) -> None:
        span = _current_valid_span()
        if span is None:
            return
        span.add_event(_require_trace_name(name, "event name"), attributes=_safe_attributes(attributes))

    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceAttributeValue] | None = None,
    ) -> AbstractContextManager[None]:
        if _current_valid_span() is None:
            return nullcontext()
        tracer = trace.get_tracer(_MANUAL_TRACER_NAME)
        span_name = _require_trace_name(name, "span name")
        return tracer.start_as_current_span(
            span_name,
            attributes=_safe_attributes(attributes),
        )


class NoopTraceRecorder:
    """trace가 없는 실행 경로에서 안전하게 사용할 수 있는 recorder."""

    def attribute(self, key: str, value: TraceAttributeValue) -> None:
        return None

    def event(self, name: str, attributes: Mapping[str, TraceAttributeValue] | None = None) -> None:
        return None

    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceAttributeValue] | None = None,
    ) -> AbstractContextManager[None]:
        return nullcontext()


def trace_recorder() -> TraceRecorder:
    return OpenTelemetryTraceRecorder()


def start_trace_span(
    name: str,
    attributes: Mapping[str, TraceAttributeValue] | None = None,
) -> AbstractContextManager[None]:
    """요청 span이 없는 background 작업에서 root span을 시작한다."""
    tracer = trace.get_tracer(_MANUAL_TRACER_NAME)
    span_name = _require_trace_name(name, "span name")
    return tracer.start_as_current_span(
        span_name,
        attributes=_safe_attributes(attributes),
    )


def capture_current_trace_context() -> TraceContext | None:
    """현재 span context를 outbox 같은 비동기 저장소에 넣을 값으로 캡처한다."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    trace_id, span_id = current_trace_context()
    sanitized_carrier = {
        key: value
        for key, value in carrier.items()
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip()
    }
    if not sanitized_carrier and not trace_id and not span_id:
        return None
    return TraceContext(
        carrier=sanitized_carrier,
        trace_id=trace_id or None,
        span_id=span_id or None,
    )


def configure_process_tracing(config: ObservabilityConfig) -> None:
    """서비스 시작 시 프로세스 전체 OpenTelemetry tracer provider를 설정한다.

    이 함수는 OpenTelemetry provider registry를 바꾸므로 전역 부작용이 있다.
    의존성으로 주입해 쓰는 객체가 아니라, 앱 시작 단계에서 한 번 붙이는 배선으로 본다.
    런타임 선택은 ObservabilityConfig로만 받아 env 해석 지점을 한 곳에 묶어 둔다.
    """
    global _tracing_configured

    # Tracer provider는 프로세스 전체에 걸리므로 여러 번 호출돼도 한 번만 설정한다.
    if _tracing_configured or config.otel_sdk_disabled:
        return

    # Resource attribute는 Tempo/Grafana에서 서비스를 찾을 때 쓰는 기본 식별자다.
    attributes: dict[str, str] = {SERVICE_NAME: config.service_name}
    if config.service_version:
        attributes[SERVICE_VERSION] = config.service_version
    if config.service_environment:
        attributes[DEPLOYMENT_ENVIRONMENT] = config.service_environment

    provider = TracerProvider(resource=Resource.create(attributes))
    provider.add_span_processor(CallsiteSpanProcessor(config.callsite_module_prefixes))
    if _pyroscope_span_profiles_enabled(config):
        provider.add_span_processor(_pyroscope_span_processor())
    if _otlp_trace_export_enabled(config):
        # exporter가 env를 다시 해석하지 않도록, 앞에서 확정한 endpoint만 넘긴다.
        provider.add_span_processor(BatchSpanProcessor(_otlp_span_exporter(config.otlp_trace_exporter_endpoint)))
    trace.set_tracer_provider(provider)
    _tracing_configured = True


# 아직 process 단위 이름으로 옮기지 못한 호출부를 위한 호환 이름이다.
configure_tracing = configure_process_tracing


def current_trace_context() -> tuple[str, str]:
    """현재 실행 context의 trace_id와 span_id를 반환한다.

    이 함수는 전역 함수지만 trace_id/span_id를 전역 변수에 저장하지 않는다.
    OpenTelemetry는 Python의 contextvars를 통해 async task/thread별 current span을
    관리하므로, FastAPI 요청 처리 중 호출하면 각 요청의 active span 값을 읽는다.

    예:
      요청 A의 handler 안에서 호출 -> 요청 A의 trace_id/span_id
      요청 B의 handler 안에서 호출 -> 요청 B의 trace_id/span_id
      요청 밖 dispatcher/background loop에서 호출 -> 유효한 current span이 없으면 빈 문자열
    """
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "", ""
    return format(span_context.trace_id, "032x"), format(span_context.span_id, "016x")


def set_current_span_attribute(key: str, value: AttributeValue | None) -> None:
    if value is None:
        return
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return
    span.set_attribute(key, value)


def set_current_span_attributes(attributes: dict[str, AttributeValue | None]) -> None:
    for key, value in attributes.items():
        set_current_span_attribute(key, value)


class CallsiteSpanProcessor(SpanProcessor):
    """span 시작 시점의 앱 코드 위치를 `code.*` attribute로 붙인다.

    OpenTelemetry SDK는 `TracerProvider.add_span_processor()`로 등록된
    processor의 `on_start()`를 span이 시작될 때 동기 호출한다. 이 위치에서
    실행 stack을 보면 자동 instrumentation span도 어떤 앱 코드 경계에서
    시작됐는지 찾을 수 있다.

    docs: https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html#opentelemetry.sdk.trace.SpanProcessor
    """

    def __init__(self, module_prefixes: Sequence[str] | None = None) -> None:
        self._module_prefixes = (
            tuple(module_prefixes) if module_prefixes is not None else DEFAULT_CALLSITE_MODULE_PREFIXES
        )

    def on_start(self, span: object, parent_context: object | None = None) -> None:
        del parent_context
        callsite = find_application_callsite(self._module_prefixes)
        if callsite is None:
            return
        for key, value in callsite.as_trace_attributes().items():
            span.set_attribute(key, value)

    def on_end(self, span: object) -> None:
        del span

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        del timeout_millis
        return True


def _current_valid_span() -> object | None:
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return None
    return span


def _require_trace_name(value: str, label: str) -> str:
    if not value:
        raise ValueError(f"{label} must not be empty")
    return value


def _safe_attributes(attributes: Mapping[str, TraceAttributeValue] | None) -> dict[str, AttributeValue] | None:
    if attributes is None:
        return None
    return {_require_trace_name(key, "attribute key"): _safe_attribute_value(value) for key, value in attributes.items()}


def _safe_attribute_value(value: TraceAttributeValue) -> AttributeValue:
    if _safe_scalar(value):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = tuple(value)
        for item in values:
            if not _safe_scalar(item):
                raise TypeError("trace attribute sequences can contain only str, int, float, or bool values")
        return values
    raise TypeError("trace attributes can contain only str, int, float, bool, or sequences of those values")


def _safe_scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _otlp_trace_export_enabled(config: ObservabilityConfig) -> bool:
    # trace 전송은 명시적으로 OTLP를 고르고 endpoint도 있을 때만 허용한다.
    traces_exporter = config.otel_traces_exporter.strip().lower()
    if traces_exporter == "none":
        return False
    if traces_exporter != "otlp":
        return False
    return bool(config.otlp_trace_exporter_endpoint)


def _pyroscope_span_profiles_enabled(config: ObservabilityConfig) -> bool:
    return config.profiling.enabled and config.profiling.span_profiles_enabled


def _pyroscope_span_processor() -> object:
    from pyroscope.otel import PyroscopeSpanProcessor

    return PyroscopeSpanProcessor()


def _otlp_span_exporter(endpoint: str | None) -> object:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(endpoint=endpoint)
