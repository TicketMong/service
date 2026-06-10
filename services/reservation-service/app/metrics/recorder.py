from time import perf_counter

from blinker import Namespace
from metrics import Expected, FailureKind, MetricLabelEvent, MetricResult

from app.metrics.events import (
    ReservationCommandDurationRecorded,
    ReservationConflictRecorded,
    ReservationRecorded,
)
from app.metrics.labels import (
    ReservationCommand,
    ReservationConflictType,
    ReservationErrorCode,
    reservation_error_code_label,
)


reservation_signals = Namespace()
reservation_telemetry_recorded = reservation_signals.signal("reservation.telemetry_recorded")


class ReservationTelemetryRecorder:
    def __init__(self, sender: str = "reservation-service") -> None:
        """예약 telemetry signal sender를 준비한다."""
        self._sender = sender

    def start_command(self, command: ReservationCommand) -> "ReservationCommandAttemptRecorder":
        """예약 command metric 기록기를 시작한다."""
        return ReservationCommandAttemptRecorder(command, recorder=self)

    def record(self, event: MetricLabelEvent) -> None:
        """예약 telemetry event를 단일 signal로 발행한다."""
        reservation_telemetry_recorded.send(self._sender, event=event)


class ReservationCommandAttemptRecorder:
    def __init__(self, command: ReservationCommand, *, recorder: ReservationTelemetryRecorder) -> None:
        """예약 command metric의 기본 실패 상태를 준비한다."""
        self._recorder = recorder
        self._started_at = perf_counter()
        self._command = command
        self._result = MetricResult.FAILURE
        self._error_code = ReservationErrorCode.INTERNAL_ERROR
        self._failure_kind = FailureKind.INTERNAL_ERROR
        self._expected = Expected.FALSE
        self._conflict_type: ReservationConflictType | None = None

    def mark_success(self) -> None:
        """예약 command 성공 상태로 metric label을 확정한다."""
        self._result = MetricResult.SUCCESS
        self._error_code = ReservationErrorCode.NONE
        self._failure_kind = FailureKind.NONE
        self._expected = Expected.TRUE
        self._conflict_type = None

    def mark_error_code(self, code: str) -> None:
        """예약 오류 코드에 맞춰 metric label을 확정한다."""
        error_code = reservation_error_code_label(code)
        self._error_code = error_code
        if error_code is ReservationErrorCode.CONFLICT:
            self._result = MetricResult.REJECTION
            self._failure_kind = FailureKind.BUSINESS_REJECTION
            self._expected = Expected.TRUE
            self._conflict_type = ReservationConflictType.SEAT_CONFLICT
            return
        if error_code in {
            ReservationErrorCode.INVALID_STATE,
            ReservationErrorCode.NOT_FOUND,
            ReservationErrorCode.SALES_NOT_OPEN,
        }:
            self._result = MetricResult.REJECTION
            self._failure_kind = FailureKind.BUSINESS_REJECTION
            self._expected = Expected.TRUE
            self._conflict_type = None
            return
        self._result = MetricResult.FAILURE
        self._failure_kind = FailureKind.INTERNAL_ERROR
        self._expected = Expected.FALSE
        self._conflict_type = None

    def record(self) -> None:
        """예약 command metric을 최종 기록한다."""
        self._recorder.record(
            ReservationRecorded(
                result=self._result,
                error_code=self._error_code,
                failure_kind=self._failure_kind,
                expected=self._expected,
            )
        )
        self._recorder.record(
            ReservationCommandDurationRecorded(
                command=self._command,
                result=self._result,
                duration_seconds=perf_counter() - self._started_at,
            )
        )
        if self._conflict_type is not None:
            self._recorder.record(
                ReservationConflictRecorded(
                    conflict_type=self._conflict_type,
                    result=self._result,
                )
            )
