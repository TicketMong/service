# Medikong Middleware

`packages/middleware`는 Medikong 서비스의 HTTP 요청 생명주기에서 공통으로 필요한 런타임 정책을 담는다.

## 책임 경계

- `server`: `/healthz`, `/readyz`, `/metrics`, readiness helper, Prometheus runtime collector
- `middleware`: request context, runtime recovery, response header, timeout/body guard 같은 요청 처리 공통 기능
- `observability`: OpenTelemetry, structlog, metrics/logs/traces backend adapter
- `errors`: exception context attach/extract와 domain metadata propagation

Kong Ingress가 담당하는 인증, CORS, TLS, rate limit, WAF성 필터링은 이 패키지에 넣지 않는다.

## v1 구성

- `RequestContextMiddleware`: `X-Request-Id`와 optional `X-Client-Action-Id`를 요청 단위 context에 저장한다.
- `ResponseHeadersMiddleware`: 응답에 `X-Request-Id`를 돌려준다.
- `RuntimeRecoveryMiddleware`: 처리되지 않은 일반 `Exception`을 500 JSON 응답으로 변환한다.

`BaseHTTPMiddleware`는 ContextVar 전파 이슈가 있어 사용하지 않는다. v1 미들웨어는 pure ASGI wrapper로 유지한다.
