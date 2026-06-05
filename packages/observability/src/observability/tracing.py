from opentelemetry import trace
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from observability.config import ObservabilityConfig


_tracing_configured = False


def configure_tracing(config: ObservabilityConfig) -> None:
    global _tracing_configured

    # Tracer providers are process-wide; keep setup idempotent and let env config disable the SDK explicitly.
    if _tracing_configured or config.otel_sdk_disabled:
        return

    # Resource attributes are the stable service identity used when searching traces in Tempo/Grafana.
    attributes: dict[str, str] = {SERVICE_NAME: config.service_name}
    if config.service_version:
        attributes[SERVICE_VERSION] = config.service_version
    if config.service_environment:
        attributes[DEPLOYMENT_ENVIRONMENT] = config.service_environment

    provider = TracerProvider(resource=Resource.create(attributes))
    if _otlp_trace_export_enabled(config):
        # Export only from the resolved config so exporter internals do not silently reinterpret env vars.
        provider.add_span_processor(BatchSpanProcessor(_otlp_span_exporter(config.otlp_trace_exporter_endpoint)))
    trace.set_tracer_provider(provider)
    _tracing_configured = True


def current_trace_context() -> tuple[str, str]:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "", ""
    return format(span_context.trace_id, "032x"), format(span_context.span_id, "016x")


def _otlp_trace_export_enabled(config: ObservabilityConfig) -> bool:
    # Keep the exporter allowlist narrow: only explicit OTLP plus an endpoint should leave the process.
    traces_exporter = config.otel_traces_exporter.strip().lower()
    if traces_exporter == "none":
        return False
    if traces_exporter != "otlp":
        return False
    return bool(config.otlp_trace_exporter_endpoint)


def _otlp_span_exporter(endpoint: str | None) -> object:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(endpoint=endpoint)
