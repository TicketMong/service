import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram


request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["service", "method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["service", "method", "path"],
)


def setup_request_logging(app: FastAPI, service_name: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(service_name)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            duration_seconds = time.perf_counter() - started
            duration_ms = int(duration_seconds * 1000)
            HTTP_REQUESTS_TOTAL.labels(
                service=service_name,
                method=request.method,
                path=request.url.path,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=service_name,
                method=request.method,
                path=request.url.path,
            ).observe(duration_seconds)
            logger.info(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "INFO",
                        "service": service_name,
                        "requestId": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "durationMs": duration_ms,
                    },
                    separators=(",", ":"),
                )
            )
            request_id_context.reset(token)
        response.headers["X-Request-Id"] = request_id
        return response
