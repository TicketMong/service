from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TicketIssueRequest(BaseModel):
    reservationId: str
    userId: int
    concertId: str
    seatId: str


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reservationId: str
    userId: int
    concertId: str
    seatId: str
    status: str
    qrUrl: str | None
    pdfUrl: str | None
    issuedAt: datetime


class PaymentApprovedEvent(BaseModel):
    eventId: str
    eventType: str
    userId: int
    sourceId: str
    reservationId: str
    concertId: str
    seatId: str
    occurredAt: str
    producer: str
    correlationId: str | None = None
