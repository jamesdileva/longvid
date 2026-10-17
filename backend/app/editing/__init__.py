"""Editing engine: reusable editing profiles and deterministic editing plans.

A profile (implementation-guide §16) is a named bundle of editing settings
(Clean / YouTube / Shorts / TikTok). The engine turns a profile + a clip range
into a deterministic editing plan (§21) that later render stages execute, and
trims the range to natural sentence/silence boundaries first (roadmap 10.2).
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
from app.editing.trimming import TrimResult, trim_clip_range

__all__ = [
    "DEFAULT_PROFILE_KEY",
    "PROFILES",
    "SUPPORTED_ASPECT_RATIOS",
    "EditingProfile",
    "TrimResult",
    "UnknownProfileError",
    "build_editing_plan",
    "clamp_duration",
    "get_profile",
    "list_profiles",
    "trim_clip_range",
]
