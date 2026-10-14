"""UTC time helpers. All stored timestamps are naive UTC for SQLite portability."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (matches SQLite storage)."""
    return datetime.now(UTC).replace(tzinfo=None)
