import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.config import settings
from app.consumers.kafka_consumer import consume_events
from app.database import connect_db, close_db
from app.observability import setup_request_logging
from app.routers import notifications


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await connect_db()
    app.state.consumer_stop_event = asyncio.Event()
    app.state.consumer_task = asyncio.create_task(
        consume_events(app.state.consumer_stop_event)
    )
    try:
        yield
    finally:
        app.state.consumer_stop_event.set()
        app.state.consumer_task.cancel()
        close_db()


app = FastAPI(title=settings.service_name, lifespan=lifespan)
setup_request_logging(app, settings.service_name)
app.include_router(notifications.router)


# Kubernetes probe와 로컬 확인에 사용하는 공개 헬스체크 API다.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
