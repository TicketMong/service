from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    contact: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_doctor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allergies: Mapped[str | None] = mapped_column(String(500), nullable=True)
    medication_warnings: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def birthDate(self) -> str:
        return self.birth_date

    @property
    def primaryDoctorId(self) -> int | None:
        return self.primary_doctor_id

    @property
    def medicationWarnings(self) -> str | None:
        return self.medication_warnings

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
