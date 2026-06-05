from collections.abc import Mapping
from typing import Protocol, runtime_checkable


SafeErrorContext = Mapping[str, str | int | float | bool | None]


@runtime_checkable
class SupportsErrorContext(Protocol):
    # This protocol is the future adapter seam; packages/errors must not depend on FastAPI or OpenTelemetry.
    def observability_context(self) -> SafeErrorContext:
        ...


def extract_error_context(exc: BaseException) -> SafeErrorContext:
    if isinstance(exc, SupportsErrorContext):
        return exc.observability_context()

    context = getattr(exc, "error_context", None)
    if isinstance(context, Mapping):
        return {str(key): value for key, value in context.items() if _is_safe_context_value(value)}

    return {}


def _is_safe_context_value(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)
