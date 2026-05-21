from fastapi import APIRouter, Depends

from app.auth import UserContext, get_user_context
from app.database import get_db
from app.services import notification_service


router = APIRouter(prefix="/notifications", tags=["notifications"])


# STAFF는 전체 알림을, PATIENT는 본인 알림 이력만 조회한다.
@router.get("")
async def list_notifications(
    user: UserContext = Depends(get_user_context),
) -> list[dict]:
    db = get_db()
    return await notification_service.list_notifications(db, user)


# STAFF 또는 알림 대상 PATIENT가 알림 단건을 조회한다.
@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    user: UserContext = Depends(get_user_context),
) -> dict:
    db = get_db()
    return await notification_service.get_notification(db, notification_id, user)
