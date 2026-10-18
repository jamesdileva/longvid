"""Tests for editing profiles and deterministic editing plans (roadmap 10.1)."""

from __future__ import annotations

import pytest

from app.editing import (
    SUPPORTED_ASPECT_RATIOS,
    UnknownProfileError,
    build_editing_plan,
    clamp_duration,
    get_profile,
    list_profiles,
)
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle


class TestProfileCatalog:
    def test_exposes_clean_youtube_shorts_tiktok(self) -> None:
        assert [profile.key for profile in list_profiles()] == [
            "clean",
            "youtube",
            "shorts",
            "tiktok",
        ]

    def test_clean_keeps_the_source_aspect_ratio_unedited(self) -> None:
        profile = get_profile("clean")
        assert profile.aspect_ratio == "original"
        assert profile.captions is False
        assert profile.zoom is False
        assert profile.audio_normalization is False
        assert profile.max_duration_seconds is None

    def test_youtube_is_landscape_with_normalized_audio(self) -> None:
        profile = get_profile("youtube")
        assert profile.aspect_ratio == "16:9"
        assert profile.captions is False
        assert profile.zoom is False
        assert profile.audio_normalization is True

    def test_shorts_and_tiktok_are_vertical_captioned_and_capped(self) -> None:
        for key in ("shorts", "tiktok"):
            profile = get_profile(key)
            assert profile.aspect_ratio == "9:16"
            assert profile.captions is True
            assert profile.zoom is True
            assert profile.max_duration_seconds == 60.0

    def test_every_profile_uses_a_supported_aspect_ratio(self) -> None:
        assert all(profile.aspect_ratio in SUPPORTED_ASPECT_RATIOS for profile in list_profiles())

    def test_unknown_profile_raises_with_guidance(self) -> None:
        with pytest.raises(UnknownProfileError) as excinfo:
            get_profile("bogus")
        assert "bogus" in str(excinfo.value)
        assert "clean" in str(excinfo.value)


class TestEditingPlan:
    def test_plan_contains_documented_keys(self) -> None:
        plan = build_editing_plan(
            get_profile("shorts"), source="source/talk.mp4", start_seconds=10.0, end_seconds=40.0
        )
        assert plan["profile"] == "shorts"
        assert plan["source"] == "source/talk.mp4"
        assert plan["start"] == 10.0
        assert plan["end"] == 40.0
        assert plan["aspect_ratio"] == "9:16"
        assert plan["captions"] is True
        assert plan["zoom"] is True
        assert plan["audio_normalization"] is True

    def test_plan_rounds_timestamps(self) -> None:
        plan = build_editing_plan(
            get_profile("clean"), source="source/x.mp4", start_seconds=1.23456, end_seconds=2.98765
        )
        assert plan["start"] == 1.235
        assert plan["end"] == 2.988

    def test_plan_caps_vertical_duration(self) -> None:
        plan = build_editing_plan(
            get_profile("tiktok"), source="source/x.mp4", start_seconds=5.0, end_seconds=120.0
        )
        assert plan["end"] == 65.0

    def test_clamp_duration_without_cap_is_a_noop(self) -> None:
        assert clamp_duration(get_profile("clean"), 3.0, 9.0) == (3.0, 9.0)

    def test_clamp_duration_keeps_invalid_ranges_for_callers(self) -> None:
        assert clamp_duration(get_profile("shorts"), 10.0, 10.0) == (10.0, 10.0)


class TestEditingProfilesApi:
    def test_lists_profiles(self, client) -> None:
        response = client.get("/api/editing-profiles")
        assert response.status_code == 200
        body = response.json()
        assert [profile["key"] for profile in body] == ["clean", "youtube", "shorts", "tiktok"]
        shorts = next(profile for profile in body if profile["key"] == "shorts")
        assert shorts["label"] == "Shorts"
        assert shorts["aspect_ratio"] == "9:16"
        assert shorts["max_duration_seconds"] == 60.0


@requires_ffmpeg
class TestEditingProfileOnClips:
    def test_clip_records_the_chosen_profile_and_plan(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["editing_profile"] == "shorts"
        plan = clip["editing_plan"]
        assert plan["profile"] == "shorts"
        assert plan["aspect_ratio"] == "9:16"
        assert plan["captions"] is True
        assert plan["source"].startswith("source/")

    def test_unknown_profile_is_rejected(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        response = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "cinema"},
        )

        assert response.status_code == 400
        assert "cinema" in response.json()["detail"]
