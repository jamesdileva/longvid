"""Export presets (roadmap Phase 18; implementation-guide §24).

A preset is a named bundle of delivery settings — container, codecs, quality
and a resolution cap — for a target platform. Pure data so the API, pipeline
and tests share one source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

SUPPORTED_CONTAINERS = ("mp4",)
SUPPORTED_VIDEO_CODECS = ("h264", "h265")
SUPPORTED_AUDIO_CODECS = ("aac",)

DEFAULT_EXPORT_PRESET_KEY = "youtube"


class UnknownExportPresetError(ValueError):
    """Raised when an export preset key is not in the catalog."""


@dataclass(frozen=True)
class ExportPreset:
    """An immutable export preset."""

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

    def to_dict(self) -> dict:
        return asdict(self)


_PRESETS: tuple[ExportPreset, ...] = (
    ExportPreset(
        key="youtube",
        label="YouTube",
        description="H.264 1080p, fast-start MP4 for standard uploads.",
        container="mp4",
        video_codec="h264",
        audio_codec="aac",
        crf=20,
        encoder_preset="medium",
        max_width=1920,
        audio_bitrate="192k",
    ),
    ExportPreset(
        key="youtube_shorts",
        label="YouTube Shorts",
        description="H.264 vertical-ready MP4 capped at 1080px wide.",
        container="mp4",
        video_codec="h264",
        audio_codec="aac",
        crf=21,
        encoder_preset="medium",
        max_width=1080,
        audio_bitrate="192k",
    ),
    ExportPreset(
        key="tiktok",
        label="TikTok",
        description="H.264 1080p MP4 tuned for short-form social.",
        container="mp4",
        video_codec="h264",
        audio_codec="aac",
        crf=21,
        encoder_preset="medium",
        max_width=1080,
        audio_bitrate="192k",
    ),
    ExportPreset(
        key="instagram_reels",
        label="Instagram Reels",
        description="H.264 1080p MP4 tuned for Reels.",
        container="mp4",
        video_codec="h264",
        audio_codec="aac",
        crf=21,
        encoder_preset="medium",
        max_width=1080,
        audio_bitrate="192k",
    ),
    ExportPreset(
        key="archive",
        label="Local archive",
        description="H.265 full-resolution MP4 for compact local archives.",
        container="mp4",
        video_codec="h265",
        audio_codec="aac",
        crf=20,
        encoder_preset="slow",
        max_width=None,
        audio_bitrate="320k",
    ),
)

EXPORT_PRESETS: dict[str, ExportPreset] = {preset.key: preset for preset in _PRESETS}


def list_export_presets() -> list[ExportPreset]:
    """Return the export presets in display order."""
    return list(_PRESETS)


def get_export_preset(key: str) -> ExportPreset:
    """Return the preset for ``key`` or raise :class:`UnknownExportPresetError`."""
    try:
        return EXPORT_PRESETS[key]
    except KeyError as exc:
        supported = ", ".join(EXPORT_PRESETS)
        raise UnknownExportPresetError(
            f"Unknown export preset '{key}'. Supported presets: {supported}."
        ) from exc
