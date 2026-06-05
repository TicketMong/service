from __future__ import annotations

from typing import Protocol

from middleware.headers import ResponseHeadersMiddleware
from middleware.recovery import RuntimeRecoveryMiddleware
from middleware.request_context import RequestContextMiddleware, request_context_middleware_options


class MiddlewareApp(Protocol):
    def add_middleware(self, middleware_class: type[object], **options: object) -> None: ...


def install_runtime_middleware(app: MiddlewareApp) -> None:
    app.add_middleware(RuntimeRecoveryMiddleware)
    app.add_middleware(ResponseHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware, **request_context_middleware_options())
