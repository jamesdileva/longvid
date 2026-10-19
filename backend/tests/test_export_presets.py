"""Tests for the export preset catalog (roadmap Phase 18; guide §24)."""

from __future__ import annotations

import pytest

from app.editing import (
    DEFAULT_EXPORT_PRESET_KEY,
    list_export_presets,
)
from app.editing.exports import (
    SUPPORTED_AUDIO_CODECS,
    SUPPORTED_CONTAINERS,
    SUPPORTED_VIDEO_CODECS,
    UnknownExportPresetError,
    get_export_preset,
)

EXPECTED_KEYS = ("youtube", "youtube_shorts", "tiktok", "instagram_reels", "archive")


class TestExportPresetCatalog:
    def test_default_preset_exists(self) -> None:
        assert get_export_preset(DEFAULT_EXPORT_PRESET_KEY).key == DEFAULT_EXPORT_PRESET_KEY

    def test_keys_in_display_order(self) -> None:
        assert tuple(preset.key for preset in list_export_presets()) == EXPECTED_KEYS

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(UnknownExportPresetError) as excinfo:
            get_export_preset("vimeo")
        assert "vimeo" in str(excinfo.value)
        assert "youtube" in str(excinfo.value)

    def test_every_preset_is_deliverable(self) -> None:
        for preset in list_export_presets():
            assert preset.label and preset.description
            assert preset.container in SUPPORTED_CONTAINERS
            assert preset.video_codec in SUPPORTED_VIDEO_CODECS
            assert preset.audio_codec in SUPPORTED_AUDIO_CODECS
            assert 0 <= preset.crf <= 51
            assert preset.encoder_preset
            assert preset.max_width is None or preset.max_width > 0
            assert preset.audio_bitrate.endswith("k")

    def test_archive_uses_hevc(self) -> None:
        assert get_export_preset("archive").video_codec == "h265"
        assert get_export_preset("archive").max_width is None

    def test_social_presets_cap_width(self) -> None:
        for key in ("youtube_shorts", "tiktok", "instagram_reels"):
            assert get_export_preset(key).max_width == 1080

    def test_to_dict_round_trips_frozen_dataclass(self) -> None:
        preset = get_export_preset("youtube")
        data = preset.to_dict()
        assert data["key"] == "youtube"
        assert data["container"] == "mp4"
        assert data["video_codec"] == "h264"
