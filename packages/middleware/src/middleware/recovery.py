from __future__ import annotations

import asyncio
import json
from concurrent.futures import CancelledError as FutureCancelledError

from middleware.request_context import REQUEST_ID_HEADER, get_current_request_id
from middleware.types import ASGIApp, Message, Receive, Scope, Send


class RuntimeRecoveryMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def track_response_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, track_response_start)
        except Exception as exc:
            if _is_cancellation(exc) or response_started:
                raise
            await _send_internal_server_error(send)


def _is_cancellation(exc: Exception) -> bool:
    return isinstance(exc, asyncio.CancelledError | FutureCancelledError)


async def _send_internal_server_error(send: Send) -> None:
    request_id = get_current_request_id()
    payload: dict[str, object] = {
        "status": "error",
        "error": "internal_server_error",
    }
    headers = [(b"content-type", b"application/json")]

    if request_id is not None:
        payload["requestId"] = request_id
        headers.append((REQUEST_ID_HEADER.lower().encode("latin-1"), request_id.encode("latin-1")))

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers.append((b"content-length", str(len(body)).encode("latin-1")))
    await send({"type": "http.response.start", "status": 500, "headers": headers})
    await send({"type": "http.response.body", "body": body})
