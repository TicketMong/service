import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import settings


logger = logging.getLogger("app.kafka")


async def publish_event(topic: str, payload: dict) -> bool:
    if not settings.kafka_bootstrap_servers:
        return False

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda value: json.dumps(value, separators=(",", ":")).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, payload)
        return True
    except Exception:
        logger.exception("failed_to_publish_event topic=%s event_id=%s", topic, payload.get("eventId"))
        raise
    finally:
        await producer.stop()
