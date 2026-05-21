from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    UserContext,
    can_doctor_update_medical_summary,
    can_list_patients,
    can_read_patient,
    get_user_context,
    require_staff,
)
from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientResponse, PatientUpdate
from app.services import patient_service


router = APIRouter(prefix="/patients", tags=["patients"])


# STAFF가 신규 환자 프로필과 처방 전 확인용 의료 요약을 등록한다.
@router.post("", response_model=PatientResponse)
def create_patient(
    request: PatientCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Patient:
    require_staff(user)
    return patient_service.create_patient(db, request)


# STAFF는 전체 환자 목록을, DOCTOR는 담당 환자 목록을 조회한다.
@router.get("", response_model=list[PatientResponse])
def list_patients(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> list[Patient]:
    if not can_list_patients(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to list patients")
    return patient_service.list_patients(db, user)


# STAFF, 담당 DOCTOR, 본인 PATIENT만 환자 단건 기록을 조회한다.
@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Patient:
    patient = patient_service.get_patient(db, patient_id)
    if not can_read_patient(user, patient.id, patient.primary_doctor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to read patient")
    return patient


# STAFF는 전체 환자 정보를 수정하고, 담당 DOCTOR는 의료 요약 필드만 수정한다.
@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    request: PatientUpdate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Patient:
    patient = patient_service.get_patient(db, patient_id)
    if user.role == "STAFF":
        return patient_service.update_patient(db, patient.id, request)
    if can_doctor_update_medical_summary(user, patient.primary_doctor_id):
        return patient_service.update_medical_summary(db, patient.id, request)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update patient")
