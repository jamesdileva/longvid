"""Export schemas — the API contract mirrored by the frontend ``types/``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.export import ExportStatus


class ExportPresetRead(BaseModel):
    """A selectable export preset (container, codecs and quality)."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str
    container: str
    video_codec: str
    audio_codec: str
    crf: int
    encoder_preset: str
    max_width: int | None
    audio_bitrate: str


class ExportCreate(BaseModel):
    """Request to render a clip through an export preset."""

    preset: str = Field(default="youtube", min_length=1, max_length=32)


class ExportRead(BaseModel):
    """An export request and the state of its rendered file."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    clip_id: int
    project_id: str
    preset: str
    container: str
    video_codec: str
    audio_codec: str
    settings: dict | None
    editing_profile: str | None
    plan_snapshot: dict | None
    app_version: str | None
    status: ExportStatus
    file_size_bytes: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_url(self) -> str | None:
        """Download URL once the export file has been rendered."""
        if self.status != ExportStatus.READY:
            return None
        return f"/api/exports/{self.id}/file"
