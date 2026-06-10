from fastapi import HTTPException, status
from blinker import Namespace
from metrics import MetricLabelEvent, MetricResult

from app.metrics.events import AuthAttemptRecorded
from app.metrics.labels import (
    AuthAction,
    AuthErrorCode,
)


auth_signals = Namespace()
auth_telemetry_recorded = auth_signals.signal("auth.telemetry_recorded")


class AuthTelemetryRecorder:
    def __init__(self, sender: str = "auth-service") -> None:
        """인증 telemetry signal sender를 준비한다."""
        self._sender = sender

    def start_attempt(self, action: AuthAction) -> "AuthAttemptRecorder":
        """인증 시도 metric 기록기를 시작한다."""
        return AuthAttemptRecorder(action, recorder=self)

    def record(self, event: MetricLabelEvent) -> None:
        """인증 telemetry event를 단일 signal로 발행한다."""
        auth_telemetry_recorded.send(self._sender, event=event)


class AuthAttemptRecorder:
    def __init__(self, action: AuthAction, *, recorder: AuthTelemetryRecorder) -> None:
        """인증 시도 metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._action = action
        self._result = MetricResult.FAILURE
        self._error_code = AuthErrorCode.INTERNAL_ERROR

    def mark_success(self) -> None:
        """인증 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS
        self._error_code = AuthErrorCode.NONE

    def mark_rejection(self, error_code: AuthErrorCode) -> None:
        """인증 거절 상태로 metric label을 확정한다."""
        self._result = MetricResult.REJECTION
        self._error_code = error_code

    def mark_http_exception(self, exc: HTTPException) -> None:
        """HTTP 예외를 인증 metric label로 변환한다."""
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            self.mark_rejection(AuthErrorCode.FORBIDDEN)
            return
        self.mark_rejection(AuthErrorCode.INVALID_TOKEN)

    def has_default_failure(self) -> bool:
        """아직 구체적인 인증 실패 코드가 정해지지 않았는지 확인한다."""
        return self._error_code is AuthErrorCode.INTERNAL_ERROR

    def record(self) -> None:
        """인증 시도 metric을 최종 기록한다."""
        self._recorder.record(AuthAttemptRecorded(action=self._action, result=self._result, error_code=self._error_code))
