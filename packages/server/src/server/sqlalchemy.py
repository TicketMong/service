from collections.abc import Mapping
from dataclasses import dataclass
import os
from typing import Any

from sqlalchemy.engine.url import make_url


DEFAULT_SQLALCHEMY_POOL_SIZE = 5
DEFAULT_SQLALCHEMY_MAX_OVERFLOW = 0
DEFAULT_SQLALCHEMY_POOL_TIMEOUT_SECONDS = 5.0
DEFAULT_SQLALCHEMY_POOL_RECYCLE_SECONDS = 1800


@dataclass(frozen=True)
class SQLAlchemyPoolSettings:
    pool_size: int = DEFAULT_SQLALCHEMY_POOL_SIZE
    max_overflow: int = DEFAULT_SQLALCHEMY_MAX_OVERFLOW
    pool_timeout_seconds: float = DEFAULT_SQLALCHEMY_POOL_TIMEOUT_SECONDS
    pool_recycle_seconds: int = DEFAULT_SQLALCHEMY_POOL_RECYCLE_SECONDS


def sqlalchemy_engine_options_from_env(
    database_url: str,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {"pool_pre_ping": True}
    if _is_sqlite_url(database_url):
        options["connect_args"] = {"check_same_thread": False}
        return options

    pool = _pool_settings_from_env(os.environ if env is None else env)
    options.update(
        pool_size=pool.pool_size,
        max_overflow=pool.max_overflow,
        pool_timeout=pool.pool_timeout_seconds,
        pool_recycle=pool.pool_recycle_seconds,
    )
    return options


def _pool_settings_from_env(env: Mapping[str, str]) -> SQLAlchemyPoolSettings:
    return SQLAlchemyPoolSettings(
        pool_size=_int_env(env, "SQLALCHEMY_POOL_SIZE", default=DEFAULT_SQLALCHEMY_POOL_SIZE, minimum=1),
        max_overflow=_int_env(env, "SQLALCHEMY_MAX_OVERFLOW", default=DEFAULT_SQLALCHEMY_MAX_OVERFLOW, minimum=0),
        pool_timeout_seconds=_float_env(
            env,
            "SQLALCHEMY_POOL_TIMEOUT_SECONDS",
            default=DEFAULT_SQLALCHEMY_POOL_TIMEOUT_SECONDS,
            minimum_exclusive=0,
        ),
        pool_recycle_seconds=_int_env(
            env,
            "SQLALCHEMY_POOL_RECYCLE_SECONDS",
            default=DEFAULT_SQLALCHEMY_POOL_RECYCLE_SECONDS,
            minimum=0,
        ),
    )


def _is_sqlite_url(database_url: str) -> bool:
    return make_url(database_url).get_backend_name() == "sqlite"


def _int_env(env: Mapping[str, str], name: str, *, default: int, minimum: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _float_env(env: Mapping[str, str], name: str, *, default: float, minimum_exclusive: float) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= minimum_exclusive:
        raise ValueError(f"{name} must be > {minimum_exclusive}")
    return value
