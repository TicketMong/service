from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    patientId: int
    type: str
    message: str
    status: str
    sourceId: int
    metadata: dict
    createdAt: datetime


class BusinessEvent(BaseModel):
    eventId: str
    eventType: str
    patientId: int
    doctorId: int
    sourceId: int
    status: str
    occurredAt: str
