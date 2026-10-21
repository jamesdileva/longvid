"""Content profile schemas (roadmap Phase 13)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.analysis.content_profiles import ContentProfile


class ContentProfileRead(BaseModel):
    """A content profile exposed to the UI."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str
    guidance: str
    keywords: list[str]
    category: str

    @classmethod
    def from_profile(cls, profile: ContentProfile) -> ContentProfileRead:
        """Build a read model from a catalog profile."""
        return cls(
            key=profile.key,
            label=profile.label,
            description=profile.description,
            guidance=profile.guidance,
            keywords=list(profile.keywords),
            category=profile.category,
        )
