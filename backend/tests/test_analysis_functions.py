"""Tests for the deterministic audio analysis functions (roadmap 6.2/6.4)."""

from __future__ import annotations

import pytest

from app.analysis.audio import (
    detect_peaks,
    detect_silence,
    rms_statistics,
    speech_density_windows,
)
from app.analysis.scenes import build_scenes
from app.services.ffmpeg_service import AudioLevel, SceneBoundary


def level(time: float, db: float) -> AudioLevel:
    return AudioLevel(time_seconds=time, rms_db=db)


def series(*pairs: tuple[float, float]) -> list[AudioLevel]:
    """Build a level series from (time, rms_db) pairs."""
    return [AudioLevel(time_seconds=time, rms_db=db) for time, db in pairs]


class TestDetectSilence:
    def test_finds_a_single_long_run(self) -> None:
        levels = series(
            (0.0, -30.0),
            (0.1, -32.0),
            (1.0, -60.0),
            (2.0, -70.0),
            (3.0, -65.0),
            (4.0, -28.0),
        )

        runs = detect_silence(levels, threshold_db=-45.0, min_seconds=1.5)

        assert len(runs) == 1
        assert runs[0].start_seconds == 1.0
        assert runs[0].end_seconds == pytest.approx(3.0)

    def test_ignores_short_runs(self) -> None:
        levels = series((0.0, -20.0), (0.2, -60.0), (0.4, -60.0), (0.6, -20.0))

        runs = detect_silence(levels, threshold_db=-45.0, min_seconds=1.5)

        assert runs == []

    def test_bridges_brief_dips_in_speech(self) -> None:
        # Quiet run with a 0.3s loud blip at t=1.3 must stay one run.
        levels = series(
            (0.0, -60.0),
            (0.5, -60.0),
            (1.0, -60.0),
            (1.3, -20.0),
            (1.6, -60.0),
            (2.0, -60.0),
            (2.5, -60.0),
        )

        runs = detect_silence(levels, threshold_db=-45.0, min_seconds=2.0)

        assert len(runs) == 1
        assert runs[0].start_seconds == pytest.approx(0.0)
        assert runs[0].end_seconds == pytest.approx(2.5)

    def test_empty_series_returns_nothing(self) -> None:
        assert detect_silence([], threshold_db=-45.0, min_seconds=1.0) == []

    def test_all_quiet_is_one_run(self) -> None:
        levels = series((0.0, -60.0), (5.0, -60.0))

        runs = detect_silence(levels, threshold_db=-45.0, min_seconds=1.0)

        assert len(runs) == 1
        assert runs[0].end_seconds == pytest.approx(5.0)


class TestDetectPeaks:
    def test_finds_local_max_above_threshold(self) -> None:
        levels = series((0.0, -20.0), (0.5, -3.0), (1.0, -20.0))

        peaks = detect_peaks(levels, threshold_db=-8.0)

        assert [p.time_seconds for p in peaks] == [0.5]

    def test_below_threshold_is_not_a_peak(self) -> None:
        levels = series((0.0, -20.0), (0.5, -12.0), (1.0, -20.0))

        assert detect_peaks(levels, threshold_db=-8.0) == []

    def test_ties_resolve_to_first_occurrence(self) -> None:
        levels = series((0.0, -5.0), (0.1, -5.0), (0.2, -5.0))

        peaks = detect_peaks(levels, threshold_db=-8.0, neighborhood_seconds=0.5)

        assert [p.time_seconds for p in peaks] == [0.0]

    def test_empty_series(self) -> None:
        assert detect_peaks([], threshold_db=-8.0) == []


class TestSpeechDensity:
    def test_computes_coverage_per_window(self) -> None:
        spans = [(0.0, 4.0), (12.0, 18.0)]

        windows = speech_density_windows(spans, total_duration=20.0, window_seconds=10.0)

        assert len(windows) == 2
        assert windows[0].density == pytest.approx(0.4)
        assert windows[1].density == pytest.approx(0.6)

    def test_window_count_and_final_partial_window(self) -> None:
        windows = speech_density_windows([(0.0, 12.0)], total_duration=12.0, window_seconds=10.0)

        assert len(windows) == 2
        assert windows[1].end_seconds == pytest.approx(12.0)
        assert windows[1].start_seconds == pytest.approx(10.0)

    def test_no_spans_means_zero_density(self) -> None:
        windows = speech_density_windows([], total_duration=10.0, window_seconds=10.0)

        assert windows[0].density == 0.0


class TestRmsStatistics:
    def test_summary_values(self) -> None:
        levels = series((0.0, -10.0), (1.0, -20.0), (2.0, -30.0))

        stats = rms_statistics(levels)

        assert stats["mean"] == pytest.approx(-20.0)
        assert stats["min"] == -30.0
        assert stats["max"] == -10.0

    def test_empty(self) -> None:
        assert rms_statistics([]) == {"mean": 0.0, "min": 0.0, "max": 0.0}


class TestBuildScenes:
    def test_single_scene_without_boundaries(self) -> None:
        scenes = build_scenes([], duration_seconds=10.0)

        assert scenes == [(0.0, 10.0, None)]

    def test_splits_on_boundaries(self) -> None:
        boundaries = [SceneBoundary(time_seconds=4.0, score=0.42)]

        scenes = build_scenes(boundaries, duration_seconds=10.0)

        assert scenes == [(0.0, 4.0, 0.42), (4.0, 10.0, None)]

    def test_deduplicates_and_ignores_out_of_range(self) -> None:
        boundaries = [
            SceneBoundary(time_seconds=2.0, score=0.5),
            SceneBoundary(time_seconds=2.0, score=0.9),
            SceneBoundary(time_seconds=-1.0, score=0.5),
            SceneBoundary(time_seconds=12.0, score=0.5),
        ]

        scenes = build_scenes(boundaries, duration_seconds=10.0)

        assert scenes == [(0.0, 2.0, 0.9), (2.0, 10.0, None)]

    def test_zero_duration(self) -> None:
        assert build_scenes([SceneBoundary(0.0, 0.5)], duration_seconds=0.0) == []
