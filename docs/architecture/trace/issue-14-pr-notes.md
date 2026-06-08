# Issue #14 PR Notes

## 원래 #14 범위에 해당하는 작업

- FastAPI 서비스의 OpenTelemetry trace 기본 연동 기반을 추가했다.
- 공통 `packages/observability` 패키지를 추가하고, 서비스별 관측성 설정을 연결했다.
- OTLP traces exporter 설정 기준과 exporter 활성화/비활성화 조건을 정리했다.
- trace resource attribute, service name, environment 등 공통 기준을 정리했다.
- request id, trace id, span id를 로그/에러 처리와 연결하는 기반을 정리했다.
- 관측성 책임을 `packages/server`에서 분리하고, 서비스 앱이 명시적으로 compose하도록 정리했다.

## 새롭게 추가된 공유 패키지

- `packages/errors`: 에러 context contract와 metadata 기반 에러 기록 기반
- `packages/middleware`: 런타임 middleware 등록을 명시적으로 구성하는 공유 패키지
- `packages/observability`: FastAPI instrumentation, tracing/logging/error boundary 담당
- `packages/kafka-utils`: Kafka producer 생성자, JSON serializer, header propagation, consumer span helper 담당

## 원래 제외 범위였지만 이번 작업에서 선반영된 Kafka 변경

이슈 #14의 원래 제외 범위에는 Kafka publish/consume trace context 전파가 포함되어 있었지만, 이번 작업 중 Kafka producer 생명주기와 header propagation까지 함께 정리했다.

- `packages/observability`에 있던 Kafka helper를 제거했다.
- Kafka 생성/headers/publish 보조 책임을 `packages/kafka-utils`로 이동했다.
- `traceparent`, `tracestate`, `correlation_id`를 payload가 아니라 Kafka headers로 전파하도록 했다.
- reservation/payment/ticket publish 지점에서 Kafka headers를 사용하도록 변경했다.
- notification/ticket consumer에서 Kafka header 기반 span/context helper를 사용하도록 변경했다.
- 서비스별 `publish_event()` 전역 함수를 제거했다.
- `AIOKafkaProducer`를 publish 호출마다 만들지 않고 FastAPI lifespan에서 `start()`/`stop()` 하도록 변경했다.
- Kafka 설정이 없으면 producer는 `None`이고, 호출부는 기존처럼 publish를 생략한다.
- publish 사용처는 producer를 dependency 또는 함수 인자로 받아 사용하도록 정리했다.

## ticket-service consumer IoC 정리

- `consume_events`가 특정 비즈니스 핸들러를 직접 import하지 않도록 변경했다.
- topic-handler binding은 `main.py` composition root에서 구성한다.
- `consume_events`는 `settings`, `SessionLocal`, business handler를 직접 참조하지 않고, Kafka 설정값과 handlers를 외부에서 주입받는다.
- handler는 payload만 받고, DB session factory와 producer 같은 의존성은 handler 객체가 직접 보유하도록 정리했다.

## 서비스별 영향

- `reservation-service`: producer lifespan 추가, reservation event publish를 주입 producer 기반으로 변경
- `payment-service`: producer lifespan 추가, payment-approved/payment-failed publish를 주입 producer 기반으로 변경
- `ticket-service`: producer + consumer lifespan 결합, ticket-issued publish와 payment-approved consume 구조 정리
- `notification-service`: Kafka consumer trace/context helper import 경로를 `kafka-utils`로 변경

## 검증

- `packages/kafka-utils`: 통과
- `packages/observability`: 통과
- `reservation-service`: 통과
- `concert-service`: 통과
- Docker 기반 `auth-service`, `payment-service`, `ticket-service`, `notification-service`: 통과
- 마지막 `ticket-service` consumer IoC 테스트: 통과

## 커밋

- `1028816 feat: move kafka publisher lifecycle to utility package`
