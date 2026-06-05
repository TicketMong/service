from observability.config import OBSERVABILITY_ENV_KEYS, ObservabilityConfig, observability_config_from_env
from observability.database import instrument_motor_client, instrument_sqlalchemy_engine
from observability.exceptions import ErrorRecordingMiddleware, record_exception
from observability.fastapi import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    create_request_log_middleware,
    get_current_request_id,
    instrument_fastapi_app,
    request_id_middleware_options,
)
from observability.fastapi_errors import HttpError, error_response, register_error_handlers
from observability.kafka import build_producer_headers, kafka_message_attributes, start_consumer_span
from observability.logging import configure_process_logging, configure_structured_logging
from observability.tracing import (
    NoopTraceRecorder,
    TraceRecorder,
    configure_process_tracing,
    configure_tracing,
    set_current_span_attributes,
    trace_recorder,
)

__all__ = [
    "OBSERVABILITY_ENV_KEYS",
    "REQUEST_ID_HEADER",
    "RequestIdMiddleware",
    "ErrorRecordingMiddleware",
    "HttpError",
    "ObservabilityConfig",
    "NoopTraceRecorder",
    "build_producer_headers",
    "configure_process_logging",
    "configure_process_tracing",
    "configure_structured_logging",
    "configure_tracing",
    "create_request_log_middleware",
    "error_response",
    "get_current_request_id",
    "instrument_motor_client",
    "instrument_fastapi_app",
    "instrument_sqlalchemy_engine",
    "kafka_message_attributes",
    "observability_config_from_env",
    "record_exception",
    "register_error_handlers",
    "request_id_middleware_options",
    "set_current_span_attributes",
    "start_consumer_span",
    "TraceRecorder",
    "trace_recorder",
]
