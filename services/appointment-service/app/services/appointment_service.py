from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import kafka
from app.auth import UserContext
from app.config import settings
from app.models import Appointment, AppointmentEventLog
from app.schemas import AppointmentCreate


REQUESTED = "REQUESTED"
CONFIRMED = "CONFIRMED"
CANCELLED = "CANCELLED"


def create_appointment(db: Session, request: AppointmentCreate, user: UserContext) -> Appointment:
    if user.role != "PATIENT" or user.patient_id != request.patientId:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="PATIENT can request only own appointment")

    appointment = Appointment(
        patient_id=request.patientId,
        doctor_id=request.doctorId,
        appointment_at=request.appointmentAt,
        reason=request.reason,
        status=REQUESTED,
    )
    db.add(appointment)
    db.flush()
    _record_event(db, appointment, "AppointmentRequested")
    db.commit()
    db.refresh(appointment)
    return appointment


def list_appointments(db: Session, user: UserContext) -> list[Appointment]:
    query = db.query(Appointment).order_by(Appointment.id)
    if user.role == "STAFF":
        return query.all()
    if user.role == "DOCTOR" and user.doctor_id is not None:
        return query.filter(Appointment.doctor_id == user.doctor_id).all()
    if user.role == "PATIENT" and user.patient_id is not None:
        return query.filter(Appointment.patient_id == user.patient_id).all()
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to list appointments")


def get_appointment(db: Session, appointment_id: int, user: UserContext) -> Appointment:
    appointment = _get_appointment(db, appointment_id)
    if not _can_access_appointment(appointment, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to read appointment")
    return appointment


async def confirm_appointment(db: Session, appointment_id: int, user: UserContext) -> Appointment:
    appointment = _get_appointment(db, appointment_id)
    if user.role != "DOCTOR" or user.doctor_id != appointment.doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assigned DOCTOR role required")
    if appointment.status != REQUESTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only REQUESTED appointment can be confirmed")

    appointment.status = CONFIRMED
    _record_event(db, appointment, "AppointmentConfirmed")
    db.commit()
    db.refresh(appointment)
    await kafka.publish_event(settings.appointment_confirmed_topic, _business_event(appointment))
    return appointment


def cancel_appointment(db: Session, appointment_id: int, user: UserContext) -> Appointment:
    appointment = _get_appointment(db, appointment_id)
    allowed = user.role == "STAFF" or (user.role == "PATIENT" and user.patient_id == appointment.patient_id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to cancel appointment")
    if appointment.status != REQUESTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only REQUESTED appointment can be cancelled")

    appointment.status = CANCELLED
    _record_event(db, appointment, "AppointmentCancelled")
    db.commit()
    db.refresh(appointment)
    return appointment


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def _can_access_appointment(appointment: Appointment, user: UserContext) -> bool:
    if user.role == "STAFF":
        return True
    if user.role == "DOCTOR":
        return user.doctor_id == appointment.doctor_id
    if user.role == "PATIENT":
        return user.patient_id == appointment.patient_id
    return False


def _record_event(db: Session, appointment: Appointment, event_type: str) -> None:
    db.add(
        AppointmentEventLog(
            appointment_id=appointment.id,
            event_type=event_type,
            payload={
                "appointmentId": appointment.id,
                "patientId": appointment.patient_id,
                "doctorId": appointment.doctor_id,
                "status": appointment.status,
            },
        )
    )


def _business_event(appointment: Appointment) -> dict:
    return {
        "eventId": str(uuid4()),
        "eventType": "appointment-confirmed",
        "patientId": appointment.patient_id,
        "doctorId": appointment.doctor_id,
        "sourceId": appointment.id,
        "status": appointment.status,
        "occurredAt": datetime.now(UTC).isoformat(),
    }
