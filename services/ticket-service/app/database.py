from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from observability import instrument_sqlalchemy_engine
from server import sqlalchemy_engine_options_from_env

from app.config import settings

engine = create_engine(settings.database_url, **sqlalchemy_engine_options_from_env(settings.database_url))
instrument_sqlalchemy_engine(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
