"""Tests for caption intelligence: keyword emphasis and auto timing (roadmap 12.3)."""

from __future__ import annotations

from app.editing.caption_emphasis import STOPWORDS, detect_emphasis, emphasize_text
from app.editing.captions import (
    ASS_COLOR_EMPHASIS,
    CaptionCue,
    build_ass,
    style_for_profile,
)
from app.editing.profiles import get_profile
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle


class TestDetectEmphasis:
    def test_prefers_all_caps_and_numbers(self) -> None:
        words = detect_emphasis("this is HUGE news about 2024 today", limit=2)

        assert words == ["HUGE", "2024"]

    def test_ignores_stopwords_and_short_words(self) -> None:
        words = detect_emphasis("the cat sat on the mat", limit=2)

        assert words == []

    def test_ties_resolve_to_first_appearance(self) -> None:
        words = detect_emphasis("amazing celebration", limit=1)

        assert words == ["amazing"]

    def test_repeated_words_appear_once(self) -> None:
        words = detect_emphasis("great work, great team", limit=1)

        assert words == ["great"]

    def test_zero_limit_disables_emphasis(self) -> None:
        assert detect_emphasis("HUGE moment", limit=0) == []

    def test_stopword_table_is_not_empty(self) -> None:
        assert "the" in STOPWORDS and "and" in STOPWORDS


class TestEmphasizeText:
    def test_wraps_whole_words_with_override_tags(self) -> None:
        marked = emphasize_text(
            "a HUGE moment",
            ["HUGE"],
            color=ASS_COLOR_EMPHASIS,
            scale=115,
            reset_color="&H00FFFFFF",
        )

        assert marked == (
            "a {\\c&H0000D5FF\\fscx115\\fscy115}HUGE{\\c&H00FFFFFF\\fscx100\\fscy100} moment"
        )

    def test_matching_is_case_insensitive_and_whole_word(self) -> None:
        marked = emphasize_text("huge monstrous", ["HUGE"], color="X", scale=110, reset_color="Y")

        assert "{\\cX" in marked.split(" ")[0]
        assert marked.endswith("monstrous")

    def test_no_words_is_a_noop(self) -> None:
        assert emphasize_text("plain text", [], color="X", scale=110, reset_color="Y") == (
            "plain text"
        )


class TestBuildAssEmphasis:
    def test_emphasised_cue_carries_override_tags(self) -> None:
        ass = build_ass(
            [CaptionCue(0.0, 2.0, "HUGE moment")],
            style_for_profile(get_profile("shorts")),
            emphases={0: ["HUGE"]},
        )

        assert "{\\c&H0000D5FF\\fscx115\\fscy115}HUGE" in ass

    def test_cues_without_emphasis_are_untouched(self) -> None:
        ass = build_ass(
            [CaptionCue(0.0, 2.0, "plain line")],
            style_for_profile(get_profile("shorts")),
            emphases={1: ["ignored"]},
        )

        assert "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,plain line" in ass


class TestAutoTiming:
    def test_long_cues_split_at_word_boundaries(self) -> None:
        from app.editing.captions import split_cues

        cues = split_cues(
            [CaptionCue(0.0, 10.0, "one two three four five six seven eight")],
            max_words=3,
        )

        assert [cue.text for cue in cues] == [
            "one two three",
            "four five six",
            "seven eight",
        ]
        assert cues[0].start_seconds == 0.0
        assert cues[-1].end_seconds == 10.0

    def test_short_cues_are_left_alone(self) -> None:
        from app.editing.captions import split_cues

        cue = CaptionCue(0.0, 2.0, "short line")
        assert split_cues([cue], max_words=6) == [cue]

    def test_zero_max_words_disables_splitting(self) -> None:
        from app.editing.captions import split_cues

        cue = CaptionCue(0.0, 2.0, "one two three four five six seven")
        assert split_cues([cue], max_words=0) == [cue]

    def test_split_times_stay_ordered_within_the_cue(self) -> None:
        from app.editing.captions import split_cues

        cues = split_cues([CaptionCue(0.0, 9.0, "alpha beta gamma delta epsilon")], max_words=2)

        times = [cue.start_seconds for cue in cues] + [cues[-1].end_seconds]
        assert times == sorted(times)
        assert cues[0].start_seconds == 0.0


@requires_ffmpeg
class TestCaptionIntelligenceThroughApi:
    def test_shorts_clip_records_emphasis_words(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        emphasis = clip["editing_plan"]["caption_emphasis"]
        assert emphasis["style"] == "vertical"
        assert emphasis["word_count"] >= 1
        assert "highlight" in emphasis["words"]

    def test_clean_clip_has_no_emphasis_record(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert "caption_emphasis" not in clip["editing_plan"]
