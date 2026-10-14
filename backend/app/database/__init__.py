"""Database layer: SQLAlchemy engine, session factory, and schema bootstrap."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM entities."""


def _ensure_data_dir() -> None:
    data_dir = Path(get_settings().data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)


def _create_engine():
    _ensure_data_dir()
    # check_same_thread=False is required because FastAPI runs sync routes/workers
    # outside the connection's creating thread.
    return create_engine(get_settings().database_url, connect_args={"check_same_thread": False})


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call repeatedly."""
    Base.metadata.create_all(engine)


def db_health_check() -> str:
    """Run a trivial query so callers can verify connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "error"
    return "ok"
