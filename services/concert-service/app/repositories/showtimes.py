"""Showtime persistence queries."""
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import entities as model


class ShowtimeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_showtime(self, showtime_id: str) -> model.Showtime | None:
        return self.db.scalar(
            select(model.Showtime)
            .options(
                selectinload(model.Showtime.seats),
                selectinload(model.Showtime.seat_grades),
                selectinload(model.Showtime.venue),
            )
            .where(model.Showtime.id == showtime_id)
        )

    def list_showtimes(self, concert_id: str, limit: int) -> Sequence[model.Showtime]:
        return self.db.scalars(
            select(model.Showtime)
            .where(model.Showtime.concert_id == concert_id)
            .order_by(model.Showtime.starts_at)
            .limit(limit)
        ).all()

    def list_showtimes_between(self, concert_id: str, start_at: datetime, end_at: datetime) -> Sequence[model.Showtime]:
        return self.db.scalars(
            select(model.Showtime)
            .where(
                model.Showtime.concert_id == concert_id,
                model.Showtime.starts_at >= start_at,
                model.Showtime.starts_at < end_at,
            )
            .order_by(model.Showtime.starts_at)
        ).all()

    def list_bookable_showtime_starts_between(self, concert_id: str, start_at: datetime, end_at: datetime) -> Sequence[datetime]:
        sellable_seat_exists = (
            select(model.Seat.id)
            .where(
                model.Seat.showtime_id == model.Showtime.id,
                model.Seat.status == "sellable",
            )
            .exists()
        )
        return self.db.scalars(
            select(model.Showtime.starts_at)
            .where(
                model.Showtime.concert_id == concert_id,
                model.Showtime.starts_at >= start_at,
                model.Showtime.starts_at < end_at,
                model.Showtime.status.not_in(("closed", "canceled", "sold_out")),
                sellable_seat_exists,
            )
            .order_by(model.Showtime.starts_at)
        ).all()
