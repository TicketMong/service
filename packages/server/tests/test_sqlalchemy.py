import pytest

from server.sqlalchemy import sqlalchemy_engine_options_from_env


def test_sqlalchemy_engine_options_use_bounded_postgres_pool_defaults() -> None:
    options = sqlalchemy_engine_options_from_env("postgresql+psycopg://user:password@db:5432/app", env={})

    assert options == {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 0,
        "pool_timeout": 5.0,
        "pool_recycle": 1800,
    }


def test_sqlalchemy_engine_options_accept_pool_overrides() -> None:
    options = sqlalchemy_engine_options_from_env(
        "postgresql+psycopg://user:password@db:5432/app",
        env={
            "SQLALCHEMY_POOL_SIZE": "3",
            "SQLALCHEMY_MAX_OVERFLOW": "1",
            "SQLALCHEMY_POOL_TIMEOUT_SECONDS": "2.5",
            "SQLALCHEMY_POOL_RECYCLE_SECONDS": "600",
        },
    )

    assert options["pool_size"] == 3
    assert options["max_overflow"] == 1
    assert options["pool_timeout"] == 2.5
    assert options["pool_recycle"] == 600


def test_sqlalchemy_engine_options_keep_sqlite_connect_args() -> None:
    options = sqlalchemy_engine_options_from_env("sqlite:///./app.db", env={"SQLALCHEMY_POOL_SIZE": "3"})

    assert options == {
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False},
    }


def test_sqlalchemy_engine_options_reject_invalid_pool_size() -> None:
    with pytest.raises(ValueError, match="SQLALCHEMY_POOL_SIZE must be >= 1"):
        sqlalchemy_engine_options_from_env(
            "postgresql+psycopg://user:password@db:5432/app",
            env={"SQLALCHEMY_POOL_SIZE": "0"},
        )
