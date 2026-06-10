from fastapi import Request
from sqlalchemy.orm import Session

from app.metrics.events import AuditEventRecorded
from app.metrics.labels import audit_event_type_label, audit_outcome_label
from app.models import AuditLog, User
from app.metrics.recorder import AuthTelemetryRecorder


auth_metrics = AuthTelemetryRecorder()


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
    """감사 로그를 저장하고 생성 결과 metric을 남긴다."""
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
    auth_metrics.record(
        AuditEventRecorded(event_type=audit_event_type_label(event_type), outcome=audit_outcome_label(outcome))
    )
