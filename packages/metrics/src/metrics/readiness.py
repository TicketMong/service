from enum import StrEnum

from prometheus_client import CollectorRegistry, Gauge

from metrics.labels import CommonServiceLabel, assert_safe_metric_label_names


class ServiceReadyLabel(StrEnum):
    # readiness label 정책
    # - 기준: 서비스 인스턴스의 readiness 상태
    # - label: 서비스 식별 label만 허용
    # - 제외: dependency 이름은 P1 service_dependency_up에서 분리
    SERVICE_NAME = CommonServiceLabel.SERVICE_NAME.value
    SERVICE_VERSION = CommonServiceLabel.SERVICE_VERSION.value
    SERVICE_ENVIRONMENT = CommonServiceLabel.SERVICE_ENVIRONMENT.value


SERVICE_READY_LABELS = tuple(label.value for label in ServiceReadyLabel)
assert_safe_metric_label_names(SERVICE_READY_LABELS)


def service_ready(registry: CollectorRegistry) -> Gauge:
    return Gauge(
        "service_ready",
        "Service readiness state. Ready is 1, not ready is 0.",
        SERVICE_READY_LABELS,
        registry=registry,
    )
