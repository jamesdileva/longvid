"""Project schemas — the API contract mirrored by the frontend ``types/``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    """Payload for creating a project."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    """Payload for updating a project. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    """Project representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: ProjectStatus
    workspace_path: str
    video_count: int
    clip_count: int
    created_at: datetime
    updated_at: datetime
