from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

import structlog
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI, Request

from observability.config import ObservabilityConfig
from observability.logging import configure_structured_logging
from observability.tracing import configure_tracing, current_trace_context


REQUEST_ID_HEADER = "X-Request-Id"
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_current_request_id() -> str | None:
    return request_id_context.get()


def setup_request_observability(app: FastAPI, config: ObservabilityConfig) -> None:
    configure_structured_logging()
    configure_tracing(config)
    _instrument_fastapi(app)
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=REQUEST_ID_HEADER,
        update_request_header=True,
        validator=_valid_request_id,
    )

    logger = structlog.get_logger(config.service_name)

    @app.middleware("http")
    async def request_observability_middleware(request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        request_id_token = request_id_context.set(request_id)
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            route = _route_template(request)
            duration_seconds = perf_counter() - started_at
            trace_id, span_id = current_trace_context()
            logger.info(
                "http.request.completed",
                **{
                    "service.name": config.service_name,
                    "severity": "INFO",
                    "severity_text": "INFO",
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "request_id": request_id,
                    "http.method": request.method,
                    "http.route": route,
                    "http.status_code": status_code,
                    "duration_ms": int(duration_seconds * 1000),
                },
            )
            request_id_context.reset(request_id_token)


def _instrument_fastapi(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


def _request_id(request: Request) -> str:
    return correlation_id.get() or request.headers.get(REQUEST_ID_HEADER) or request.headers.get("x-request-id") or str(uuid4())


def _valid_request_id(request_id: str) -> bool:
    return bool(request_id.strip())


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path or request.url.path)
