from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: str
    patient_id: int | None
    doctor_id: int | None


def get_user_context(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_patient_id: str | None = Header(default=None, alias="X-Patient-Id"),
    x_doctor_id: str | None = Header(default=None, alias="X-Doctor-Id"),
) -> UserContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")

    return UserContext(
        user_id=x_user_id,
        role=x_user_role.upper(),
        patient_id=_parse_optional_int(x_patient_id, "X-Patient-Id"),
        doctor_id=_parse_optional_int(x_doctor_id, "X-Doctor-Id"),
    )


def require_staff(user: UserContext) -> None:
    if user.role != "STAFF":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="STAFF role required")


def can_list_patients(user: UserContext) -> bool:
    return user.role == "STAFF" or (user.role == "DOCTOR" and user.doctor_id is not None)


def can_read_patient(user: UserContext, patient_id: int, primary_doctor_id: int | None) -> bool:
    if user.role == "STAFF":
        return True
    if user.role == "PATIENT":
        return user.patient_id == patient_id
    if user.role == "DOCTOR":
        return user.doctor_id is not None and user.doctor_id == primary_doctor_id
    return False


def can_doctor_update_medical_summary(user: UserContext, primary_doctor_id: int | None) -> bool:
    return user.role == "DOCTOR" and user.doctor_id is not None and user.doctor_id == primary_doctor_id


def _parse_optional_int(value: str | None, header_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{header_name} must be an integer",
        ) from exc
