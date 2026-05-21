import pytest
from mongomock_motor import AsyncMongoMockClient
from fastapi.testclient import TestClient

import app.database as database
from app.main import app
from app.services.notification_service import handle_business_event


def override_get_db():
    return database.client["notification_db"]


app.dependency_overrides[database.get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_mock_db():
    database.client = AsyncMongoMockClient()
    yield
    database.client = None


client = TestClient(app, raise_server_exceptions=True)


def test_appointment_confirmed_event_creates_notification() -> None:
    import asyncio
    db = database.client["notification_db"]
    notification = asyncio.get_event_loop().run_until_complete(
        handle_business_event(db, appointment_event(patient_id=1, source_id=100))
    )

    assert notification["patientId"] == 1
    assert notification["type"] == "appointment-confirmed"
    assert "예약이 확정되었습니다" in notification["message"]


def test_prescription_issued_event_creates_notification() -> None:
    import asyncio
    db = database.client["notification_db"]
    notification = asyncio.get_event_loop().run_until_complete(
        handle_business_event(db, prescription_event(patient_id=1, source_id=200))
    )

    assert notification["patientId"] == 1
    assert notification["type"] == "prescription-issued"
    assert "처방이 발행되었습니다" in notification["message"]


def test_duplicate_event_id_returns_existing_notification() -> None:
    import asyncio
    db = database.client["notification_db"]
    loop = asyncio.get_event_loop()
    first = loop.run_until_complete(handle_business_event(db, appointment_event(patient_id=1, source_id=100)))
    second = loop.run_until_complete(handle_business_event(db, appointment_event(patient_id=1, source_id=100)))
    count = loop.run_until_complete(db["notifications"].count_documents({}))

    assert second["id"] == first["id"]
    assert count == 1


def test_patient_can_list_only_own_notifications() -> None:
    seed_notifications()
    response = client.get("/notifications", headers=patient_headers(1))

    assert response.status_code == 200
    assert all(item["patientId"] == 1 for item in response.json())


def test_staff_can_list_all_notifications() -> None:
    seed_notifications()
    response = client.get("/notifications", headers=staff_headers())

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_patient_cannot_read_other_patient_notification() -> None:
    import asyncio
    db = database.client["notification_db"]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_business_event(db, appointment_event(patient_id=2, source_id=100)))
    notifications = loop.run_until_complete(db["notifications"].find().to_list(None))
    other_id = str(notifications[0]["_id"])

    response = client.get(f"/notifications/{other_id}", headers=patient_headers(1))
    assert response.status_code == 403


def seed_notifications() -> None:
    import asyncio
    db = database.client["notification_db"]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handle_business_event(db, appointment_event(patient_id=1, source_id=100)))
    loop.run_until_complete(handle_business_event(db, prescription_event(patient_id=2, source_id=200)))


def appointment_event(patient_id: int, source_id: int) -> dict:
    return {
        "eventId": "event-1",
        "eventType": "appointment-confirmed",
        "patientId": patient_id,
        "doctorId": 10,
        "sourceId": source_id,
        "status": "CONFIRMED",
        "occurredAt": "2026-05-13T10:00:00Z",
    }


def prescription_event(patient_id: int, source_id: int) -> dict:
    return {
        "eventId": "event-2",
        "eventType": "prescription-issued",
        "patientId": patient_id,
        "doctorId": 10,
        "sourceId": source_id,
        "status": "ISSUED",
        "occurredAt": "2026-05-13T10:00:00Z",
    }


def patient_headers(patient_id: int) -> dict[str, str]:
    return {"X-User-Id": f"patient-{patient_id}", "X-User-Role": "PATIENT", "X-Patient-Id": str(patient_id)}


def staff_headers() -> dict[str, str]:
    return {"X-User-Id": "staff-1", "X-User-Role": "STAFF"}
