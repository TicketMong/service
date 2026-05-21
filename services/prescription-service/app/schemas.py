from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PrescriptionCreate(BaseModel):
    patientId: int
    doctorId: int
    medicationName: str
    dosage: str
    instructions: str | None = None


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patientId: int
    doctorId: int
    medicationName: str
    dosage: str
    instructions: str | None = None
    issuedAt: datetime
    patientSnapshotAvailable: bool
    warnings: list[str]
    createdAt: datetime


class PatientSummary(BaseModel):
    id: int
    name: str
    contact: str
    primaryDoctorId: int | None = None
    allergies: str | None = None
    medicationWarnings: str | None = None
