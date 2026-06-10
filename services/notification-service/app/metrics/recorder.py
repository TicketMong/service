from time import perf_counter

from blinker import Namespace
from metrics import MetricLabelEvent, MetricResult

from app.metrics.events import NotificationCreatedRecorded, NotificationEventConsumeRecorded
from app.metrics.labels import (
    notification_event_type_label,
    notification_topic_label,
)


notification_signals = Namespace()
notification_telemetry_recorded = notification_signals.signal("notification.telemetry_recorded")


class NotificationTelemetryRecorder:
    def __init__(self, sender: str = "notification-service") -> None:
        """알림 telemetry signal sender를 준비한다."""
        self._sender = sender

    def start_event(self, *, topic: str | None, event_type: str | None) -> "NotificationEventAttemptRecorder":
        """알림 이벤트 처리 metric 기록기를 시작한다."""
        return NotificationEventAttemptRecorder(topic=topic, event_type=event_type, recorder=self)

    def record(self, event: MetricLabelEvent) -> None:
        """알림 telemetry event를 단일 signal로 발행한다."""
        notification_telemetry_recorded.send(self._sender, event=event)


class NotificationEventAttemptRecorder:
    def __init__(
        self,
        *,
        topic: str | None,
        event_type: str | None,
        recorder: NotificationTelemetryRecorder,
    ) -> None:
        """알림 이벤트 처리 metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._started_at = perf_counter()
        self._topic = notification_topic_label(topic)
        self._event_type = notification_event_type_label(event_type)
        self._result = MetricResult.FAILURE

    def mark_success(self) -> None:
        """알림 생성 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS

    def mark_duplicate(self) -> None:
        """알림 중복 이벤트 상태로 metric label을 확정한다."""
        self._result = MetricResult.DUPLICATE

    def record(self) -> None:
        """알림 이벤트 소비와 생성 metric을 최종 기록한다."""
        self._recorder.record(
            NotificationEventConsumeRecorded(topic=self._topic, event_type=self._event_type, result=self._result)
        )
        self._recorder.record(
            NotificationCreatedRecorded(
                event_type=self._event_type,
                result=self._result,
                duration_seconds=perf_counter() - self._started_at,
            )
        )
