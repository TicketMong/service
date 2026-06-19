from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from observability import instrument_sqlalchemy_engine
from server import sqlalchemy_engine_options_from_env

from app.config import settings


engine = create_engine(settings.database_url, **sqlalchemy_engine_options_from_env(settings.database_url))
instrument_sqlalchemy_engine(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
