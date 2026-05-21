from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


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


def test_staff_can_create_and_read_patient() -> None:
    response = client.post(
        "/patients",
        headers=staff_headers(),
        json={
            "name": "Kim Patient",
            "birthDate": "1990-01-01",
            "gender": "F",
            "contact": "010-1111-2222",
            "primaryDoctorId": 10,
            "allergies": "penicillin",
            "medicationWarnings": "check blood pressure",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["name"] == "Kim Patient"
    assert body["primaryDoctorId"] == 10

    read_response = client.get("/patients/1", headers=staff_headers())
    assert read_response.status_code == 200
    assert read_response.json()["allergies"] == "penicillin"

    list_response = client.get("/patients", headers=staff_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_patient_can_read_only_own_record() -> None:
    create_patient("Patient A")
    create_patient("Patient B")

    own_response = client.get("/patients/1", headers=patient_headers(1))
    other_response = client.get("/patients/2", headers=patient_headers(1))

    assert own_response.status_code == 200
    assert other_response.status_code == 403


def test_doctor_can_read_assigned_patient() -> None:
    create_patient("Assigned Patient", primary_doctor_id=10)
    create_patient("Other Patient", primary_doctor_id=20)

    assigned_response = client.get("/patients/1", headers=doctor_headers(10))
    other_response = client.get("/patients/2", headers=doctor_headers(10))

    assert assigned_response.status_code == 200
    assert other_response.status_code == 403


def test_doctor_can_list_only_assigned_patients() -> None:
    create_patient("Assigned A", primary_doctor_id=10)
    create_patient("Other Doctor Patient", primary_doctor_id=20)
    create_patient("Assigned B", primary_doctor_id=10)

    response = client.get("/patients", headers=doctor_headers(10))

    assert response.status_code == 200
    body = response.json()
    assert [patient["name"] for patient in body] == ["Assigned A", "Assigned B"]


def test_patient_cannot_list_patients() -> None:
    create_patient("Patient A")

    response = client.get("/patients", headers=patient_headers(1))

    assert response.status_code == 403


def test_doctor_can_update_assigned_patient_medical_summary_only() -> None:
    create_patient("Assigned Patient", primary_doctor_id=10)

    response = client.patch(
        "/patients/1",
        headers=doctor_headers(10),
        json={"allergies": "aspirin", "medicationWarnings": "monitor blood sugar"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allergies"] == "aspirin"
    assert body["medicationWarnings"] == "monitor blood sugar"


def test_doctor_cannot_update_demographic_fields() -> None:
    create_patient("Assigned Patient", primary_doctor_id=10)

    response = client.patch(
        "/patients/1",
        headers=doctor_headers(10),
        json={"contact": "010-9999-9999", "allergies": "aspirin"},
    )

    assert response.status_code == 403


def test_doctor_cannot_update_unassigned_patient() -> None:
    create_patient("Other Doctor Patient", primary_doctor_id=20)

    response = client.patch(
        "/patients/1",
        headers=doctor_headers(10),
        json={"allergies": "aspirin"},
    )

    assert response.status_code == 403


def test_non_staff_cannot_create_or_update_patient() -> None:
    create_response = client.post(
        "/patients",
        headers=patient_headers(1),
        json={
            "name": "Blocked",
            "birthDate": "1990-01-01",
            "gender": "F",
            "contact": "010-0000-0000",
        },
    )

    assert create_response.status_code == 403

    create_patient("Updatable")
    update_response = client.patch("/patients/1", headers=patient_headers(1), json={"contact": "010-9999-9999"})
    assert update_response.status_code == 403


def test_missing_user_context_returns_401() -> None:
    response = client.get("/patients/1")

    assert response.status_code == 401


def create_patient(name: str, primary_doctor_id: int = 10) -> dict:
    response = client.post(
        "/patients",
        headers=staff_headers(),
        json={
            "name": name,
            "birthDate": "1990-01-01",
            "gender": "F",
            "contact": "010-1111-2222",
            "primaryDoctorId": primary_doctor_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def staff_headers() -> dict[str, str]:
    return {"X-User-Id": "staff-1", "X-User-Role": "STAFF"}


def patient_headers(patient_id: int) -> dict[str, str]:
    return {"X-User-Id": f"patient-{patient_id}", "X-User-Role": "PATIENT", "X-Patient-Id": str(patient_id)}


def doctor_headers(doctor_id: int) -> dict[str, str]:
    return {"X-User-Id": f"doctor-{doctor_id}", "X-User-Role": "DOCTOR", "X-Doctor-Id": str(doctor_id)}
