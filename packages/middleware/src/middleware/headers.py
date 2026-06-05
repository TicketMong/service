from __future__ import annotations

from middleware.request_context import REQUEST_ID_HEADER, get_current_request_id
from middleware.types import ASGIApp, Message, Receive, Scope, Send


class ResponseHeadersMiddleware:
    """응답 시작 시점에 현재 request_id를 X-Request-Id 헤더로 돌려준다.

    요청 처리 중 생성되거나 전달받은 request_id를 클라이언트도 확인할 수 있게
    응답 헤더에 싣는다. 실제 값은 RequestContextMiddleware가 보관한
    ContextVar에서 읽는다.
    """

    def __init__(self, app: ASGIApp, *, request_id_header: str = REQUEST_ID_HEADER) -> None:
        self.app = app
        self.request_id_header = request_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # HTTP 요청이 아니면 응답 헤더를 바꾸지 않고 다음 ASGI app으로 넘긴다.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_request_id(message: Message) -> None:
            # ASGI 응답은 start/body 메시지로 나뉘므로 헤더를 바꿀 수 있는 start 시점만 처리한다.
            if message["type"] == "http.response.start":
                request_id = get_current_request_id()
                if request_id is not None:
                    # 기존 X-Request-Id가 있으면 현재 요청 컨텍스트 값을 기준으로 덮어쓴다.
                    _set_header(message, self.request_id_header, request_id)
            await send(message)

        # 다음 ASGI app이 보내는 응답 시작 메시지에 request_id를 추가한다.
        await self.app(scope, receive, send_with_request_id)


def _set_header(message: Message, header_name: str, header_value: str) -> None:
    # ASGI 헤더는 bytes tuple 목록이므로 이름을 소문자로 맞춘 뒤 기존 값을 제거하고 새 값을 넣는다.
    normalized = header_name.lower().encode("latin-1")
    headers = [(name, value) for name, value in message.get("headers", []) if name.lower() != normalized]
    headers.append((normalized, header_value.encode("latin-1")))
    message["headers"] = headers
