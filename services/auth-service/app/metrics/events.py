from dataclasses import dataclass

from metrics import CounterMetricSpec, MetricResult, MetricSpec

from app.metrics.labels import (
    AuditEventType,
    AuditOutcome,
    AuthAction,
    AuthErrorCode,
    AuthRevocationReason,
    AuthTokenType,
)


@dataclass(frozen=True)
class AuthAttemptRecorded:
    action: AuthAction
    result: MetricResult
    error_code: AuthErrorCode

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """인증 시도 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="auth_attempts_total",
                description="Auth attempts by action and result.",
                label_fields={
                    "action": "action",
                    "result": "result",
                    "error_code": "error_code",
                },
            ),
        )


@dataclass(frozen=True)
class AuthTokenIssuedRecorded:
    token_type: AuthTokenType

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """토큰 발급 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="auth_tokens_issued_total",
                description="Auth tokens issued by token type.",
                label_fields={
                    "token_type": "token_type",
                },
            ),
        )


@dataclass(frozen=True)
class AuthTokenRevocationRecorded:
    token_type: AuthTokenType
    reason: AuthRevocationReason

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """토큰 무효화 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="auth_token_revocations_total",
                description="Auth token revocations by token type and reason.",
                label_fields={
                    "token_type": "token_type",
                    "reason": "reason",
                },
            ),
        )


@dataclass(frozen=True)
class AuditEventRecorded:
    event_type: AuditEventType
    outcome: AuditOutcome

    @classmethod
    def metric_specs(cls) -> tuple[MetricSpec, ...]:
        """감사 event가 기록할 metric spec을 반환한다."""
        return (
            CounterMetricSpec(
                name="audit_events_total",
                description="Audit events by type and outcome.",
                label_fields={
                    "event_type": "event_type",
                    "outcome": "outcome",
                },
            ),
        )
