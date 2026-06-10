from time import perf_counter

from blinker import Namespace
from metrics import MetricLabelEvent, MetricResult

from app.metrics.events import (
    TicketArtifactUploadRecorded,
    TicketEventConsumeRecorded,
    TicketIssuedRecorded,
)
from app.metrics.labels import (
    TicketArtifact,
    TicketSource,
    ticket_event_type_label,
    ticket_topic_label,
)


ticket_signals = Namespace()
ticket_telemetry_recorded = ticket_signals.signal("ticket.telemetry_recorded")


class TicketTelemetryRecorder:
    def __init__(self, sender: str = "ticket-service") -> None:
        """티켓 telemetry signal sender를 준비한다."""
        self._sender = sender

    def start_issue(self, source: TicketSource) -> "TicketIssueAttemptRecorder":
        """티켓 발급 metric 기록기를 시작한다."""
        return TicketIssueAttemptRecorder(source, recorder=self)

    def start_artifact_upload(self, artifact: TicketArtifact) -> "TicketArtifactUploadAttemptRecorder":
        """티켓 artifact 업로드 metric 기록기를 시작한다."""
        return TicketArtifactUploadAttemptRecorder(artifact, recorder=self)

    def start_event_consume(self, *, topic: str | None, event_type: str | None) -> "TicketEventConsumeAttemptRecorder":
        """티켓 이벤트 소비 metric 기록기를 시작한다."""
        return TicketEventConsumeAttemptRecorder(topic=topic, event_type=event_type, recorder=self)

    def record(self, event: MetricLabelEvent) -> None:
        """티켓 telemetry event를 단일 signal로 발행한다."""
        ticket_telemetry_recorded.send(self._sender, event=event)


class TicketIssueAttemptRecorder:
    def __init__(self, source: TicketSource, *, recorder: TicketTelemetryRecorder) -> None:
        """티켓 발급 metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._started_at = perf_counter()
        self._source = source
        self._result = MetricResult.FAILURE

    def mark_success(self) -> None:
        """티켓 발급 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS

    def mark_duplicate(self) -> None:
        """티켓 중복 발급 상태로 metric label을 확정한다."""
        self._result = MetricResult.DUPLICATE

    def record(self) -> None:
        """티켓 발급 metric을 최종 기록한다."""
        self._recorder.record(
            TicketIssuedRecorded(
                source=self._source,
                result=self._result,
                duration_seconds=perf_counter() - self._started_at,
            )
        )


class TicketArtifactUploadAttemptRecorder:
    def __init__(self, artifact: TicketArtifact, *, recorder: TicketTelemetryRecorder) -> None:
        """티켓 artifact 업로드 metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._started_at = perf_counter()
        self._artifact = artifact
        self._result = MetricResult.FAILURE

    def mark_success(self) -> None:
        """티켓 artifact 업로드 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS

    def record(self) -> None:
        """티켓 artifact 업로드 metric을 최종 기록한다."""
        self._recorder.record(
            TicketArtifactUploadRecorded(
                artifact=self._artifact,
                result=self._result,
                duration_seconds=perf_counter() - self._started_at,
            )
        )


class TicketEventConsumeAttemptRecorder:
    def __init__(
        self,
        *,
        topic: str | None,
        event_type: str | None,
        recorder: TicketTelemetryRecorder,
    ) -> None:
        """티켓 이벤트 소비 metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._topic = ticket_topic_label(topic)
        self._event_type = ticket_event_type_label(event_type)
        self._result = MetricResult.FAILURE

    def mark_success(self) -> None:
        """티켓 이벤트 소비 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS

    def mark_duplicate(self) -> None:
        """티켓 이벤트 중복 소비 상태로 metric label을 확정한다."""
        self._result = MetricResult.DUPLICATE

    def record(self) -> None:
        """티켓 이벤트 소비 metric을 최종 기록한다."""
        self._recorder.record(
            TicketEventConsumeRecorded(topic=self._topic, event_type=self._event_type, result=self._result)
        )
