from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AppointmentEventLog
from app.services import appointment_service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_patient_can_request_appointment_and_event_log_is_stored() -> None:
    response = create_appointment(patient_id=1, doctor_id=10)

    assert response["status"] == "REQUESTED"

    with TestingSessionLocal() as db:
        events = db.query(AppointmentEventLog).all()
        assert len(events) == 1
        assert events[0].event_type == "AppointmentRequested"


def test_patient_cannot_request_for_another_patient() -> None:
    response = client.post(
        "/appointments",
        headers=patient_headers(1),
        json={"patientId": 2, "doctorId": 10, "appointmentAt": "2026-05-20T10:00:00", "reason": "headache"},
    )

    assert response.status_code == 403


def test_doctor_can_confirm_assigned_appointment_and_publish_event(monkeypatch: pytest.MonkeyPatch) -> None:
    appointment = create_appointment(patient_id=1, doctor_id=10)
    published: list[tuple[str, dict]] = []

    async def fake_publish_event(topic: str, payload: dict) -> bool:
        published.append((topic, payload))
        return True

    monkeypatch.setattr(appointment_service.kafka, "publish_event", fake_publish_event)

    response = client.post(f"/appointments/{appointment['id']}/confirm", headers=doctor_headers(10))

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    assert published[0][0] == "appointment-confirmed"
    assert published[0][1]["eventType"] == "appointment-confirmed"

    with TestingSessionLocal() as db:
        event_types = [event.event_type for event in db.query(AppointmentEventLog).order_by(AppointmentEventLog.id)]
        assert event_types == ["AppointmentRequested", "AppointmentConfirmed"]


def test_unassigned_doctor_cannot_confirm_appointment() -> None:
    appointment = create_appointment(patient_id=1, doctor_id=10)

    response = client.post(f"/appointments/{appointment['id']}/confirm", headers=doctor_headers(20))

    assert response.status_code == 403


def test_patient_can_cancel_requested_appointment() -> None:
    appointment = create_appointment(patient_id=1, doctor_id=10)

    response = client.post(f"/appointments/{appointment['id']}/cancel", headers=patient_headers(1))

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_list_appointments_is_filtered_by_role() -> None:
    create_appointment(patient_id=1, doctor_id=10)
    create_appointment(patient_id=2, doctor_id=20)

    patient_response = client.get("/appointments", headers=patient_headers(1))
    doctor_response = client.get("/appointments", headers=doctor_headers(20))
    staff_response = client.get("/appointments", headers=staff_headers())

    assert [item["patientId"] for item in patient_response.json()] == [1]
    assert [item["doctorId"] for item in doctor_response.json()] == [20]
    assert len(staff_response.json()) == 2


def create_appointment(patient_id: int, doctor_id: int) -> dict:
    response = client.post(
        "/appointments",
        headers=patient_headers(patient_id),
        json={
            "patientId": patient_id,
            "doctorId": doctor_id,
            "appointmentAt": "2026-05-20T10:00:00",
            "reason": "headache",
        },
    )
    assert response.status_code == 200
    return response.json()


def patient_headers(patient_id: int) -> dict[str, str]:
    return {"X-User-Id": f"patient-{patient_id}", "X-User-Role": "PATIENT", "X-Patient-Id": str(patient_id)}


def doctor_headers(doctor_id: int) -> dict[str, str]:
    return {"X-User-Id": f"doctor-{doctor_id}", "X-User-Role": "DOCTOR", "X-Doctor-Id": str(doctor_id)}


def staff_headers() -> dict[str, str]:
    return {"X-User-Id": "staff-1", "X-User-Role": "STAFF"}
