from fastapi import APIRouter, Depends, Query

from app.auth import UserContext, get_user_context
from app.database import get_db
from app.schemas import NotificationListResponse
from app.services import notification_service


router = APIRouter(prefix="/notifications", tags=["notifications"])


# 로그인한 사용자 본인의 알림 목록을 조회한다.
@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    user: UserContext = Depends(get_user_context),
) -> NotificationListResponse:
    db = get_db()
    return await notification_service.list_notifications(db, user, limit=limit, cursor=cursor)


# 로그인한 사용자 본인의 알림 단건을 조회한다.
@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    user: UserContext = Depends(get_user_context),
) -> dict:
    db = get_db()
    return await notification_service.get_notification(db, notification_id, user)
