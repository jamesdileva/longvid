"""Tests for hook detection: strongest opening moment (roadmap 12.4)."""

from __future__ import annotations

from app.editing.hooks import select_hook
from app.editing.profiles import get_profile
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle

SEGMENTS = [
    (0.0, 4.0, "so anyway welcome back"),
    (10.0, 14.0, "HUGE revelation about 2024"),
    (14.0, 18.0, "and here is the payoff"),
]


def _hook(profile_key: str = "shorts", **overrides):
    return select_hook(
        get_profile(profile_key),
        segments=overrides.pop("segments", SEGMENTS),
        start_seconds=overrides.pop("start_seconds", 0.0),
        end_seconds=overrides.pop("end_seconds", 20.0),
        emphasis_times=overrides.pop("emphasis_times", []),
        min_opening_seconds=overrides.pop("min_opening_seconds", 1.5),
        min_remaining_seconds=overrides.pop("min_remaining_seconds", 3.0),
        min_score=overrides.pop("min_score", 1.0),
        keyword_limit=overrides.pop("keyword_limit", 3),
    )


class TestHookSelection:
    def test_non_hook_profiles_return_none(self) -> None:
        assert _hook("clean") is None
        assert _hook("youtube") is None

    def test_strongest_later_sentence_becomes_the_opening(self) -> None:
        hook = _hook()

        assert hook is not None
        assert hook.applied is True
        assert hook.hook_start_seconds == 10.0
        assert hook.hook_end_seconds == 14.0
        assert hook.hook_text == "HUGE revelation about 2024"
        assert hook.skipped_seconds == 10.0
        assert hook.score >= 2

    def test_strongest_already_at_the_opening_is_not_reapplied(self) -> None:
        hook = _hook(
            segments=[
                (0.0, 4.0, "HUGE revelation about 2024"),
                (4.0, 8.0, "and then some filler"),
            ],
        )

        assert hook is not None
        assert hook.applied is False
        assert hook.hook_start_seconds == 0.0
        assert hook.skipped_seconds == 0.0

    def test_no_segments_means_no_hook(self) -> None:
        assert _hook(segments=[]) is None

    def test_too_late_sentences_are_ineligible(self) -> None:
        hook = _hook(
            segments=[(0.0, 2.0, "uh"), (19.0, 20.0, "HUGE revelation about 2024")],
        )

        assert hook is None

    def test_weak_sentences_are_rejected_by_the_score_threshold(self) -> None:
        hook = _hook(
            segments=[(0.0, 2.0, "um"), (5.0, 7.0, "so um yeah")],
        )

        assert hook is None

    def test_emphasis_moments_boost_a_sentence(self) -> None:
        hook = _hook(
            segments=[(0.0, 4.0, "ordinary words here"), (6.0, 9.0, "another plain line")],
            emphasis_times=[7.0],
            min_score=1.0,
        )

        assert hook is not None
        assert hook.hook_start_seconds == 6.0
        assert hook.applied is True

    def test_to_dict_records_the_decision(self) -> None:
        hook = _hook()

        assert hook is not None
        data = hook.to_dict()
        assert data["applied"] is True
        assert data["hook_start_seconds"] == 10.0
        assert data["skipped_seconds"] == 10.0
        assert data["hook_text"] == "HUGE revelation about 2024"


@requires_ffmpeg
class TestHookThroughApi:
    def test_shorts_clip_records_a_hook(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        hook = clip["editing_plan"]["hook"]
        assert "HIGHLIGHT" in hook["hook_text"]
        assert isinstance(hook["score"], float)

    def test_clean_clip_has_no_hook(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert "hook" not in clip["editing_plan"]
