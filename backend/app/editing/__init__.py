"""Editing engine: reusable editing profiles and deterministic editing plans.

A profile (implementation-guide §16) is a named bundle of editing settings
(Clean / YouTube / Shorts / TikTok). The engine turns a profile + a clip range
into a deterministic editing plan (§21) that later render stages execute.
"""

from app.editing.plan import build_editing_plan, clamp_duration
from app.editing.profiles import (
    DEFAULT_PROFILE_KEY,
    PROFILES,
    SUPPORTED_ASPECT_RATIOS,
    EditingProfile,
    UnknownProfileError,
    get_profile,
    list_profiles,
)

__all__ = [
    "DEFAULT_PROFILE_KEY",
    "PROFILES",
    "SUPPORTED_ASPECT_RATIOS",
    "EditingProfile",
    "UnknownProfileError",
    "build_editing_plan",
    "clamp_duration",
    "get_profile",
    "list_profiles",
]
