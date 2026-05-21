from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import UserContext, get_user_context
from app.database import get_db
from app.models import Appointment
from app.schemas import AppointmentCreate, AppointmentResponse
from app.services import appointment_service


router = APIRouter(prefix="/appointments", tags=["appointments"])


# PATIENT가 진료 예약을 REQUESTED 상태로 생성한다.
@router.post("", response_model=AppointmentResponse)
def create_appointment(
    request: AppointmentCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Appointment:
    return appointment_service.create_appointment(db, request, user)


# STAFF, DOCTOR, PATIENT가 자기 권한 범위에 맞는 예약 목록을 조회한다.
@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> list[Appointment]:
    return appointment_service.list_appointments(db, user)


# 예약 관련 PATIENT, 담당 DOCTOR, STAFF가 예약 단건을 조회한다.
@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Appointment:
    return appointment_service.get_appointment(db, appointment_id, user)


# DOCTOR가 REQUESTED 예약을 CONFIRMED로 전환하고 appointment-confirmed 이벤트를 발행한다.
@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Appointment:
    return await appointment_service.confirm_appointment(db, appointment_id, user)


# PATIENT 또는 STAFF가 REQUESTED 예약을 CANCELLED로 전환한다.
@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user_context),
) -> Appointment:
    return appointment_service.cancel_appointment(db, appointment_id, user)
