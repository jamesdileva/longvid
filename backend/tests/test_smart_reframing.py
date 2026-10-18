"""Tests for smart reframing: vision providers and dynamic crop (roadmap 11.3)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.editing.framing import framing_plan
from app.editing.profiles import get_profile
from app.editing.reframing import dynamic_framing
from app.providers.vision import (
    SubjectSample,
    SubjectTrack,
    VisionProviderUnavailableError,
    get_vision_provider,
)
from app.providers.vision.synthetic import SyntheticVisionProvider
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job, run_job_settle


def _track(positions: list[tuple[float, float]]) -> SubjectTrack:
    return SubjectTrack(
        samples=tuple(
            SubjectSample(time_seconds=time, x_center=x, y_center=0.5, width=0.2, height=0.3)
            for time, x in positions
        )
    )


class TestSubjectTrack:
    def test_round_trips_through_dict(self) -> None:
        track = _track([(0.0, 0.3), (1.0, 0.6)])

        restored = SubjectTrack.from_dict(track.to_dict())

        assert restored == track
        assert not restored.is_empty

    def test_empty_payload_is_an_empty_track(self) -> None:
        assert SubjectTrack.from_dict(None).is_empty
        assert SubjectTrack.from_dict({}).is_empty


class TestVisionFactory:
    def test_synthetic_provider_is_available(self) -> None:
        provider = get_vision_provider(Settings(vision_provider="synthetic"))

        assert provider.name == "synthetic"
        assert provider.is_available()

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(VisionProviderUnavailableError):
            get_vision_provider(Settings(vision_provider="bogus"))

    def test_synthetic_track_drifts_across_the_frame(self) -> None:
        provider = SyntheticVisionProvider(sample_interval_seconds=1.0)

        track = provider.track_subjects(None, duration_seconds=10.0)  # type: ignore[arg-type]

        assert len(track.samples) == 11
        assert track.samples[0].x_center < track.samples[-1].x_center
        assert all(0.0 <= sample.x_center <= 1.0 for sample in track.samples)


class TestDynamicFraming:
    def test_follows_a_moving_subject(self) -> None:
        track = _track([(t, 0.3 + 0.03 * t) for t in range(6)])

        framing = dynamic_framing(
            get_profile("shorts"),
            source_width=1920,
            source_height=1080,
            track=track,
            start_seconds=0.0,
            end_seconds=5.0,
            smooth_window_seconds=2.0,
            max_keyframes=20,
        )

        assert framing is not None
        chain = framing.filter_chain()
        assert chain.startswith("crop=")
        assert "if(lt(t," in chain
        assert chain.endswith("scale=1080:1920,setsar=1")
        assert framing.to_dict()["dynamic"] is True

    def test_static_subject_needs_no_dynamic_crop(self) -> None:
        track = _track([(t, 0.5) for t in range(6)])

        framing = dynamic_framing(
            get_profile("shorts"),
            source_width=1920,
            source_height=1080,
            track=track,
            start_seconds=0.0,
            end_seconds=5.0,
            smooth_window_seconds=2.0,
            max_keyframes=20,
        )

        assert framing is None

    def test_no_samples_in_range_is_none(self) -> None:
        track = _track([(t, 0.3 + 0.03 * t) for t in range(4)])

        framing = dynamic_framing(
            get_profile("shorts"),
            source_width=1920,
            source_height=1080,
            track=track,
            start_seconds=100.0,
            end_seconds=110.0,
            smooth_window_seconds=2.0,
            max_keyframes=20,
        )

        assert framing is None

    def test_profiles_without_reframing_are_none(self) -> None:
        track = _track([(t, 0.3 + 0.03 * t) for t in range(4)])

        framing = dynamic_framing(
            get_profile("clean"),
            source_width=1920,
            source_height=1080,
            track=track,
            start_seconds=0.0,
            end_seconds=3.0,
            smooth_window_seconds=2.0,
            max_keyframes=20,
        )

        assert framing is None


@requires_ffmpeg
class TestSmartReframingThroughApi:
    def test_shorts_is_static_without_a_track(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["editing_plan"]["framing"].get("dynamic") is None

    def test_tracking_then_generate_yields_a_dynamic_crop(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        job = run_job(client, video["id"], "track_subjects")
        assert job["status"] == "completed"

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        framing = clip["editing_plan"]["framing"]
        assert framing["dynamic"] is True
        assert framing["keyframes"]
        assert clip["file_url"]

    def test_static_framing_used_when_reframing_disabled(
        self, client, narrate_video, monkeypatch
    ) -> None:
        from app.config import get_settings

        monkeypatch.setenv("LONGVID_SMART_REFRAME_ENABLED", "false")
        get_settings.cache_clear()
        _, video = prepare_with_candidates(client, narrate_video)
        run_job(client, video["id"], "track_subjects")

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert not clip["editing_plan"]["framing"].get("dynamic")
        assert framing_plan(get_profile("shorts"), source_width=320, source_height=240) is not None
