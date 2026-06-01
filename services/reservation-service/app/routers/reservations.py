from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status

from app import kafka, schemas
from app.config import settings
from app.dependencies import get_user_id
from app.routers.dependencies import reservation_command_service, reservation_query_service
from app.services import ReservationCommandService, ReservationQueryService
from app.services.reservations import concert_id_from_request


router = APIRouter()


@router.post("/reservations", status_code=status.HTTP_201_CREATED, response_model=schemas.ReservationResponse)
async def create_reservation(
    request: schemas.CreateReservationRequest,
    http_request: Request,
    reservations: Annotated[ReservationCommandService, Depends(reservation_command_service)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> schemas.ReservationResponse:
    response = reservations.create_reservation(user_id, request)
    await kafka.publish_event(
        settings.reservation_created_topic,
        _reservation_event_payload(
            event_name="reservation-created",
            response=response,
            source_id=response.id,
            concert_id=concert_id_from_request(request),
            http_request=http_request,
        ),
    )
    return response


@router.get("/reservations/me", response_model=schemas.ReservationListResponse)
def list_my_reservations(
    reservations: Annotated[ReservationQueryService, Depends(reservation_query_service)],
    user_id: Annotated[str, Depends(get_user_id)],
    limit: int = 20,
) -> schemas.ReservationListResponse:
    return reservations.list_my_reservations(user_id, limit)


@router.get("/reservations/{id}", response_model=schemas.ReservationResponse)
def get_reservation(id: str, reservations: Annotated[ReservationQueryService, Depends(reservation_query_service)]) -> schemas.ReservationResponse:
    return reservations.get_reservation(id)


@router.post("/reservations/{id}/cancel", response_model=schemas.ReservationResponse)
def cancel_reservation(id: str, reservations: Annotated[ReservationCommandService, Depends(reservation_command_service)]) -> schemas.ReservationResponse:
    return reservations.cancel_reservation(id)


@router.post("/reservations/{id}/expire", response_model=schemas.ReservationResponse)
async def expire_reservation(
    id: str,
    http_request: Request,
    reservations: Annotated[ReservationCommandService, Depends(reservation_command_service)],
) -> schemas.ReservationResponse:
    response = reservations.expire_reservation(id)
    await kafka.publish_event(
        settings.reservation_expired_topic,
        _reservation_event_payload(
            event_name="reservation-expired",
            response=response,
            source_id=response.id,
            concert_id=None,
            http_request=http_request,
        ),
    )
    return response


def _reservation_event_payload(
    *,
    event_name: str,
    response: schemas.ReservationResponse,
    source_id: str,
    concert_id: str | None,
    http_request: Request,
) -> dict:
    return {
        "eventId": f"evt-{uuid4()}",
        "eventType": event_name,
        "userId": _event_user_id(response.userId),
        "sourceId": source_id,
        "reservationId": response.id,
        "concertId": concert_id,
        "seatId": response.seatId,
        "occurredAt": datetime.now(UTC).isoformat(),
        "producer": settings.service_name,
        "correlationId": getattr(http_request.state, "request_id", None) or http_request.headers.get("X-Request-Id"),
    }


def _event_user_id(value: str) -> int | str:
    return int(value) if value.isdigit() else value
