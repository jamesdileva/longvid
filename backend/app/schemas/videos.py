"""Video schemas — the API contract mirrored by the frontend ``types/``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.video import VideoStatus


class VideoImportRequest(BaseModel):
    """Path of a user-selected video (chosen via the Electron file dialog)."""

    path: str = Field(min_length=1, max_length=1000)


class VideoRead(BaseModel):
    """Video representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str
    filename: str
    status: VideoStatus
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    sample_rate: int | None
    channels: int | None
    file_size_bytes: int | None
    audio_path: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def thumbnail_url(self) -> str | None:
        if self.status != VideoStatus.READY:
            return None
        return f"/api/videos/{self.id}/thumbnail"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def preview_url(self) -> str | None:
        if self.status != VideoStatus.READY:
            return None
        return f"/api/videos/{self.id}/preview"
