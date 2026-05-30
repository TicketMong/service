from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    reservationId: str
    concertId: str = "unknown"
    seatId: str | None = None
    amount: int = Field(ge=0)
    method: str
    simulation: str = "approve"


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reservationId: str
    concertId: str
    amount: int
    method: str
    status: str
    approvedAt: datetime | None = None
    createdAt: datetime


class SettlementBasisResponse(BaseModel):
    concertId: str
    grossAmount: int
    refundAmount: int
    netAmount: int
    ticketCount: int
    platformFeeAmount: int
    providerSettlementAmount: int
    calculatedAt: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, str]
    timestamp: datetime
