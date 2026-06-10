from enum import StrEnum


class TicketSource(StrEnum):
    API = "api"
    PAYMENT_APPROVED_EVENT = "payment_approved_event"


class TicketArtifact(StrEnum):
    QR = "qr"
    PDF = "pdf"


class TicketEventType(StrEnum):
    PAYMENT_APPROVED = "payment-approved"
    TICKET_ISSUED = "ticket-issued"
    OTHER = "other"


class TicketTopic(StrEnum):
    PAYMENT_APPROVED = "payment-approved"
    OTHER = "other"


def ticket_event_type_label(value: str | None) -> TicketEventType:
    """이벤트 타입을 ticket-service metric label 값으로 정규화한다."""
    if value == TicketEventType.PAYMENT_APPROVED.value:
        return TicketEventType.PAYMENT_APPROVED
    if value == TicketEventType.TICKET_ISSUED.value:
        return TicketEventType.TICKET_ISSUED
    return TicketEventType.OTHER


def ticket_topic_label(value: str | None) -> TicketTopic:
    """Kafka topic 값을 ticket-service metric label 값으로 정규화한다."""
    if value == TicketTopic.PAYMENT_APPROVED.value:
        return TicketTopic.PAYMENT_APPROVED
    return TicketTopic.OTHER
