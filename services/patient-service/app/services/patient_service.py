from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import UserContext
from app.models import Patient
from app.schemas import PatientCreate, PatientUpdate


def create_patient(db: Session, request: PatientCreate) -> Patient:
    patient = Patient(
        name=request.name,
        birth_date=request.birthDate,
        gender=request.gender,
        contact=request.contact,
        primary_doctor_id=request.primaryDoctorId,
        allergies=request.allergies,
        medication_warnings=request.medicationWarnings,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def list_patients(db: Session, user: UserContext) -> list[Patient]:
    query = db.query(Patient)
    if user.role == "DOCTOR":
        query = query.filter(Patient.primary_doctor_id == user.doctor_id)
    return query.order_by(Patient.id).all()


def get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def update_patient(db: Session, patient_id: int, request: PatientUpdate) -> Patient:
    patient = get_patient(db, patient_id)
    updates = request.model_dump(exclude_unset=True)
    return apply_patient_updates(db, patient, updates)


def update_medical_summary(db: Session, patient_id: int, request: PatientUpdate) -> Patient:
    patient = get_patient(db, patient_id)
    updates = request.model_dump(exclude_unset=True)
    allowed_fields = {"allergies", "medicationWarnings"}
    blocked_fields = set(updates) - allowed_fields
    if blocked_fields:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DOCTOR can update only allergies and medicationWarnings",
        )
    return apply_patient_updates(db, patient, updates)


def apply_patient_updates(db: Session, patient: Patient, updates: dict) -> Patient:
    field_map = {
        "birthDate": "birth_date",
        "primaryDoctorId": "primary_doctor_id",
        "medicationWarnings": "medication_warnings",
    }

    for key, value in updates.items():
        setattr(patient, field_map.get(key, key), value)

    db.commit()
    db.refresh(patient)
    return patient
