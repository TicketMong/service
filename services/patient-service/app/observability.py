import logging
import time
from contextvars import ContextVar
from uuid import uuid4

from fastapi import FastAPI, Request


logger = logging.getLogger("app.request")
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_current_request_id() -> str | None:
    return request_id_context.get()


def setup_request_logging(app: FastAPI, service_name: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request_id_token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request_id=%s service=%s method=%s path=%s status=%s duration_ms=%s",
                request_id,
                service_name,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
            request_id_context.reset(request_id_token)
