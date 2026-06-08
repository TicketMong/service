from __future__ import annotations

import asyncio
import traceback
from collections.abc import Mapping
from concurrent.futures import CancelledError as FutureCancelledError
from typing import Final

import structlog
from middleware.request_context import get_current_request_id
from middleware.types import ASGIApp, Receive, Scope, Send
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.types import AttributeValue

from observability.error_context import extract_error_context
from observability.tracing import current_trace_context, set_current_span_attributes


_RECORDED_ATTR: Final = "__medikong_observability_recorded__"


def record_exception(
    exc: BaseException,
    *,
    service_name: str,
    attributes: Mapping[str, AttributeValue] | None = None,
) -> bool:
    """Record one exception on the current span and structured log."""
    if is_exception_recorded(exc):
        return False

    mark_exception_recorded(exc)
    error_attributes: dict[str, AttributeValue] = {
        "error.type": type(exc).__name__,
        **extract_error_context(exc),
    }
    if attributes:
        error_attributes.update(attributes)

    span = trace.get_current_span()
    if span.get_span_context().is_valid:
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        set_current_span_attributes(error_attributes)

    trace_id, span_id = current_trace_context()
    structlog.get_logger(service_name).error(
        "exception.recorded",
        **{
            "service.name": service_name,
            "severity": "ERROR",
            "severity_text": "ERROR",
            "trace_id": trace_id,
            "span_id": span_id,
            "request_id": get_current_request_id(),
            "error.type": type(exc).__name__,
            "error.message": str(exc),
            "exception.stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            **error_attributes,
        },
    )
    return True


def is_exception_recorded(exc: BaseException) -> bool:
    return bool(getattr(exc, _RECORDED_ATTR, False))


def mark_exception_recorded(exc: BaseException) -> None:
    setattr(exc, _RECORDED_ATTR, True)


class ErrorRecordingMiddleware:
    """Record unhandled exceptions and let downstream recovery decide the response."""

    def __init__(self, app: ASGIApp, *, service_name: str) -> None:
        self.app = app
        self.service_name = service_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            if _is_cancellation(exc):
                raise
            record_exception(exc, service_name=self.service_name)
            raise


def _is_cancellation(exc: Exception) -> bool:
    return isinstance(exc, asyncio.CancelledError | FutureCancelledError)
