from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from errors import ExceptionContext, get_exception_context

SafeErrorContextValue = str | int | float | bool
SafeErrorContext = Mapping[str, SafeErrorContextValue]


@runtime_checkable
class SupportsErrorContext(Protocol):
    # 나중에 packages/errors의 context를 읽기 위한 자리다. errors 쪽이 FastAPI나 OpenTelemetry를 알면 안 된다.
    def observability_context(self) -> SafeErrorContext:
        ...


def extract_error_context(exc: BaseException) -> SafeErrorContext:
    context = get_exception_context(exc)
    attributes = exception_context_to_attributes(context)

    if attributes:
        return attributes

    if isinstance(exc, SupportsErrorContext):
        return _safe_mapping(exc.observability_context())

    legacy_context = getattr(exc, "error_context", None)
    if isinstance(legacy_context, Mapping):
        return _safe_mapping(legacy_context)

    return {}


def exception_context_to_attributes(context: ExceptionContext) -> dict[str, SafeErrorContextValue]:
    if context.is_empty:
        return {}

    attributes: dict[str, SafeErrorContextValue] = {}
    _set_if_safe(attributes, "error.code", context.code)
    _set_if_safe(attributes, "error.domain", context.domain)
    _set_if_safe(attributes, "error.message", context.message)
    _set_if_safe(attributes, "error.public_message", context.public_message)
    _set_if_safe(attributes, "error.hint", context.hint)
    _set_if_safe(attributes, "error.owner", context.owner)
    _set_if_safe(attributes, "error.user", context.user)
    _set_if_safe(attributes, "error.tenant", context.tenant)
    _set_if_safe(attributes, "error.duration_ms", context.duration_ms)
    if context.tags:
        attributes["error.tags"] = ",".join(context.tags)
    if context.occurred_at is not None:
        attributes["error.occurred_at"] = _format_datetime(context.occurred_at)

    for key, value in context.attributes.items():
        _set_if_safe(attributes, f"error.attr.{_normalize_attribute_key(key)}", value)

    return attributes


def _safe_mapping(values: Mapping[str, Any]) -> dict[str, SafeErrorContextValue]:
    safe: dict[str, SafeErrorContextValue] = {}
    for key, value in values.items():
        _set_if_safe(safe, str(key), value)
    return safe


def _is_safe_context_value(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _set_if_safe(attributes: dict[str, SafeErrorContextValue], key: str, value: Any) -> None:
    if _is_safe_context_value(value):
        attributes[key] = value


def _normalize_attribute_key(key: object) -> str:
    return str(key).strip().replace(" ", "_").replace("-", "_")


def _format_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
