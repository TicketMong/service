"""Compatibility exports for services that still import server.observability.

The implementation lives in packages/observability so packages/server can stay
focused on operational endpoints, readiness, and metrics.
"""

from observability import (
    OBSERVABILITY_ENV_KEYS,
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    ObservabilityConfig,
    configure_process_logging,
    configure_process_tracing,
    configure_structured_logging,
    configure_tracing,
    create_request_log_middleware,
    get_current_request_id,
    instrument_fastapi_app,
    observability_config_from_env,
    request_id_middleware_options,
)
from observability.tracing import _otlp_trace_export_enabled

__all__ = [
    "OBSERVABILITY_ENV_KEYS",
    "REQUEST_ID_HEADER",
    "RequestIdMiddleware",
    "ObservabilityConfig",
    "configure_process_logging",
    "configure_process_tracing",
    "configure_structured_logging",
    "configure_tracing",
    "create_request_log_middleware",
    "get_current_request_id",
    "instrument_fastapi_app",
    "observability_config_from_env",
    "request_id_middleware_options",
    "_otlp_trace_export_enabled",
]
