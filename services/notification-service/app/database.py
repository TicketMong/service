from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

client: AsyncIOMotorClient = None


def get_db() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_db_name]


async def connect_db() -> None:
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)


def close_db() -> None:
    global client
    if client:
        client.close()
