import logging

import structlog


_logging_configured = False
_logging_instrumented = False


def configure_process_logging() -> None:
    global _logging_configured, _logging_instrumented

    if not _logging_instrumented:
        _instrument_logging()
        _logging_instrumented = True

    if _logging_configured:
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(key="timestamp", fmt="iso", utc=True),
            structlog.processors.JSONRenderer(separators=(",", ":")),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _logging_configured = True


configure_structured_logging = configure_process_logging


def _instrument_logging() -> None:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor

    LoggingInstrumentor().instrument(set_logging_format=False)
