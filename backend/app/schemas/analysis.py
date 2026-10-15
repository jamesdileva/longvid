"""Analysis schemas — the API contract for scenes and events."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SceneRead(BaseModel):
    """A persisted scene boundary span."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    position: int
    start_seconds: float
    end_seconds: float
    score: float | None = None


class EventRead(BaseModel):
    """A generic analysis event with optional analyzer payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    type: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None
    source: str
    payload: dict[str, Any] | None = None
    created_at: datetime
