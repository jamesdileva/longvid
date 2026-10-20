"""Tests for dynamic zoom: emphasis pulses and the zoompan filter (roadmap 12.2)."""

from __future__ import annotations

import pytest

from app.database import get_sessionmaker
from app.editing.profiles import get_profile
from app.editing.zoom import _merge, zoom_plan
from app.services.analysis import EventInput, replace_events
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle

FPS = 10.0
SIZE = (1080, 1920)


def _plan(profile_key: str, *, emphasis=(3.0,), start=0.0, end=12.0):
    return zoom_plan(
        get_profile(profile_key),
        emphasis_times=list(emphasis),
        start_seconds=start,
        end_seconds=end,
        target_width=SIZE[0],
        target_height=SIZE[1],
        fps=FPS,
        scale=1.12,
        lead_seconds=0.3,
        hold_seconds=1.5,
        max_pulses=6,
    )


class TestZoomDetection:
    def test_landscape_profiles_do_not_zoom(self) -> None:
        assert _plan("clean") is None
        assert _plan("youtube") is None

    def test_vertical_profile_builds_a_pulse_around_the_moment(self) -> None:
        plan = _plan("shorts")

        assert plan is not None
        assert len(plan.pulses) == 1
        pulse = plan.pulses[0]
        assert pulse.start_seconds == pytest.approx(2.7)
        assert pulse.end_seconds == pytest.approx(4.5)
        assert pulse.scale == pytest.approx(1.12)

    def test_moments_outside_the_clip_are_ignored(self) -> None:
        assert _plan("shorts", emphasis=(20.0,), start=0.0, end=12.0) is None

    def test_no_emphasis_means_no_plan(self) -> None:
        assert _plan("shorts", emphasis=()) is None

    def test_unknown_target_is_skipped(self) -> None:
        plan = zoom_plan(
            get_profile("tiktok"),
            emphasis_times=[3.0],
            start_seconds=0.0,
            end_seconds=12.0,
            target_width=None,
            target_height=None,
            fps=FPS,
            scale=1.12,
            lead_seconds=0.3,
            hold_seconds=1.5,
            max_pulses=6,
        )

        assert plan is None

    def test_pulses_are_clamped_to_the_clip(self) -> None:
        plan = _plan("shorts", emphasis=(11.5,), start=0.0, end=12.0)

        assert plan is not None
        assert plan.pulses[0].end_seconds == pytest.approx(12.0)

    def test_overlapping_pulses_merge(self) -> None:
        plan = _plan("tiktok", emphasis=(3.0, 3.4))

        assert plan is not None
        assert len(plan.pulses) == 1
        assert plan.pulses[0].start_seconds == pytest.approx(2.7)
        assert plan.pulses[0].end_seconds == pytest.approx(4.9)

    def test_pulse_count_is_capped(self) -> None:
        plan = zoom_plan(
            get_profile("tiktok"),
            emphasis_times=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
            start_seconds=0.0,
            end_seconds=12.0,
            target_width=SIZE[0],
            target_height=SIZE[1],
            fps=FPS,
            scale=1.12,
            lead_seconds=0.3,
            hold_seconds=1.5,
            max_pulses=3,
        )

        assert plan is not None
        assert len(plan.pulses) == 3

    def test_merge_joins_touching_spans(self) -> None:
        assert _merge([(0.0, 1.0), (1.0, 2.0), (3.0, 4.0)]) == [(0.0, 2.0), (3.0, 4.0)]


class TestZoomFilter:
    def test_filter_uses_zoompan_at_the_framed_size(self) -> None:
        plan = _plan("shorts")

        assert plan is not None
        chain = plan.filter_chain()
        assert chain.startswith("zoompan=z='")
        assert "d=1:s=1080x1920:fps=10.00000" in chain
        assert "x='iw/2-(iw/zoom/2)'" in chain

    def test_expression_is_a_triangular_pulse_over_frame_number(self) -> None:
        plan = _plan("shorts", emphasis=(3.0,))

        assert plan is not None
        chain = plan.filter_chain()
        assert "if(between((in/10.00000),2.700,4.500)" in chain
        assert "abs(((in/10.00000)-3.600)/0.900)" in chain

    def test_filter_centers_when_there_are_no_pulses_is_impossible(self) -> None:
        # zoom_plan returns None (not an empty plan) when nothing applies.
        assert _plan("shorts", emphasis=()) is None

    def test_to_dict_records_the_plan(self) -> None:
        plan = _plan("tiktok", emphasis=(3.0,))

        assert plan is not None
        data = plan.to_dict()
        assert data["scale"] == pytest.approx(1.12)
        assert data["fps"] == pytest.approx(FPS)
        assert data["target_width"] == 1080
        assert data["pulses"] == [[2.7, 4.5, 1.12]]
        assert data["filter"].startswith("zoompan=")


@requires_ffmpeg
class TestZoomThroughApi:
    def test_tiktok_clip_records_dynamic_zoom(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)
        candidates = client.get(f"/api/videos/{video['id']}/candidates").json()
        candidate = candidates[0]
        mid = (candidate["start_seconds"] + candidate["end_seconds"]) / 2
        session = get_sessionmaker()()
        try:
            replace_events(
                session,
                video["id"],
                [EventInput(type="audio_spike", start_seconds=mid, end_seconds=mid)],
            )
        finally:
            session.close()

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "tiktok"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        zoom = clip["editing_plan"]["zoom_pulses"]
        assert len(zoom["pulses"]) >= 1
        assert "zoompan" in zoom["filter"]

    def test_youtube_clip_has_no_zoom_key(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "youtube"},
        )
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert "zoom_pulses" not in clip["editing_plan"]
