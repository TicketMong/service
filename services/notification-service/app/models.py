from datetime import datetime, timezone


def notification_to_doc(
    patient_id: int,
    type: str,
    message: str,
    status: str,
    source_id: int,
    metadata: dict | None = None,
) -> dict:
    return {
        "patient_id": patient_id,
        "type": type,
        "message": message,
        "status": status,
        "source_id": source_id,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc),
    }


def processed_event_to_doc(event_id: str, notification_id: str) -> dict:
    return {
        "event_id": event_id,
        "notification_id": notification_id,
        "created_at": datetime.now(timezone.utc),
    }
