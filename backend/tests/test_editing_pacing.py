"""Tests for pacing: dead-air analysis and jump-cut tightening (roadmap 12.1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.editing.pacing import _STYLE_PACING, pacing_plan
from app.editing.profiles import get_profile
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle

SEGMENTS = [(0.0, 4.0, "a"), (8.0, 12.0, "b")]
SILENCES = [(4.0, 8.0)]


def _plan(profile_key: str, **overrides):
    profile = get_profile(profile_key)
    return pacing_plan(
        profile,
        start_seconds=0.0,
        end_seconds=12.0,
        segments=SEGMENTS,
        silences=SILENCES,
        scene_times=overrides.pop("scene_times", [3.0, 9.0]),
        max_removed_ratio=overrides.pop("max_removed_ratio", 0.5),
    )


class TestPacingAnalysis:
    def test_relaxed_profile_makes_no_decision(self) -> None:
        assert _plan("clean") is None
        assert _plan("youtube") is None

    def test_reports_speech_and_silence_ratios(self) -> None:
        decision = _plan("shorts")

        assert decision is not None
        assert decision.speech_ratio == pytest.approx(8 / 12)
        assert decision.silence_ratio == pytest.approx(4 / 12)

    def test_reports_scene_change_rate(self) -> None:
        decision = _plan("shorts")

        assert decision is not None
        # two scene changes in 12s -> 10 per minute
        assert decision.scene_changes_per_minute == pytest.approx(10.0)

    def test_standard_style_cuts_dead_air_with_breathing_room(self) -> None:
        decision = _plan("shorts")

        assert decision is not None
        assert decision.applied
        assert decision.dead_air_runs == ((4.25, 7.75),)
        assert decision.silence_removed_seconds == pytest.approx(3.5)

    def test_punchy_style_keeps_less_breathing_room(self) -> None:
        decision = _plan("tiktok")

        assert decision is not None
        assert decision.dead_air_runs == ((4.15, 7.85),)

    def test_short_runs_are_left_alone(self) -> None:
        decision = pacing_plan(
            get_profile("shorts"),
            start_seconds=0.0,
            end_seconds=10.0,
            segments=[(0.0, 2.0, "a")],
            silences=[(2.0, 3.0)],
            max_removed_ratio=0.5,
        )

        assert decision is not None
        assert not decision.applied
        assert decision.dead_air_runs == ()

    def test_contiguous_transcript_does_not_block_a_cut(self) -> None:
        # ASR segments are contiguous and pad into silence; the RMS silence run
        # is trusted over transcript overlap.
        decision = pacing_plan(
            get_profile("tiktok"),
            start_seconds=0.0,
            end_seconds=12.0,
            segments=[(0.0, 12.0, "speech")],
            silences=[(4.0, 8.0)],
            max_removed_ratio=0.5,
        )

        assert decision is not None
        assert decision.applied
        assert decision.dead_air_runs == ((4.15, 7.85),)

    def test_removal_is_capped_by_budget(self) -> None:
        decision = _plan("tiktok", max_removed_ratio=0.1)

        assert decision is not None
        assert not decision.applied

    def test_style_table_covers_relaxed_standard_punchy(self) -> None:
        assert set(_STYLE_PACING) == {"relaxed", "standard", "punchy"}
        assert _STYLE_PACING["relaxed"] is None


class TestPacingFilters:
    def test_video_filter_drops_spans_and_compacts_time(self) -> None:
        decision = _plan("shorts")

        assert decision is not None
        chain = decision.video_filter()
        assert chain == "select='not(between(t,4.250,7.750))',setpts=N/FRAME_RATE/TB"

    def test_audio_filter_mirrors_the_video_spans(self) -> None:
        decision = _plan("shorts")

        assert decision is not None
        assert decision.audio_filter() == "aselect='not(between(t,4.250,7.750))',asetpts=N/SR/TB"

    def test_no_runs_means_no_filters(self) -> None:
        decision = pacing_plan(
            get_profile("tiktok"),
            start_seconds=0.0,
            end_seconds=4.0,
            silences=[],
            max_removed_ratio=0.5,
        )

        assert decision is not None
        assert decision.video_filter() is None
        assert decision.audio_filter() is None

    def test_to_dict_records_the_full_decision(self) -> None:
        decision = _plan("tiktok")

        assert decision is not None
        data = decision.to_dict()
        assert data["style"] == "punchy"
        assert data["applied"] is True
        assert data["dead_air_runs"] == [[4.15, 7.85]]
        assert data["video_filter"].startswith("select=")
        assert data["audio_filter"].startswith("aselect=")


class TestPacingProfiles:
    def test_vertical_profiles_pace_and_landscape_profiles_do_not(self) -> None:
        assert replace(get_profile("clean")).pacing == "relaxed"
        assert get_profile("youtube").pacing == "relaxed"
        assert get_profile("shorts").pacing == "standard"
        assert get_profile("tiktok").pacing == "punchy"


@requires_ffmpeg
class TestPacingThroughApi:
    def test_tiktok_clip_records_a_pacing_decision(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "tiktok"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        pacing = clip["editing_plan"]["pacing"]
        assert pacing["style"] == "punchy"
        assert isinstance(pacing["speech_ratio"], float)

    def test_clean_clip_has_no_pacing_key(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "clean"},
        )
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert "pacing" not in clip["editing_plan"]
