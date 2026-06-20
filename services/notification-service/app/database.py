from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from observability import instrument_motor_client

from app.config import settings

client: AsyncIOMotorClient | None = None


def get_db() -> AsyncIOMotorDatabase:
    if client is None:
        raise RuntimeError("MongoDB client is not connected")
    return client[settings.mongodb_db_name]


async def connect_db() -> None:
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    instrument_motor_client(client)
    await ensure_indexes()


async def ensure_indexes() -> None:
    db = get_db()
    await db["notifications"].create_index([("user_id", 1), ("_id", -1)], name="user_id_1__id_-1")
    await db["processed_events"].create_index([("event_id", 1)], unique=True, name="event_id_1")


def close_db() -> None:
    global client
    if client is not None:
        client.close()
        client = None
