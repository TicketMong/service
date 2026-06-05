"""Compatibility exports for services that still import server.observability.

The implementation lives in packages/observability so packages/server can stay
focused on operational endpoints, readiness, and metrics.
"""

from observability import (
    OBSERVABILITY_ENV_KEYS,
    REQUEST_ID_HEADER,
    ObservabilityConfig,
    configure_structured_logging,
    configure_tracing,
    get_current_request_id,
    observability_config_from_env,
    setup_request_observability,
)
from observability.tracing import _otlp_trace_export_enabled

__all__ = [
    "OBSERVABILITY_ENV_KEYS",
    "REQUEST_ID_HEADER",
    "ObservabilityConfig",
    "configure_structured_logging",
    "configure_tracing",
    "get_current_request_id",
    "observability_config_from_env",
    "setup_request_observability",
    "_otlp_trace_export_enabled",
]
