from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    name: str
    birthDate: str
    gender: str
    contact: str
    primaryDoctorId: int | None = None
    allergies: str | None = None
    medicationWarnings: str | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    birthDate: str | None = None
    gender: str | None = None
    contact: str | None = None
    primaryDoctorId: int | None = None
    allergies: str | None = None
    medicationWarnings: str | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birthDate: str
    gender: str
    contact: str
    primaryDoctorId: int | None = None
    allergies: str | None = None
    medicationWarnings: str | None = None
    createdAt: datetime
    updatedAt: datetime
