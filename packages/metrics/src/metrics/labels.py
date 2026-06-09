from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


DEFAULT_SERVICE_VERSION = "unknown"
DEFAULT_SERVICE_ENVIRONMENT = "local"

# 고카디널리티 label 금지 목록
# - 목적: Prometheus 시계열 폭증 방지
# - metric: 서비스/route/status 같은 낮은 cardinality 차원만 기록
# - log/trace: request_id, trace_id, domain object ID 같은 요청별 값 기록
FORBIDDEN_HIGH_CARDINALITY_LABELS = frozenset(
    {
        "request_id",
        "trace_id",
        "span_id",
        "correlation_id",
        "user_id",
        "order_id",
        "payment_id",
        "reservation_id",
        "ticket_id",
        "path",
        "raw_path",
    }
)


class CommonServiceLabel(StrEnum):
    SERVICE_NAME = "service_name"
    SERVICE_VERSION = "service_version"
    SERVICE_ENVIRONMENT = "service_environment"


class MetricResult(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    REJECTION = "rejection"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"


class FailureKind(StrEnum):
    NONE = "none"
    BUSINESS_REJECTION = "business_rejection"
    INTERNAL_ERROR = "internal_error"
    DEPENDENCY_ERROR = "dependency_error"


class Expected(StrEnum):
    TRUE = "true"
    FALSE = "false"


COMMON_SERVICE_LABELS = tuple(label.value for label in CommonServiceLabel)


@dataclass(frozen=True)
class ServiceIdentity:
    # 공통 서비스 식별 label
    # - 필수: service_name
    # - 선택: service_version, service_environment
    # - 기본값: label 누락으로 PromQL/dashboard 쿼리가 갈라지는 상황 방지
    service_name: str
    service_version: str = DEFAULT_SERVICE_VERSION
    service_environment: str = DEFAULT_SERVICE_ENVIRONMENT

    @classmethod
    def from_optional_values(
        cls,
        *,
        service_name: str,
        service_version: str | None,
        service_environment: str | None,
    ) -> "ServiceIdentity":
        return cls(
            service_name=service_name,
            service_version=_default_if_blank(service_version, DEFAULT_SERVICE_VERSION),
            service_environment=_default_if_blank(service_environment, DEFAULT_SERVICE_ENVIRONMENT),
        )

    def service_labels(self) -> dict[str, str]:
        return {
            CommonServiceLabel.SERVICE_NAME.value: self.service_name,
            CommonServiceLabel.SERVICE_VERSION.value: self.service_version,
            CommonServiceLabel.SERVICE_ENVIRONMENT.value: self.service_environment,
        }


def assert_safe_metric_label_names(label_names: Iterable[str]) -> None:
    forbidden = sorted(FORBIDDEN_HIGH_CARDINALITY_LABELS.intersection(label_names))
    if forbidden:
        raise ValueError(f"high-cardinality metric labels are not allowed: {', '.join(forbidden)}")


def _default_if_blank(value: str | None, default: str) -> str:
    if value is None or value == "":
        return default
    return value
