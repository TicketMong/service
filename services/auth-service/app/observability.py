import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request


request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def setup_request_logging(app: FastAPI, service_name: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(service_name)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-Id"] = request_id
        logger.info(
            "service=%s request_id=%s method=%s path=%s status=%s duration_ms=%s",
            service_name,
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
