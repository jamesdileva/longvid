"""Build deterministic editing plans from a profile and a clip range (§21).

The plan is the contract between selection and rendering: a plain dict that a
later FFmpeg stage executes. It is stored on each clip so an export can be
reproduced exactly (implementation-guide §24).
"""

from app.editing.profiles import EditingProfile

PLAN_VERSION = 1


def clamp_duration(
    profile: EditingProfile, start_seconds: float, end_seconds: float
) -> tuple[float, float]:
    """Clamp a clip range to the profile's maximum duration (if any).

    Vertical short-form profiles cap clips at e.g. 60 seconds. The start is kept
    and the end pulled forward; a profile without a cap returns the range
    unchanged. Invalid ranges (end <= start) are left untouched for the caller
    to reject.
    """
    if profile.max_duration_seconds is None or end_seconds <= start_seconds:
        return start_seconds, end_seconds
    limit = start_seconds + profile.max_duration_seconds
    if end_seconds > limit:
        return start_seconds, limit
    return start_seconds, end_seconds


def build_editing_plan(
    profile: EditingProfile,
    *,
    source: str,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    """Return the deterministic editing plan for a clip range."""
    start, end = clamp_duration(profile, start_seconds, end_seconds)
    return {
        "plan_version": PLAN_VERSION,
        "profile": profile.key,
        "source": source,
        "start": round(start, 3),
        "end": round(end, 3),
        "aspect_ratio": profile.aspect_ratio,
        "captions": profile.captions,
        "zoom": profile.zoom,
        "audio_normalization": profile.audio_normalization,
    }
