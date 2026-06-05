import asyncio
from collections.abc import Awaitable, Callable, Mapping
import json
from typing import Any

from aiokafka import AIOKafkaConsumer
from kafka_utils import kafka_message_attributes, start_consumer_span
from observability import record_exception, set_current_span_attributes


EventHandler = Callable[[dict], Awaitable[None]]
EventHandlers = Mapping[str, EventHandler]
ConsumerFactory = Callable[..., Any]


async def consume_events(
    stop_event: asyncio.Event,
    *,
    bootstrap_servers: str,
    group_id: str,
    service_name: str,
    handlers: EventHandlers,
    consumer_factory: ConsumerFactory = AIOKafkaConsumer,
) -> None:
    if not bootstrap_servers:
        return
    if not handlers:
        raise ValueError("consume_events requires at least one topic handler")

    consumer = consumer_factory(
        *handlers.keys(),
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    await consumer.start()
    try:
        async for message in consumer:
            with start_consumer_span(message):
                set_current_span_attributes({"event.type": str(message.value.get("eventType", "")) or None})
                try:
                    handler = handlers.get(message.topic)
                    if handler is None:
                        raise ValueError(f"No Kafka event handler is bound for topic: {message.topic}")
                    await handler(message.value)
                except Exception as exc:
                    record_exception(exc, service_name=service_name, attributes=kafka_message_attributes(message))
                    raise
            if stop_event.is_set():
                break
    finally:
        await consumer.stop()
