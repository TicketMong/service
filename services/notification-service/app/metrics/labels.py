from enum import StrEnum


class NotificationEventType(StrEnum):
    RESERVATION_CREATED = "reservation-created"
    RESERVATION_EXPIRED = "reservation-expired"
    PAYMENT_APPROVED = "payment-approved"
    PAYMENT_FAILED = "payment-failed"
    TICKET_ISSUED = "ticket-issued"
    OTHER = "other"


class NotificationTopic(StrEnum):
    RESERVATION_CREATED = "reservation-created"
    RESERVATION_EXPIRED = "reservation-expired"
    PAYMENT_APPROVED = "payment-approved"
    PAYMENT_FAILED = "payment-failed"
    TICKET_ISSUED = "ticket-issued"
    OTHER = "other"


class NotificationRouteKind(StrEnum):
    LIST = "list"
    DETAIL = "detail"


def notification_event_type_label(value: str | None) -> NotificationEventType:
    """비즈니스 이벤트 타입을 notification-service metric label 값으로 정규화한다."""
    for event_type in NotificationEventType:
        if value == event_type.value:
            return event_type
    return NotificationEventType.OTHER


def notification_topic_label(value: str | None) -> NotificationTopic:
    """Kafka topic 값을 notification-service metric label 값으로 정규화한다."""
    for topic in NotificationTopic:
        if value == topic.value:
            return topic
    return NotificationTopic.OTHER
