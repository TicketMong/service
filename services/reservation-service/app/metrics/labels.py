from enum import StrEnum


class ReservationCommand(StrEnum):
    CREATE = "create"
    CANCEL = "cancel"
    EXPIRE = "expire"


class ReservationErrorCode(StrEnum):
    NONE = "none"
    CONFLICT = "reservation.conflict"
    INVALID_STATE = "reservation.invalid_state"
    NOT_FOUND = "reservation.not_found"
    SALES_NOT_OPEN = "sales.not_open"
    INTERNAL_ERROR = "reservation.internal_error"


class ReservationConflictType(StrEnum):
    SEAT_CONFLICT = "seat_conflict"


class SalesStateAction(StrEnum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"


class ReservationEventType(StrEnum):
    CREATED = "reservation-created"
    EXPIRED = "reservation-expired"


def reservation_error_code_label(code: str) -> ReservationErrorCode:
    """예약 오류 코드를 metric label용 저카디널리티 값으로 정규화한다."""
    for error_code in ReservationErrorCode:
        if code == error_code.value:
            return error_code
    return ReservationErrorCode.INTERNAL_ERROR
