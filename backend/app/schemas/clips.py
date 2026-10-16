"""Clip schemas — the API contract mirrored by the frontend ``types/``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.clip import ClipStatus

ClipSelection = Literal["top5", "top10", "all", "accepted"]


class ClipGenerateRequest(BaseModel):
    """Which candidates to turn into clips.

    Either an explicit ``candidate_ids`` list or a named ``selection``
    (roadmap 9.3: Top 5 / Top 10 / All; ``accepted`` uses human-approved ones).
    """

    selection: ClipSelection = "top5"
    candidate_ids: list[int] | None = None
    editing_profile: str = Field(default="clean", min_length=1, max_length=32)


class ClipUpdate(BaseModel):
    """Editable clip fields."""

    title: str | None = Field(default=None, max_length=255)


class ClipRead(BaseModel):
    """A clip timeline definition and its render state."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    candidate_id: int | None
    title: str | None
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    editing_profile: str
    editing_plan: dict | None
    status: ClipStatus
    file_size_bytes: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_url(self) -> str | None:
        """Streaming URL once the MP4 has been rendered."""
        if self.status != ClipStatus.READY:
            return None
        return f"/api/clips/{self.id}/file"
