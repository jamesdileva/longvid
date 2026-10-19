"""Editing profile schemas (implementation-guide §16)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.editing.profiles import EditingProfile


class EditingProfileRead(BaseModel):
    """A named editing profile exposed to the UI."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str
    aspect_ratio: str
    captions: bool
    zoom: bool
    audio_normalization: bool
    max_duration_seconds: float | None
    pacing: str

    @classmethod
    def from_profile(cls, profile: EditingProfile) -> EditingProfileRead:
        """Build a read model from a catalog profile."""
        return cls.model_validate(profile)
