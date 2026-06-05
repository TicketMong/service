from fastapi import FastAPI, status
from observability import HttpError, register_error_handlers

from app.config import settings


class NotFoundError(HttpError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            f"{resource}.not_found",
            f"{resource} not found.",
            {"id": resource_id},
            domain="reservation",
        )


class ConflictError(HttpError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(status.HTTP_409_CONFLICT, code, message, details, domain="reservation")


def register_exception_handlers(app: FastAPI) -> None:
    register_error_handlers(app, service_name=settings.service_name, domain="reservation")
