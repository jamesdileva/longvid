"""Named editing profiles (implementation-guide §16).

Each profile bundles the destination settings a clip is aimed at:

* ``clean``   - raw cut at the source aspect ratio, no reframing, no captions.
* ``youtube`` - standard landscape, mild normalization, minimal reframing.
* ``shorts``  - vertical, captioned, moderate zoom, capped at 60 seconds.
* ``tiktok``  - vertical, captioned, energetic emphasis, capped at 60 seconds.

Profiles are pure data so the API, pipeline and tests can all share one source
of truth. Applying a profile's settings to pixels happens in later phases
(captions §10.3, vertical/reframing §11); this phase defines and validates them.
"""

from dataclasses import asdict, dataclass

SUPPORTED_ASPECT_RATIOS = ("original", "16:9", "9:16", "1:1")

DEFAULT_PROFILE_KEY = "clean"


class UnknownProfileError(ValueError):
    """Raised when an editing profile key is not in the catalog."""


@dataclass(frozen=True)
class EditingProfile:
    """An immutable editing profile."""

    key: str
    label: str
    description: str
    aspect_ratio: str
    captions: bool
    zoom: bool
    audio_normalization: bool
    max_duration_seconds: float | None = None
    pacing: str = "relaxed"
    hook: bool = False

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the profile."""
        return asdict(self)


_PROFILES: tuple[EditingProfile, ...] = (
    EditingProfile(
        key="clean",
        label="Clean",
        description="Raw cut at the source aspect ratio, no reframing or captions.",
        aspect_ratio="original",
        captions=False,
        zoom=False,
        audio_normalization=False,
    ),
    EditingProfile(
        key="youtube",
        label="YouTube",
        description="Standard landscape clip with light audio normalization.",
        aspect_ratio="16:9",
        captions=False,
        zoom=False,
        audio_normalization=True,
    ),
    EditingProfile(
        key="shorts",
        label="Shorts",
        description="Vertical captioned clip with a moderate zoom, up to 60s.",
        aspect_ratio="9:16",
        captions=True,
        zoom=True,
        audio_normalization=True,
        max_duration_seconds=60.0,
        pacing="standard",
        hook=True,
    ),
    EditingProfile(
        key="tiktok",
        label="TikTok",
        description="Vertical captioned clip with energetic emphasis, up to 60s.",
        aspect_ratio="9:16",
        captions=True,
        zoom=True,
        audio_normalization=True,
        max_duration_seconds=60.0,
        pacing="punchy",
        hook=True,
    ),
)

PROFILES: dict[str, EditingProfile] = {profile.key: profile for profile in _PROFILES}


def list_profiles() -> list[EditingProfile]:
    """Return the editing profiles in display order."""
    return list(_PROFILES)


def get_profile(key: str) -> EditingProfile:
    """Return the profile for ``key`` or raise :class:`UnknownProfileError`."""
    try:
        return PROFILES[key]
    except KeyError as exc:
        supported = ", ".join(PROFILES)
        raise UnknownProfileError(
            f"Unknown editing profile '{key}'. Supported profiles: {supported}."
        ) from exc
