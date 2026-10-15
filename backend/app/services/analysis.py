"""Analysis persistence: scenes and generic events for a video.

Both are replaced on re-analysis so the stored data always reflects the
latest run (events also stay open to future LLM-backed analyzers).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.scene import Scene
from app.models.video import Video


@dataclass(frozen=True)
class EventInput:
    """Analyzer output waiting to be persisted as an event."""

    type: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None
    source: str = "deterministic"
    payload: dict[str, Any] | None = None


def replace_scenes(
    db: Session, video_id: int, scenes: Sequence[tuple[float, float, float | None]]
) -> list[Scene]:
    """Replace a video's scenes with the given ordered spans."""
    db.execute(delete(Scene).where(Scene.video_id == video_id))
    rows = [
        Scene(
            video_id=video_id,
            position=position,
            start_seconds=start,
            end_seconds=end,
            score=score,
        )
        for position, (start, end, score) in enumerate(scenes)
    ]
    db.add_all(rows)
    db.commit()
    return rows


def replace_events(db: Session, video_id: int, events: Sequence[EventInput]) -> list[Event]:
    """Replace a video's events with the given set."""
    db.execute(delete(Event).where(Event.video_id == video_id))
    rows = [
        Event(
            video_id=video_id,
            type=event.type,
            start_seconds=round(event.start_seconds, 3),
            end_seconds=round(event.end_seconds, 3),
            confidence=event.confidence,
            source=event.source,
            payload=json.dumps(event.payload) if event.payload else None,
        )
        for event in events
    ]
    db.add_all(rows)
    db.commit()
    return rows


def list_scenes(db: Session, video_id: int) -> list[Scene]:
    """All scenes for a video, in order."""
    stmt = select(Scene).where(Scene.video_id == video_id).order_by(Scene.position)
    return list(db.execute(stmt).scalars())


def list_events(db: Session, video_id: int) -> list[Event]:
    """All events for a video, chronological."""
    stmt = select(Event).where(Event.video_id == video_id).order_by(Event.start_seconds)
    return list(db.execute(stmt).scalars())


def get_video_duration(db: Session, video_id: int) -> float | None:
    """A video's duration, if known."""
    return db.execute(
        select(Video.duration_seconds).where(Video.id == video_id)
    ).scalar_one_or_none()
