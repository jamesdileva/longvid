"""Editing profiles API — the named destination presets (roadmap 10.1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.editing import list_profiles
from app.schemas import EditingProfileRead

router = APIRouter(tags=["editing"])


@router.get("/editing-profiles", response_model=list[EditingProfileRead])
def list_editing_profiles() -> list[EditingProfileRead]:
    """Return the editing profile catalog in display order."""
    return [EditingProfileRead.from_profile(profile) for profile in list_profiles()]
