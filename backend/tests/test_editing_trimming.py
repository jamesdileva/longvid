"""Tests for automatic trimming (roadmap 10.2).

Unit tests pin the pure trim_clip_range behaviour; the integration test runs
the real pipeline (transcript + analyze_events + candidates) and asserts the
created clip's plan records the trim.
"""

from __future__ import annotations

import pytest

from app.database import get_sessionmaker
from app.editing.trimming import trim_clip_range
from app.providers.transcription.base import SegmentResult
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import create_project, import_video, run_job, run_job_settle

SEGMENTS = [
    (10.0, 20.0, "first sentence"),
    (22.0, 30.0, "second sentence"),
]

SILENCES = [(30.0, 40.0)]


def trim(start: float, end: float, *, segments=SEGMENTS, silences=SILENCES, **overrides):
    defaults = {
        "sentence_tolerance": 3.0,
        "pre_roll": 0.5,
        "post_roll": 1.0,
        "duration": 100.0,
    }
    return trim_clip_range(
        start, end, segments=segments, silences=silences, **{**defaults, **overrides}
    )


class TestNoTrimNeeded:
    def test_boundaries_already_on_speech_edges(self) -> None:
        result = trim(10.0, 20.0)

        assert result.start_seconds == 10.0
        assert result.end_seconds == 20.0
        assert result.trim["applied"] is False
        assert result.trim["silence_removed_seconds"] == 0.0

    def test_no_transcript_and_no_silence_keeps_range(self) -> None:
        result = trim(5.0, 9.0, segments=[], silences=[])

        assert (result.start_seconds, result.end_seconds) == (5.0, 9.0)
        assert result.trim["applied"] is False

    def test_degenerate_range_is_left_alone(self) -> None:
        result = trim(9.0, 9.0)

        assert result.trim["applied"] is False


class TestSentenceBoundaries:
    def test_head_snaps_back_to_complete_the_opening_sentence(self) -> None:
        result = trim(12.0, 20.0)  # 2s into the first sentence, within tolerance

        assert result.start_seconds == 10.0
        assert result.trim["sentence_start"] is True

    def test_head_beyond_tolerance_is_kept(self) -> None:
        result = trim(19.0, 20.0)  # 9s into the first sentence

        assert result.start_seconds == 19.0
        assert result.trim["sentence_start"] is False

    def test_tail_snaps_forward_to_finish_the_closing_sentence(self) -> None:
        result = trim(10.0, 28.0)  # cuts the second sentence 2s short

        assert result.end_seconds == 30.0
        assert result.trim["sentence_end"] is True

    def test_tail_beyond_tolerance_is_kept(self) -> None:
        result = trim(22.0, 23.0)  # 7s short of the closing sentence's end

        assert result.end_seconds == 23.0
        assert result.trim["sentence_end"] is False

    def test_snapping_to_a_far_later_sentence_does_not_bloat_the_clip(self) -> None:
        # Only the first sentence overlaps; a far second sentence must not pull.
        result = trim(21.0, 21.5, segments=SEGMENTS[:1])

        assert result.end_seconds == 21.5


class TestSilenceRemoval:
    def test_head_inside_silence_keeps_only_pre_roll_of_dead_air(self) -> None:
        result = trim(35.0, 45.0)  # start sits 5s into the trailing silence

        assert result.start_seconds == 39.5  # silence end (40) minus pre-roll
        assert result.trim["silence_removed_seconds"] > 0.0

    def test_tail_inside_silence_keeps_only_post_roll_of_dead_air(self) -> None:
        result = trim(10.0, 35.0)  # end sits inside the trailing silence

        assert result.end_seconds == 31.0  # silence start (30) plus post-roll
        assert result.trim["silence_removed_seconds"] > 0.0

    def test_silence_trimming_works_without_transcript(self) -> None:
        result = trim(35.0, 45.0, segments=[], silences=[(30.0, 40.0)])

        assert result.start_seconds == 39.5
        assert result.end_seconds == 45.0
        assert result.trim["applied"] is True

    def test_tail_just_past_a_silence_run_is_still_trimmed(self) -> None:
        # A run reaching the video end stops one sampling step short (29.952),
        # while the padded boundary is the video end itself (30.0).
        result = trim(0.0, 30.0, silences=[(15.04, 29.952)], duration=30.0)

        assert result.end_seconds == 16.04  # run start + post-roll
        assert result.trim["applied"] is True

    def test_head_silence_start_is_respected_as_floor(self) -> None:
        result = trim(30.5, 45.0)  # start just inside the run start

        assert result.start_seconds == 39.5  # floor is the run start, target the speech edge


class TestBoundsAndSafety:
    def test_range_is_clamped_to_video_duration(self) -> None:
        result = trim(90.0, 99.0, silences=[], duration=95.0)

        assert result.end_seconds == 95.0

    def test_reverted_range_reports_not_applied(self) -> None:
        # A pathological squeeze (silence + instant speech) must not collapse.
        result = trim(39.9, 40.1, silences=[(30.0, 40.0)], duration=100.0)

        assert result.end_seconds > result.start_seconds


@requires_ffmpeg
class TestTrimmingThroughApi:
    def test_clip_plan_records_the_trim(self, client, narrate_video) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)
        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "transcribe")

        session = get_sessionmaker()()
        try:
            row = video_service.get_video(session, video["id"])
            assert row is not None
            transcript_service.replace_transcript(
                session,
                row,
                [SegmentResult(1.0, 5.0, "[HIGHLIGHT] opening words")],
            )
        finally:
            session.close()
        run_job(client, video["id"], "analyze_events")
        run_job(client, video["id"], "generate_candidates")

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"selection": "all"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        candidate = client.get(f"/api/videos/{video['id']}/candidates").json()[0]
        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        plan = clip["editing_plan"]
        trim_record = plan["trim"]

        # The 12s narration is silent in its second half, so the padded tail
        # (candidate end = video end) is pulled back to the speech edge, either
        # by the silence run or by the beyond-tolerance sentence fallback.
        assert trim_record["applied"] is True
        assert trim_record["original_end"] == pytest.approx(candidate["end_seconds"], abs=0.01)
        assert clip["end_seconds"] < trim_record["original_end"]
        assert clip["end_seconds"] <= 8.6  # speech ends at 5s; some tail may remain
        assert clip["end_seconds"] > 4.8  # the closing sentence is not cut short
        assert trim_record["silence_removed_seconds"] > 1.0
        assert clip["duration_seconds"] == pytest.approx(
            clip["end_seconds"] - clip["start_seconds"], abs=0.01
        )
