from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from middleware.types import ASGIApp, Receive, Scope, Send


REQUEST_ID_HEADER = "X-Request-Id"
CLIENT_ACTION_ID_HEADER = "X-Client-Action-Id"


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    client_action_id: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("medikong_request_context", default=None)


class RequestContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        request_id_header: str = REQUEST_ID_HEADER,
        client_action_id_header: str = CLIENT_ACTION_ID_HEADER,
    ) -> None:
        self.app = app
        self.request_id_header = request_id_header
        self.client_action_id_header = client_action_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        context = RequestContext(
            request_id=_header_or_generated(scope, self.request_id_header),
            client_action_id=_optional_header(scope, self.client_action_id_header),
        )
        state = scope.setdefault("state", {})
        state["request_id"] = context.request_id
        state["client_action_id"] = context.client_action_id
        token = _request_context.set(context)
        try:
            await self.app(scope, receive, send)
        finally:
            _request_context.reset(token)


def get_current_request_context() -> RequestContext | None:
    return _request_context.get()


def get_current_request_id() -> str | None:
    context = get_current_request_context()
    return context.request_id if context is not None else None


def get_current_client_action_id() -> str | None:
    context = get_current_request_context()
    return context.client_action_id if context is not None else None


def request_context_middleware_options() -> dict[str, str]:
    return {
        "request_id_header": REQUEST_ID_HEADER,
        "client_action_id_header": CLIENT_ACTION_ID_HEADER,
    }


def _header_or_generated(scope: Scope, header_name: str) -> str:
    value = _optional_header(scope, header_name)
    return value or str(uuid4())


def _optional_header(scope: Scope, header_name: str) -> str | None:
    normalized = header_name.lower().encode("latin-1")
    for name, value in scope.get("headers", []):
        if name.lower() != normalized:
            continue
        decoded = value.decode("latin-1").strip()
        return decoded or None
    return None
