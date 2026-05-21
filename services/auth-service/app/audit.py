from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    request: Request,
    *,
    event_type: str,
    outcome: str,
    user: User | None = None,
    user_email: str | None = None,
    details: str | None = None,
) -> None:
    db.add(
        AuditLog(
            event_type=event_type,
            outcome=outcome,
            user_id=user.id if user else None,
            user_email=user.email if user else user_email,
            role=user.role if user else None,
            request_id=request.headers.get("X-Request-Id"),
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            details=details,
        )
    )
    db.commit()
