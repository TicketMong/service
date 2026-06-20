from datetime import datetime
from typing import Any

from contracts.events import BusinessEvent
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    userId: str
    type: str
    message: str
    status: str
    sourceId: str
    metadata: dict[str, Any]
    createdAt: datetime


class NotificationPageInfo(BaseModel):
    nextCursor: str | None = None
    hasMore: bool = False
    limit: int


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    page: NotificationPageInfo


__all__ = ["BusinessEvent", "NotificationListResponse", "NotificationPageInfo", "NotificationResponse"]
