from __future__ import annotations

from typing import Protocol

from middleware.headers import ResponseHeadersMiddleware
from middleware.recovery import RuntimeRecoveryMiddleware
from middleware.request_context import RequestContextMiddleware, request_context_middleware_options


class MiddlewareApp(Protocol):
    def add_middleware(self, middleware_class: type[object], **options: object) -> None: ...


def install_runtime_middleware(app: MiddlewareApp) -> None:
    """FastAPI 앱에 Medikong 공통 런타임 미들웨어를 표준 순서로 등록한다.

    FastAPI는 마지막에 등록한 미들웨어를 요청 처리 때 먼저 실행한다.
    아래 순서로 등록하면 RequestContextMiddleware가 요청 컨텍스트를 먼저
    만들고, ResponseHeadersMiddleware가 응답 헤더를 맞추며,
    RuntimeRecoveryMiddleware가 아직 응답하지 못한 일반 예외를 500 응답으로 바꾼다.
    """

    app.add_middleware(RuntimeRecoveryMiddleware)
    app.add_middleware(ResponseHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware, **request_context_middleware_options())
