from dataclasses import dataclass

from metrics import CounterMetricSpec, Expected, FailureKind, HistogramMetricSpec, MetricResult, MetricSpec

from app.metrics.labels import (
    ReservationCommand,
    ReservationConflictType,
    ReservationErrorCode,
    ReservationEventType,
    SalesStateAction,
)


@dataclass(frozen=True)
class ReservationRecorded:
    result: MetricResult
    error_code: ReservationErrorCode
    failure_kind: FailureKind
    expected: Expected

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """예약 command event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="reservations_total",
                description="Reservation command attempts by result.",
                label_fields={
                    "result": "result",
                    "error_code": "error_code",
                    "failure_kind": "failure_kind",
                    "expected": "expected",
                },
            ),
        )


@dataclass(frozen=True)
class ReservationCommandDurationRecorded:
    command: ReservationCommand
    result: MetricResult
    duration_seconds: float

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """예약 command 처리 시간 event가 기록할 metric spec을 반환한다."""
        return (
            HistogramMetricSpec(
                name="reservation_command_duration_seconds",
                description="Reservation command duration in seconds.",
                label_fields={
                    "command": "command",
                    "result": "result",
                },
                value_field="duration_seconds",
            ),
        )


@dataclass(frozen=True)
class ReservationConflictRecorded:
    conflict_type: ReservationConflictType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """예약 충돌 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="reservation_conflicts_total",
                description="Reservation conflicts by type and result.",
                label_fields={
                    "conflict_type": "conflict_type",
                    "result": "result",
                },
            ),
        )


@dataclass(frozen=True)
class SalesStateChangeRecorded:
    action: SalesStateAction
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """판매 상태 변경 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="sales_state_changes_total",
                description="Sales state change commands by result.",
                label_fields={
                    "action": "action",
                    "result": "result",
                },
            ),
        )


@dataclass(frozen=True)
class ReservationEventPublishRecorded:
    event_type: ReservationEventType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """예약 이벤트 발행 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="reservation_events_published_total",
                description="Reservation event publish attempts by result.",
                label_fields={
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
        )
