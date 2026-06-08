from __future__ import annotations

from typing import Any


_sqlalchemy_instrumented_engine_ids: set[int] = set()
_pymongo_instrumented = False


def instrument_sqlalchemy_engine(engine: Any) -> None:
    if engine is None:
        raise ValueError("engine must not be None")

    engine_id = id(engine)
    if engine_id in _sqlalchemy_instrumented_engine_ids:
        return

    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    SQLAlchemyInstrumentor().instrument(engine=engine)
    _sqlalchemy_instrumented_engine_ids.add(engine_id)


def instrument_motor_client(client: Any) -> None:
    global _pymongo_instrumented

    if client is None:
        raise ValueError("client must not be None")

    if _pymongo_instrumented:
        return

    from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

    PymongoInstrumentor().instrument()
    _pymongo_instrumented = True
