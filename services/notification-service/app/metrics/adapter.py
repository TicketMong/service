from metrics import (
    CommonServiceLabel,
    MetricHandleMap,
    MetricLabelEvent,
    connect_metrics_for_events,
    create_metrics_for_events,
)
from prometheus_client import CollectorRegistry

from app.metrics.events import (
    NotificationCreatedRecorded,
    NotificationEventConsumeRecorded,
    NotificationReadRecorded,
)
from app.metrics.recorder import notification_telemetry_recorded


NOTIFICATION_SERVICE_LABELS = (
    CommonServiceLabel.SERVICE_NAME.value,
    CommonServiceLabel.SERVICE_ENVIRONMENT.value,
)
NOTIFICATION_METRIC_EVENTS: tuple[type[MetricLabelEvent], ...] = (
    NotificationEventConsumeRecorded,
    NotificationCreatedRecorded,
    NotificationReadRecorded,
)


class NotificationMetricsAdapter:
    def __init__(self, *, registry: CollectorRegistry, service_name: str, service_environment: str) -> None:
        """알림 telemetry event를 기록할 Prometheus metric 핸들을 준비한다."""
        _require_service_label("service_name", service_name)
        _require_service_label("service_environment", service_environment)
        self._service_labels = {"service_name": service_name, "service_environment": service_environment}
        self._metrics: MetricHandleMap = create_metrics_for_events(
            registry,
            service_label_names=NOTIFICATION_SERVICE_LABELS,
            event_types=NOTIFICATION_METRIC_EVENTS,
        )

    def connect(self) -> None:
        """알림 telemetry signal과 Prometheus 기록 함수를 연결한다."""
        connect_metrics_for_events(
            notification_telemetry_recorded,
            self._metrics,
            self._service_labels,
            NOTIFICATION_METRIC_EVENTS,
        )


def configure_notification_metrics(
    registry: CollectorRegistry,
    *,
    service_name: str,
    service_environment: str,
) -> NotificationMetricsAdapter:
    """notification-service 전용 Prometheus metric adapter를 등록한다."""
    adapter = NotificationMetricsAdapter(
        registry=registry,
        service_name=service_name,
        service_environment=service_environment,
    )
    adapter.connect()
    return adapter


def _require_service_label(name: str, value: str | None) -> None:
    """metric에 필요한 서비스 label 값이 비어 있지 않은지 확인한다."""
    if value is None or value == "":
        raise ValueError(f"{name} is required")
