from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from observability import instrument_sqlalchemy_engine, instrument_sqlalchemy_pool_events, trace_recorder
from server import sqlalchemy_engine_options_from_env

from app.config import settings

engine = create_engine(settings.database_url, **sqlalchemy_engine_options_from_env(settings.database_url))
instrument_sqlalchemy_engine(engine)
instrument_sqlalchemy_pool_events(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    recorder = trace_recorder()
    with recorder.span("ticket.dependency.db.session_create"):
        db = SessionLocal()
    try:
        yield db
    finally:
        with recorder.span("ticket.dependency.db.session_close"):
            db.close()
