from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    medication_name: Mapped[str] = mapped_column(String(150), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    patient_snapshot_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def patientId(self) -> int:
        return self.patient_id

    @property
    def doctorId(self) -> int:
        return self.doctor_id

    @property
    def medicationName(self) -> str:
        return self.medication_name

    @property
    def issuedAt(self) -> datetime:
        return self.issued_at

    @property
    def patientSnapshotAvailable(self) -> bool:
        return self.patient_snapshot_available

    @property
    def warnings(self) -> list[str]:
        return self.warnings_json

    @property
    def createdAt(self) -> datetime:
        return self.created_at
