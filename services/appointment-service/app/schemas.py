from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    patientId: int
    doctorId: int
    appointmentAt: str
    reason: str | None = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patientId: int
    doctorId: int
    appointmentAt: str
    reason: str | None = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class AppointmentEventPayload(BaseModel):
    eventId: str
    eventType: str
    patientId: int
    doctorId: int
    sourceId: int
    status: str
    occurredAt: str
