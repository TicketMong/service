from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import UserContext, get_user_context
from app.database import get_db
from app.models import Prescription
from app.schemas import PrescriptionCreate, PrescriptionResponse
from app.services import prescription_service


router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


# DOCTOR가 처방을 발행하며 patient-service 조회, circuit breaker fallback, prescription-issued 이벤트를 처리한다.
@router.post("", response_model=PrescriptionResponse)
async def issue_prescription(
    request: PrescriptionCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Prescription:
    return await prescription_service.issue_prescription(db, request, user)


# STAFF, DOCTOR, PATIENT가 자기 권한 범위에 맞는 처방 목록을 조회한다.
@router.get("", response_model=list[PrescriptionResponse])
def list_prescriptions(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> list[Prescription]:
    return prescription_service.list_prescriptions(db, user)


# 처방 관련 PATIENT, 발행 DOCTOR, STAFF가 처방 단건을 조회한다.
@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Prescription:
    return prescription_service.get_prescription(db, prescription_id, user)
