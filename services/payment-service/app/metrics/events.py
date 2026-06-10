from dataclasses import dataclass

from metrics import CounterMetricSpec, FailureKind, HistogramMetricSpec, MetricResult, MetricSpec, Retryable

from app.metrics.labels import PaymentErrorCode, PaymentEventType, PaymentMethod


@dataclass(frozen=True)
class PaymentRecorded:
    method: PaymentMethod
    result: MetricResult
    error_code: PaymentErrorCode
    failure_kind: FailureKind
    retryable: Retryable
    duration_seconds: float

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """결제 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="payments_total",
                description="Payment attempts by result.",
                label_fields={
                    "method": "method",
                    "result": "result",
                    "error_code": "error_code",
                    "failure_kind": "failure_kind",
                    "retryable": "retryable",
                },
            ),
            HistogramMetricSpec(
                name="payment_request_duration_seconds",
                description="Payment request duration in seconds.",
                label_fields={
                    "method": "method",
                    "result": "result",
                },
                value_field="duration_seconds",
            ),
        )


@dataclass(frozen=True)
class PaymentEventPublishRecorded:
    event_type: PaymentEventType
    result: MetricResult

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """결제 이벤트 발행 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="payment_events_published_total",
                description="Payment event publish attempts by result.",
                label_fields={
                    "event_type": "event_type",
                    "result": "result",
                },
            ),
        )
