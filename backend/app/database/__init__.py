"""Database layer: SQLAlchemy engine, session factory, and schema bootstrap.

The engine is created lazily and cached per-settings, which lets tests swap
``LONGVID_DATA_DIR`` and get an isolated database.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM entities."""


@lru_cache
def get_engine():
    """Return the process-wide engine, creating the data directory first."""
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    # check_same_thread=False is required: FastAPI workers run outside the
    # thread that created the connection.
    return create_engine(settings.database_url, connect_args={"check_same_thread": False})


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    """Cached session factory bound to the engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call repeatedly."""
    # Import models so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(get_engine())


def db_health_check() -> str:
    """Run a trivial query so callers can verify connectivity."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "error"
    return "ok"


def reset_caches() -> None:
    """Clear engine/session caches. Used by tests after settings changes."""
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
