"""Aspect-ratio conversion and center cropping (roadmap 11.1/11.2).

The deterministic MVP of reframing: given a source resolution and a profile's
target aspect ratio, work out a *center crop* that reshapes the frame and
optionally a mild *zoom* (a ``zoom``-enabled profile crops a little tighter so
the subject reads larger on a phone). No subject tracking yet — smart/dynamic
reframing (roadmap 11.3) plugs in here later.

The result is a pure FFmpeg filter chain (``crop`` then ``scale``) recorded in
the editing plan so every render is reproducible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.editing.profiles import EditingProfile

# Delivery resolutions for the supported target aspect ratios.
ASPECT_TARGETS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}

# Mild zoom for zoom-enabled (vertical) profiles: a little tighter than a plain
# center crop so the subject stays legible after the tall reframe.
ZOOM_FACTOR = 1.15


@dataclass(frozen=True)
class Framing:
    """A resolved center-crop + scale conversion."""

    target_width: int
    target_height: int
    crop_width: int
    crop_height: int
    crop_x: int
    crop_y: int
    zoom: float

    def filter_chain(self) -> str:
        """The FFmpeg video filter chain (crop, scale, square pixels)."""
        return (
            f"crop={self.crop_width}:{self.crop_height}:{self.crop_x}:{self.crop_y},"
            f"scale={self.target_width}:{self.target_height},setsar=1"
        )

    def to_dict(self) -> dict:
        """Plan snapshot including the concrete filter chain."""
        return {**asdict(self), "filter": self.filter_chain()}


def _even(value: float) -> int:
    """Largest even integer <= ``value`` (yuv420p needs even dimensions)."""
    return max(2, int(value) // 2 * 2)


def framing_plan(
    profile: EditingProfile,
    *,
    source_width: int | None,
    source_height: int | None,
) -> Framing | None:
    """Resolve a framing conversion, or ``None`` when the frame is untouched.

    Returns ``None`` when the profile keeps the source aspect ratio, when the
    source resolution is unknown, or when the source already matches the target
    aspect ratio and no zoom was requested (avoiding a needless re-encode).
    """
    if profile.aspect_ratio == "original":
        return None
    if not source_width or not source_height:
        return None
    target = ASPECT_TARGETS.get(profile.aspect_ratio)
    if target is None:
        return None

    target_ratio = target[0] / target[1]
    source_ratio = source_width / source_height
    if source_ratio >= target_ratio:
        crop_height = float(source_height)
        crop_width = source_height * target_ratio
    else:
        crop_width = float(source_width)
        crop_height = source_width / target_ratio

    if source_ratio == target_ratio and not profile.zoom:
        return None

    zoom = ZOOM_FACTOR if profile.zoom else 1.0
    crop_width_i = _even(crop_width / zoom)
    crop_height_i = _even(crop_height / zoom)
    crop_x = _even((source_width - crop_width_i) / 2)
    crop_y = _even((source_height - crop_height_i) / 2)
    return Framing(
        target_width=target[0],
        target_height=target[1],
        crop_width=crop_width_i,
        crop_height=crop_height_i,
        crop_x=max(crop_x, 0),
        crop_y=max(crop_y, 0),
        zoom=zoom,
    )
