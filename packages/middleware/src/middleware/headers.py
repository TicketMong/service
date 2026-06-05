from __future__ import annotations

from middleware.request_context import REQUEST_ID_HEADER, get_current_request_id
from middleware.types import ASGIApp, Message, Receive, Scope, Send


class ResponseHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, request_id_header: str = REQUEST_ID_HEADER) -> None:
        self.app = app
        self.request_id_header = request_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                request_id = get_current_request_id()
                if request_id is not None:
                    _set_header(message, self.request_id_header, request_id)
            await send(message)

        await self.app(scope, receive, send_with_request_id)


def _set_header(message: Message, header_name: str, header_value: str) -> None:
    normalized = header_name.lower().encode("latin-1")
    headers = [(name, value) for name, value in message.get("headers", []) if name.lower() != normalized]
    headers.append((normalized, header_value.encode("latin-1")))
    message["headers"] = headers
