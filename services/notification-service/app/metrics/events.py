from dataclasses import dataclass

from metrics import CounterMetricSpec, HistogramMetricSpec, MetricResult, MetricSpec

from app.metrics.labels import NotificationEventType, NotificationRouteKind, NotificationTopic


@dataclass(frozen=True)
class NotificationEventConsumeRecorded:
    topic: NotificationTopic
    event_type: NotificationEventType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """알림 이벤트 소비 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="notification_events_consumed_total",
                description="Notification event consume attempts by result.",
                label_fields={
                    "topic": "topic",
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
        )


@dataclass(frozen=True)
class NotificationCreatedRecorded:
    event_type: NotificationEventType
    result: MetricResult
    duration_seconds: float

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """알림 생성 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="notifications_created_total",
                description="Notifications created by business event and result.",
                label_fields={
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
            HistogramMetricSpec(
                name="notification_create_duration_seconds",
                description="Notification creation duration in seconds.",
                label_fields={
                    "event_type": "event_type",
                    "result": "result",
                },
                value_field="duration_seconds",
            ),
        )


@dataclass(frozen=True)
class NotificationReadRecorded:
    route_kind: NotificationRouteKind
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """알림 조회 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="notification_reads_total",
                description="Notification reads by route kind.",
                label_fields={
                    "route_kind": "route_kind",
                    "result": "result",
                },
            ),
        )
