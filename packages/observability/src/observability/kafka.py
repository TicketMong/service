from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from middleware import get_current_request_id
from opentelemetry import propagate, trace
from opentelemetry.trace import Span, SpanKind


TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
CORRELATION_ID_HEADER = "correlation_id"
KafkaHeaders = list[tuple[str, bytes]]


def build_producer_headers(
    payload: Mapping[str, Any],
    *,
    correlation_id: str | None = None,
) -> KafkaHeaders:
    carrier: dict[str, str] = {}
    propagate.inject(carrier)

    resolved_correlation_id = correlation_id or _string_value(payload.get("correlationId")) or get_current_request_id()
    if resolved_correlation_id:
        carrier[CORRELATION_ID_HEADER] = resolved_correlation_id

    return [(key, value.encode("utf-8")) for key, value in carrier.items() if key in _ALLOWED_HEADERS]


def headers_to_carrier(headers: Sequence[tuple[str | bytes, bytes]] | None) -> dict[str, str]:
    carrier: dict[str, str] = {}
    for key, value in headers or ():
        decoded_key = key.decode("utf-8") if isinstance(key, bytes) else key
        if decoded_key not in _ALLOWED_HEADERS:
            continue
        carrier[decoded_key] = value.decode("utf-8")
    return carrier


@contextmanager
def start_consumer_span(message: Any, *, name: str | None = None) -> Iterator[Span]:
    topic = str(getattr(message, "topic", "unknown"))
    carrier = headers_to_carrier(getattr(message, "headers", None))
    parent_context = propagate.extract(carrier)
    tracer = trace.get_tracer("observability.kafka")
    span_name = name or f"kafka.consume {topic}"

    with tracer.start_as_current_span(
        span_name,
        context=parent_context,
        kind=SpanKind.CONSUMER,
        attributes=kafka_message_attributes(message, carrier=carrier),
    ) as span:
        yield span


def kafka_message_attributes(message: Any, *, carrier: Mapping[str, str] | None = None) -> dict[str, str | int]:
    topic = str(getattr(message, "topic", "unknown"))
    attributes: dict[str, str | int] = {
        "messaging.system": "kafka",
        "messaging.destination.name": topic,
        "messaging.operation": "process",
    }
    partition = getattr(message, "partition", None)
    offset = getattr(message, "offset", None)
    if isinstance(partition, int):
        attributes["messaging.kafka.partition"] = partition
    if isinstance(offset, int):
        attributes["messaging.kafka.message.offset"] = offset

    correlation_id = (carrier or headers_to_carrier(getattr(message, "headers", None))).get(CORRELATION_ID_HEADER)
    if correlation_id:
        attributes[CORRELATION_ID_HEADER] = correlation_id
    return attributes


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_ALLOWED_HEADERS = {TRACEPARENT_HEADER, TRACESTATE_HEADER, CORRELATION_ID_HEADER}
