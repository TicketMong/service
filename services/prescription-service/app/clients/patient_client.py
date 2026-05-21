import httpx
from fastapi import HTTPException, status

from app.auth import UserContext
from app.config import settings
from app.observability import get_current_request_id
from app.schemas import PatientSummary


class PatientServiceUnavailable(Exception):
    pass


def get_patient_summary(patient_id: int, user: UserContext) -> PatientSummary:
    headers = {
        "X-User-Id": user.user_id,
        "X-User-Role": user.role,
    }
    if user.patient_id is not None:
        headers["X-Patient-Id"] = str(user.patient_id)
    if user.doctor_id is not None:
        headers["X-Doctor-Id"] = str(user.doctor_id)
    request_id = get_current_request_id()
    if request_id is not None:
        headers["X-Request-Id"] = request_id

    url = f"{settings.patient_service_url.rstrip('/')}/patients/{patient_id}"
    try:
        response = httpx.get(url, headers=headers, timeout=settings.patient_service_timeout_seconds)
    except httpx.RequestError as exc:
        raise PatientServiceUnavailable("patient-service request failed") from exc

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if response.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor is not allowed to read patient")
    if response.status_code >= 500:
        raise PatientServiceUnavailable("patient-service returned 5xx")
    response.raise_for_status()
    return PatientSummary.model_validate(response.json())
