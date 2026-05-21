from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth import UserContext
from app.models import notification_to_doc, processed_event_to_doc
from app.schemas import BusinessEvent


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["patientId"] = doc.pop("patient_id")
    doc["sourceId"] = doc.pop("source_id")
    doc["createdAt"] = doc.pop("created_at")
    return doc


async def list_notifications(
    db: AsyncIOMotorDatabase, user: UserContext
) -> list[dict]:
    query = {}
    if user.role == "PATIENT" and user.patient_id is not None:
        query["patient_id"] = user.patient_id
    elif user.role != "STAFF":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    cursor = db["notifications"].find(query).sort("_id", 1)
    return [_serialize(doc) async for doc in cursor]


async def get_notification(
    db: AsyncIOMotorDatabase, notification_id: str, user: UserContext
) -> dict:
    doc = await db["notifications"].find_one({"_id": ObjectId(notification_id)})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not _can_access(doc, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return _serialize(doc)


async def handle_business_event(db: AsyncIOMotorDatabase, payload: dict) -> dict:
    event = BusinessEvent.model_validate(payload)

    processed = await db["processed_events"].find_one({"event_id": event.eventId})
    if processed:
        doc = await db["notifications"].find_one(
            {"_id": ObjectId(processed["notification_id"])}
        )
        if doc:
            return _serialize(doc)

    metadata = _metadata_for_event(event)
    doc = notification_to_doc(
        patient_id=event.patientId,
        type=event.eventType,
        message=_message_for_event(event),
        status="CREATED",
        source_id=event.sourceId,
        metadata=metadata,
    )
    result = await db["notifications"].insert_one(doc)
    await db["processed_events"].insert_one(
        processed_event_to_doc(event.eventId, str(result.inserted_id))
    )
    doc["_id"] = result.inserted_id
    return _serialize(doc)


def _can_access(doc: dict, user: UserContext) -> bool:
    if user.role == "STAFF":
        return True
    if user.role == "PATIENT":
        return user.patient_id == doc["patient_id"]
    return False


def _message_for_event(event: BusinessEvent) -> str:
    if event.eventType == "appointment-confirmed":
        return f"예약이 확정되었습니다. 예약 ID: {event.sourceId}"
    if event.eventType == "prescription-issued":
        return f"처방이 발행되었습니다. 처방 ID: {event.sourceId}"
    return f"새 알림이 도착했습니다. 이벤트: {event.eventType}"


def _metadata_for_event(event: BusinessEvent) -> dict:
    if event.eventType == "appointment-confirmed":
        return {"doctor_id": event.doctorId, "appointment_id": event.sourceId}
    if event.eventType == "prescription-issued":
        return {"doctor_id": event.doctorId, "prescription_id": event.sourceId}
    return {}
