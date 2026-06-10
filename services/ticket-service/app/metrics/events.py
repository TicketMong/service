from dataclasses import dataclass

from metrics import CounterMetricSpec, HistogramMetricSpec, MetricResult, MetricSpec

from app.metrics.labels import TicketArtifact, TicketEventType, TicketSource, TicketTopic


@dataclass(frozen=True)
class TicketIssuedRecorded:
    source: TicketSource
    result: MetricResult
    duration_seconds: float

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """티켓 발급 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="tickets_issued_total",
                description="Ticket issue attempts by result.",
                label_fields={
                    "source": "source",
                    "result": "result",
                },
            ),
            HistogramMetricSpec(
                name="ticket_issue_duration_seconds",
                description="Ticket issue duration in seconds.",
                label_fields={
                    "source": "source",
                    "result": "result",
                },
                value_field="duration_seconds",
            ),
        )


@dataclass(frozen=True)
class TicketArtifactUploadRecorded:
    artifact: TicketArtifact
    result: MetricResult
    duration_seconds: float

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """티켓 artifact 업로드 event가 기록할 metric spec을 반환한다."""
        return (
            HistogramMetricSpec(
                name="ticket_artifact_upload_duration_seconds",
                description="Ticket artifact upload duration in seconds.",
                label_fields={
                    "artifact": "artifact",
                    "result": "result",
                },
                value_field="duration_seconds",
            ),
        )


@dataclass(frozen=True)
class TicketEventConsumeRecorded:
    topic: TicketTopic
    event_type: TicketEventType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """티켓 이벤트 소비 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="ticket_events_consumed_total",
                description="Ticket event consume attempts by result.",
                label_fields={
                    "topic": "topic",
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
        )


@dataclass(frozen=True)
class TicketEventPublishRecorded:
    event_type: TicketEventType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """티켓 이벤트 발행 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="ticket_events_published_total",
                description="Ticket event publish attempts by result.",
                label_fields={
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
        )
