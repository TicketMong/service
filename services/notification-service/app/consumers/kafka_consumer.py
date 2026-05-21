import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.database import get_db
from app.services.notification_service import handle_business_event


async def consume_events(stop_event: asyncio.Event) -> None:
    if not settings.kafka_bootstrap_servers:
        return

    consumer = AIOKafkaConsumer(
        settings.appointment_confirmed_topic,
        settings.prescription_issued_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    await consumer.start()
    try:
        async for message in consumer:
            db = get_db()
            await handle_business_event(db, message.value)
            if stop_event.is_set():
                break
    finally:
        await consumer.stop()
