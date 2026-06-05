from __future__ import annotations

import asyncio
import json
from concurrent.futures import CancelledError as FutureCancelledError

from middleware.request_context import REQUEST_ID_HEADER, get_current_request_id
from middleware.types import ASGIApp, Message, Receive, Scope, Send


class RuntimeRecoveryMiddleware:
    """처리되지 않은 일반 Exception을 500 응답으로 바꾸는 미들웨어.

    도메인 에러나 validation error의 응답 모양은 FastAPI exception handler가
    담당한다. 이 미들웨어는 예상하지 못한 런타임 예외가 발생했는데 아직
    응답을 보내지 않은 경우에만 최소 500 JSON 응답을 만든다.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # HTTP 요청이 아니면 500 응답 처리 대상이 아니므로 다음 ASGI app으로 넘긴다.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 응답이 이미 시작되면 상태 코드와 헤더를 바꿀 수 없으므로, 시작 여부를 추적한다.
        response_started = False

        async def track_response_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            # 다음 ASGI app이 보내는 응답 시작 메시지를 확인하면서 정상 처리를 먼저 시도한다.
            await self.app(scope, receive, track_response_start)
        except Exception as exc:
            # 취소 계열 예외와 이미 응답이 시작된 뒤의 실패는 500 응답으로 바꾸지 않고 그대로 전파한다.
            if _is_cancellation(exc) or response_started:
                raise
            # 아직 응답이 시작되지 않은 일반 Exception만 최소 500 JSON 응답으로 변환한다.
            await _send_internal_server_error(send)


def _is_cancellation(exc: Exception) -> bool:
    return isinstance(exc, asyncio.CancelledError | FutureCancelledError)


async def _send_internal_server_error(send: Send) -> None:
    # request_id가 있으면 장애 문의와 로그 조회에 사용할 수 있도록 응답 본문과 헤더에 함께 넣는다.
    request_id = get_current_request_id()
    payload: dict[str, object] = {
        "status": "error",
        "error": "internal_server_error",
    }
    headers = [(b"content-type", b"application/json")]

    if request_id is not None:
        payload["requestId"] = request_id
        headers.append((REQUEST_ID_HEADER.lower().encode("latin-1"), request_id.encode("latin-1")))

    # ASGI 응답은 start 메시지로 상태/헤더를 먼저 보내고 body 메시지로 본문을 보낸다.
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers.append((b"content-length", str(len(body)).encode("latin-1")))
    await send({"type": "http.response.start", "status": 500, "headers": headers})
    await send({"type": "http.response.body", "body": body})
