"""Job schemas — the API contract mirrored by the frontend ``types/``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.processing import JobStatus, JobType


class JobProcessRequest(BaseModel):
    """Payload requesting a background job for a video."""

    type: JobType


class JobRead(BaseModel):
    """Processing job representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    type: JobType
    status: JobStatus
    progress: float
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
