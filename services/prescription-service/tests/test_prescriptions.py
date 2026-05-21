from collections.abc import Generator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.patient_client import PatientServiceUnavailable
from app.database import Base, get_db
from app.main import app
from app.schemas import PatientSummary
from app.services import prescription_service


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
    prescription_service.patient_lookup_breaker.close()
    yield


def test_doctor_can_issue_prescription_when_patient_lookup_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prescription_service.patient_client, "get_patient_summary", patient_lookup_success)
    published: list[tuple[str, dict]] = []

    async def fake_publish_event(topic: str, payload: dict) -> bool:
        published.append((topic, payload))
        return True

    monkeypatch.setattr(prescription_service.kafka, "publish_event", fake_publish_event)

    response = issue_prescription()

    assert response.status_code == 200
    body = response.json()
    assert body["patientSnapshotAvailable"] is True
    assert body["warnings"] == []
    assert published[0][0] == "prescription-issued"
    assert published[0][1]["eventType"] == "prescription-issued"


def test_patient_lookup_failure_uses_fallback_and_opens_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def unavailable(patient_id: int, user) -> PatientSummary:
        calls["count"] += 1
        raise PatientServiceUnavailable("down")

    async def fake_publish_event(topic: str, payload: dict) -> bool:
        return True

    monkeypatch.setattr(prescription_service.patient_client, "get_patient_summary", unavailable)
    monkeypatch.setattr(prescription_service.kafka, "publish_event", fake_publish_event)

    first_response = issue_prescription()
    second_response = issue_prescription(medication_name="Ibuprofen")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["patientSnapshotAvailable"] is False
    assert second_response.json()["patientSnapshotAvailable"] is False
    assert calls["count"] == 1


def test_patient_not_found_is_not_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_found(patient_id: int, user) -> PatientSummary:
        raise HTTPException(status_code=404, detail="Patient not found")

    monkeypatch.setattr(prescription_service.patient_client, "get_patient_summary", not_found)

    response = issue_prescription()

    assert response.status_code == 404


def test_non_doctor_cannot_issue_prescription() -> None:
    response = client.post(
        "/prescriptions",
        headers=patient_headers(1),
        json={
            "patientId": 1,
            "doctorId": 10,
            "medicationName": "Amoxicillin",
            "dosage": "500mg",
            "instructions": "after meals",
        },
    )

    assert response.status_code == 403


def test_list_prescriptions_is_filtered_by_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prescription_service.patient_client, "get_patient_summary", patient_lookup_success)

    async def fake_publish_event(topic: str, payload: dict) -> bool:
        return True

    monkeypatch.setattr(prescription_service.kafka, "publish_event", fake_publish_event)
    issue_prescription(patient_id=1, doctor_id=10, medication_name="A")
    issue_prescription(patient_id=2, doctor_id=20, medication_name="B")

    patient_response = client.get("/prescriptions", headers=patient_headers(1))
    doctor_response = client.get("/prescriptions", headers=doctor_headers(20))
    staff_response = client.get("/prescriptions", headers=staff_headers())

    assert [item["patientId"] for item in patient_response.json()] == [1]
    assert [item["doctorId"] for item in doctor_response.json()] == [20]
    assert len(staff_response.json()) == 2


def issue_prescription(patient_id: int = 1, doctor_id: int = 10, medication_name: str = "Amoxicillin"):
    return client.post(
        "/prescriptions",
        headers=doctor_headers(doctor_id),
        json={
            "patientId": patient_id,
            "doctorId": doctor_id,
            "medicationName": medication_name,
            "dosage": "500mg",
            "instructions": "after meals",
        },
    )


def patient_lookup_success(patient_id: int, user) -> PatientSummary:
    return PatientSummary(
        id=patient_id,
        name="Patient",
        contact="010-1111-2222",
        primaryDoctorId=user.doctor_id,
        allergies="none",
        medicationWarnings="none",
    )


def patient_headers(patient_id: int) -> dict[str, str]:
    return {"X-User-Id": f"patient-{patient_id}", "X-User-Role": "PATIENT", "X-Patient-Id": str(patient_id)}


def doctor_headers(doctor_id: int) -> dict[str, str]:
    return {"X-User-Id": f"doctor-{doctor_id}", "X-User-Role": "DOCTOR", "X-Doctor-Id": str(doctor_id)}


def staff_headers() -> dict[str, str]:
    return {"X-User-Id": "staff-1", "X-User-Role": "STAFF"}
