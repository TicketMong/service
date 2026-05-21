from datetime import UTC, datetime
from uuid import uuid4

import pybreaker
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import kafka
from app.auth import UserContext
from app.clients import patient_client
from app.clients.patient_client import PatientServiceUnavailable
from app.config import settings
from app.models import Prescription
from app.schemas import PrescriptionCreate


patient_lookup_breaker = pybreaker.CircuitBreaker(fail_max=1, reset_timeout=5, exclude=[HTTPException])


async def issue_prescription(db: Session, request: PrescriptionCreate, user: UserContext) -> Prescription:
    if user.role != "DOCTOR" or user.doctor_id != request.doctorId:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="DOCTOR role required")

    patient_snapshot_available = True
    warnings: list[str] = []
    try:
        patient_lookup_breaker.call(patient_client.get_patient_summary, request.patientId, user)
    except (PatientServiceUnavailable, pybreaker.CircuitBreakerError):
        patient_snapshot_available = False
        warnings.append("환자 의료요약 조회에 실패하여 부분 처방 기록으로 저장되었습니다.")

    prescription = Prescription(
        patient_id=request.patientId,
        doctor_id=request.doctorId,
        medication_name=request.medicationName,
        dosage=request.dosage,
        instructions=request.instructions,
        issued_at=datetime.now(UTC),
        patient_snapshot_available=patient_snapshot_available,
        warnings_json=warnings,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    await kafka.publish_event(settings.prescription_issued_topic, _business_event(prescription))
    return prescription


def list_prescriptions(db: Session, user: UserContext) -> list[Prescription]:
    query = db.query(Prescription).order_by(Prescription.id)
    if user.role == "STAFF":
        return query.all()
    if user.role == "DOCTOR" and user.doctor_id is not None:
        return query.filter(Prescription.doctor_id == user.doctor_id).all()
    if user.role == "PATIENT" and user.patient_id is not None:
        return query.filter(Prescription.patient_id == user.patient_id).all()
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to list prescriptions")


def get_prescription(db: Session, prescription_id: int, user: UserContext) -> Prescription:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    if not _can_access_prescription(prescription, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to read prescription")
    return prescription


def _can_access_prescription(prescription: Prescription, user: UserContext) -> bool:
    if user.role == "STAFF":
        return True
    if user.role == "DOCTOR":
        return user.doctor_id == prescription.doctor_id
    if user.role == "PATIENT":
        return user.patient_id == prescription.patient_id
    return False


def _business_event(prescription: Prescription) -> dict:
    return {
        "eventId": str(uuid4()),
        "eventType": "prescription-issued",
        "patientId": prescription.patient_id,
        "doctorId": prescription.doctor_id,
        "sourceId": prescription.id,
        "status": "ISSUED",
        "occurredAt": datetime.now(UTC).isoformat(),
    }
