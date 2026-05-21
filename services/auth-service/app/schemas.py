from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    displayName: str
    role: str
    patientId: int | None = None
    doctorId: int | None = None
    isActive: bool
    createdAt: datetime


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "Bearer"
    expiresIn: int
    refreshExpiresIn: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class LogoutRequest(BaseModel):
    refreshToken: str | None = None


class DemoAccountResponse(BaseModel):
    email: str
    password: str
    displayName: str
    role: str
    patientId: int | None = None
    doctorId: int | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eventType: str
    outcome: str
    userId: int | None = None
    userEmail: str | None = None
    role: str | None = None
    requestId: str | None = None
    method: str | None = None
    path: str | None = None
    clientIp: str | None = None
    userAgent: str | None = None
    details: str | None = None
    createdAt: datetime
