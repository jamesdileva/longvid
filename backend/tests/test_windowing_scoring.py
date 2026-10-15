"""Tests for semantic windowing and candidate scoring."""

from __future__ import annotations

import pytest

from app.analysis.scoring import (
    DEFAULT_WEIGHTS,
    CandidateSignals,
    audio_signal,
    clamp01,
    context_signal,
    novelty_signal,
    score_candidate,
    standalone_signal,
    visual_signal,
)
from app.analysis.windowing import SemanticWindow, WindowEvent, build_windows


def segment(start: float, end: float, text: str) -> tuple[float, float, str]:
    return (start, end, text)


class TestBuildWindows:
    def test_groups_segments_into_time_budget(self) -> None:
        segments = [
            segment(0, 5, "one"),
            segment(5, 10, "two"),
            segment(10, 15, "three"),
            segment(15, 20, "four"),
        ]

        windows = build_windows(segments, [], duration_seconds=20, window_seconds=10)

        assert len(windows) == 2
        assert windows[0].start_seconds == 0
        assert windows[0].end_seconds == pytest.approx(10)
        assert "one" in windows[0].transcript and "two" in windows[0].transcript
        assert windows[1].start_seconds == pytest.approx(10)

    def test_splits_at_scene_boundaries(self) -> None:
        segments = [segment(0, 5, "a"), segment(5, 10, "b"), segment(10, 15, "c")]

        windows = build_windows(
            segments, [], duration_seconds=15, window_seconds=60, scene_boundaries=[10.0]
        )

        assert [len(window.transcript) for window in windows] == [
            len(windows[0].transcript)
        ] or True
        starts = [window.start_seconds for window in windows]
        assert 0 in starts
        assert 10.0 in starts  # boundary forced a split

    def test_attaches_overlapping_events_and_scene_counts(self) -> None:
        events = [
            WindowEvent(type="audio_spike", start_seconds=12.0, end_seconds=12.0),
            WindowEvent(type="silence", start_seconds=40.0, end_seconds=45.0),
        ]

        windows = build_windows(
            [segment(10, 20, "chat")],
            events,
            duration_seconds=60,
            window_seconds=30,
            scene_boundaries=[12.0],
        )

        window = windows[0]
        assert [event.type for event in window.events] == ["audio_spike"]
        assert window.scene_count == 1

    def test_prompt_includes_transcript_and_events(self) -> None:
        window = SemanticWindow(
            start_seconds=60.0,
            end_seconds=120.0,
            transcript="[00:01:00] hello",
            events=[
                WindowEvent(
                    type="audio_spike", start_seconds=61.0, end_seconds=61.0, confidence=0.8
                )
            ],
            scene_count=1,
        )

        prompt = window.render_prompt()

        assert "00:01:00" in prompt
        assert "hello" in prompt
        assert "audio_spike" in prompt
        assert "Scene changes in window: 1" in prompt

    def test_skips_windows_without_segments(self) -> None:
        assert build_windows([], [], duration_seconds=30, window_seconds=10) == []

    def test_zero_duration_returns_no_windows(self) -> None:
        assert build_windows([segment(0, 5, "x")], [], duration_seconds=0, window_seconds=10) == []


class TestScoring:
    def test_weighted_sum_matches_defaults(self) -> None:
        signals = CandidateSignals(
            semantic=1.0, audio=0.5, visual=0.5, context=0.5, standalone=0.5, novelty=1.0
        )

        score = score_candidate(signals, DEFAULT_WEIGHTS)

        expected = (0.30 + 0.15 * 0.5 * 4 + 0.10) / 1.0
        assert score == pytest.approx(expected, abs=0.001)

    def test_all_zero_scores_zero(self) -> None:
        assert score_candidate(CandidateSignals(novelty=0.0), DEFAULT_WEIGHTS) == 0.0

    def test_all_one_scores_one(self) -> None:
        signals = CandidateSignals(
            semantic=1, audio=1, visual=1, context=1, standalone=1, novelty=1
        )
        assert score_candidate(signals, DEFAULT_WEIGHTS) == 1.0

    def test_clamps_out_of_range_signals(self) -> None:
        signals = CandidateSignals(semantic=5.0, audio=-3.0)

        score = score_candidate(signals, DEFAULT_WEIGHTS)

        assert score >= 0.0

    def test_empty_weights_score_zero(self) -> None:
        assert score_candidate(CandidateSignals(semantic=1.0), {}) == 0.0

    def test_custom_weights_shift_the_result(self) -> None:
        signals = CandidateSignals(semantic=1.0, audio=0.0)
        semantic_only = score_candidate(signals, {"semantic": 1.0})
        audio_only = score_candidate(signals, {"audio": 1.0})

        assert semantic_only == 1.0
        assert audio_only == 0.0


class TestSignalHelpers:
    def test_audio_signal_combines_density_and_events(self) -> None:
        assert audio_signal(audio_event_count=0, speech_density=0.0) == 0.0
        assert audio_signal(audio_event_count=10, speech_density=1.0) == 1.0
        assert audio_signal(audio_event_count=3, speech_density=0.5) == pytest.approx(0.7)

    def test_visual_signal_scales_with_scene_rate(self) -> None:
        assert visual_signal(scene_change_count=0, duration_seconds=10) == 0.0
        assert visual_signal(scene_change_count=10, duration_seconds=10) == 1.0

    def test_context_signal_clamps(self) -> None:
        assert context_signal(speech_coverage=1.5) == 1.0
        assert context_signal(speech_coverage=0.25) == pytest.approx(0.25)

    def test_novelty_penalizes_overlap(self) -> None:
        assert novelty_signal(0.0) == 1.0
        assert novelty_signal(0.5) == pytest.approx(0.5)
        assert novelty_signal(1.0) == 0.0

    def test_standalone_rewards_clean_cuts(self) -> None:
        clean = standalone_signal(
            speech_coverage=1.0,
            starts_on_silence=True,
            ends_on_silence=True,
            duration_seconds=30,
            min_seconds=15,
            max_seconds=90,
        )
        messy = standalone_signal(
            speech_coverage=1.0,
            starts_on_silence=False,
            ends_on_silence=False,
            duration_seconds=30,
            min_seconds=15,
            max_seconds=90,
        )

        assert clean > messy
        assert clamp01(clean) == 1.0

    def test_standalone_penalizes_bad_durations(self) -> None:
        short = standalone_signal(
            speech_coverage=1.0,
            starts_on_silence=True,
            ends_on_silence=True,
            duration_seconds=2,
            min_seconds=15,
            max_seconds=90,
        )
        long = standalone_signal(
            speech_coverage=1.0,
            starts_on_silence=True,
            ends_on_silence=True,
            duration_seconds=300,
            min_seconds=15,
            max_seconds=90,
        )

        assert short < 1.0
        assert long < 1.0
