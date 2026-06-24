from __future__ import annotations

import tomllib
from pathlib import Path
from uuid import UUID, uuid5

from errors import ContextualError, errctx, get_exception_context, in_domain


TEST_UUID_NAMESPACE = UUID("018f0d5b-8e30-7a60-9bf1-91b6d979d3c0")
SEAT_ID = str(uuid5(TEST_UUID_NAMESPACE, "errors-test:seat:1"))
RESERVATION_ID = str(uuid5(TEST_UUID_NAMESPACE, "errors-test:reservation:1"))


def test_attach_context_to_regular_exception_and_raise_same_object() -> None:
    exc = ValueError("seat already reserved")

    attached = (
        in_domain("reservation")
        .code("reservation.conflict")
        .tag("seat")
        .with_attr("seat_id", SEAT_ID)
        .public("Seat is already reserved.")
        .hint("Check active reservation unique constraint.")
        .owner("reservation")
        .attach(exc)
    )

    assert attached is exc

    try:
        raise exc
    except ValueError as raised:
        assert raised is exc
        context = get_exception_context(raised)

    assert context.domain == "reservation"
    assert context.code == "reservation.conflict"
    assert context.tags == ("seat",)
    assert context.attributes == {"seat_id": SEAT_ID}
    assert context.public_message == "Seat is already reserved."
    assert context.hint == "Check active reservation unique constraint."
    assert context.owner == "reservation"
    assert context.occurred_at is not None


def test_get_exception_context_returns_empty_context_when_missing() -> None:
    context = get_exception_context(RuntimeError("missing"))

    assert context.is_empty
    assert context.attributes == {}
    assert context.tags == ()


def test_attach_merges_with_existing_context_without_dropping_values() -> None:
    exc = RuntimeError("reservation failed")

    in_domain("reservation").code("reservation.conflict").tag("seat").with_attr("seat_id", SEAT_ID).attach(exc)
    (
        errctx()
        .in_domain("payment")
        .code("payment.failed")
        .tag("retry")
        .tags("dependency", "seat")
        .with_attr("reservation_id", RESERVATION_ID)
        .attach(exc)
    )

    context = get_exception_context(exc)

    assert context.domain == "reservation"
    assert context.code == "reservation.conflict"
    assert context.tags == ("seat", "retry", "dependency")
    assert context.attributes == {
        "seat_id": SEAT_ID,
        "reservation_id": RESERVATION_ID,
    }


def test_raise_from_preserves_exception_chain_and_context_lookup() -> None:
    class ReservationConflict(ContextualError):
        pass

    try:
        try:
            original = ValueError("unique constraint")
            in_domain("reservation").code("reservation.conflict").with_attr("seat_id", SEAT_ID).attach(original)
            raise original
        except ValueError as exc:
            raise ReservationConflict("Seat is already reserved.") from exc
    except ReservationConflict as wrapped:
        context = get_exception_context(wrapped)

        assert wrapped.__cause__ is not None
        assert context.cause is wrapped.__cause__
        assert context.domain == "reservation"
        assert context.code == "reservation.conflict"
        assert context.attributes == {"seat_id": SEAT_ID}


def test_business_code_can_add_context_without_observability_imports() -> None:
    def reserve_seat() -> None:
        try:
            raise ValueError("duplicate seat hold")
        except ValueError as exc:
            (
                in_domain("reservation")
                .code("reservation.seat_hold_conflict")
                .tag("seat")
                .with_attr("seat_id", SEAT_ID)
                .public("Seat is already reserved.")
                .attach(exc)
            )
            raise

    try:
        reserve_seat()
    except ValueError as exc:
        context = get_exception_context(exc)

    assert context.code == "reservation.seat_hold_conflict"
    assert context.domain == "reservation"
    assert context.public_message == "Seat is already reserved."


def test_errors_package_has_no_observability_framework_dependencies() -> None:
    package_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert dependencies == []

    source_text = "\n".join(path.read_text(encoding="utf-8") for path in (package_root / "src" / "errors").glob("*.py"))
    banned_names = ("opentelemetry", "fastapi", "structlog", "sentry")

    for name in banned_names:
        assert name not in source_text.lower()
