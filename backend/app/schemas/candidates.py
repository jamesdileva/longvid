"""Candidate schemas — the API contract mirrored by the frontend types/."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.candidate import CandidateStatus


class CandidateStatusUpdate(BaseModel):
    """Human feedback on a candidate."""

    status: CandidateStatus


class CandidateRead(BaseModel):
    """A scored candidate clip proposal."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    start_seconds: float
    end_seconds: float
    status: CandidateStatus
    semantic_score: float
    audio_score: float
    visual_score: float
    context_score: float
    standalone_score: float
    novelty_score: float
    overall_score: float
    category: str | None
    reason: str | None
    source: str
    event_ids: str | None
    created_at: datetime
    updated_at: datetime
