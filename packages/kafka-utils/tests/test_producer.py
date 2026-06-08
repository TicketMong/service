from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kafka_utils import build_producer_headers, create_kafka_producer
from kafka_utils import producer as producer_module


def test_create_kafka_producer_returns_none_without_kafka_config() -> None:
    producer = create_kafka_producer("")

    assert producer is None


def test_create_kafka_producer_configures_aiokafka_producer() -> None:
    producers: list[FakeProducer] = []

    def factory(**kwargs: object) -> FakeProducer:
        producer = FakeProducer(kwargs)
        producers.append(producer)
        return producer

    producer = create_kafka_producer(
        "kafka:9092",
        client_id="reservation-service",
        producer_factory=factory,
    )

    assert producer is producers[0]
    assert producers[0].kwargs["bootstrap_servers"] == "kafka:9092"
    assert producers[0].kwargs["client_id"] == "reservation-service"
    assert producers[0].kwargs["value_serializer"]({"eventId": "evt-1", "count": 1}) == b'{"eventId":"evt-1","count":1}'


def test_create_kafka_producer_omits_empty_client_id() -> None:
    producer = create_kafka_producer(
        "kafka:9092",
        producer_factory=lambda **kwargs: FakeProducer(kwargs),
    )

    assert producer is not None
    assert "client_id" not in producer.kwargs


def test_build_producer_headers_uses_trace_and_correlation_headers(monkeypatch) -> None:
    def fake_inject(carrier: dict[str, str]) -> None:
        carrier["traceparent"] = "00-trace-span-01"
        carrier["tracestate"] = "vendor=value"

    monkeypatch.setattr(producer_module.propagate, "inject", fake_inject)

    headers = dict(build_producer_headers(correlation_id="req-1"))

    assert headers == {
        "traceparent": b"00-trace-span-01",
        "tracestate": b"vendor=value",
        "correlation_id": b"req-1",
    }


class FakeProducer:
    def __init__(self, kwargs: Mapping[str, Any]) -> None:
        self.kwargs = dict(kwargs)
