"""Transcript schemas — the API contract mirrored by the frontend types/."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentRead(BaseModel):
    """A timestamped span of transcribed text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None


class TranscriptRead(BaseModel):
    """A video's transcript with its ordered segments."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    language: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    segments: list[TranscriptSegmentRead] = Field(default_factory=list)
