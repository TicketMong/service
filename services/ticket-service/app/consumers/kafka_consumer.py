import asyncio
import json
from aiokafka import AIOKafkaConsumer
from observability import kafka_message_attributes, record_exception, set_current_span_attributes, start_consumer_span

from app.config import settings
from app.database import SessionLocal
from app.services.ticket_service import handle_payment_approved


async def consume_events(stop_event: asyncio.Event) -> None:
    if not settings.kafka_bootstrap_servers:
        return

    consumer = AIOKafkaConsumer(
        settings.payment_approved_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )

    await consumer.start()
    try:
        async for message in consumer:
            with start_consumer_span(message):
                set_current_span_attributes({"event.type": str(message.value.get("eventType", "")) or None})
                db = SessionLocal()
                try:
                    await handle_payment_approved(db, message.value)
                except Exception as exc:
                    record_exception(exc, service_name=settings.service_name, attributes=kafka_message_attributes(message))
                    raise
                finally:
                    db.close()
            if stop_event.is_set():
                break
    finally:
        await consumer.stop()
