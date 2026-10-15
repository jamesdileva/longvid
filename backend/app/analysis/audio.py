"""Deterministic audio analysis — pure functions over sampled levels (6.2/6.4).

All detectors are pure: given a level series and thresholds they return the
same result every time, which keeps them unit-testable without media.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from app.services.ffmpeg_service import AudioLevel


@dataclass(frozen=True)
class SilenceRun:
    """A contiguous stretch of audio below the silence threshold."""

    start_seconds: float
    end_seconds: float
    mean_rms_db: float


@dataclass(frozen=True)
class AudioPeak:
    """A local energy maximum above the peak threshold."""

    time_seconds: float
    rms_db: float


@dataclass(frozen=True)
class DensityWindow:
    """A fixed-length analysis window with its speech coverage."""

    start_seconds: float
    end_seconds: float
    density: float


def detect_silence(
    levels: list[AudioLevel],
    *,
    threshold_db: float,
    min_seconds: float,
    gap_tolerance_seconds: float = 0.75,
) -> list[SilenceRun]:
    """Find silence runs at least ``min_seconds`` long.

    Brief dips below the threshold inside speech are tolerated (bridged) so
    natural pauses don't fragment silence detection.
    """
    if not levels:
        return []

    runs: list[SilenceRun] = []
    quiet: list[AudioLevel] = []
    bridge: list[AudioLevel] = []

    def flush() -> None:
        nonlocal quiet, bridge
        if not quiet:
            bridge = []
            return
        start = quiet[0].time_seconds
        end = quiet[-1].time_seconds
        if end - start >= min_seconds:
            mean = sum(level.rms_db for level in quiet) / len(quiet)
            runs.append(SilenceRun(start_seconds=start, end_seconds=end, mean_rms_db=mean))
        quiet = []
        bridge = []

    for level in levels:
        if level.rms_db < threshold_db:
            quiet.append(level)
            bridge = []
        elif quiet and (level.time_seconds - quiet[-1].time_seconds) <= gap_tolerance_seconds:
            # short excursion — keep the run open
            bridge.append(level)
        else:
            if bridge:
                quiet.extend(bridge)
            flush()
    flush()
    return runs


def detect_peaks(
    levels: list[AudioLevel], *, threshold_db: float, neighborhood_seconds: float = 1.0
) -> list[AudioPeak]:
    """Find local RMS maxima at or above ``threshold_db``.

    A level is a peak when it is the maximum within +/-``neighborhood_seconds``
    (ties resolve to the first occurrence, so no duplicate peaks).
    """
    if not levels:
        return []
    times = [level.time_seconds for level in levels]
    peaks: list[AudioPeak] = []
    for index, level in enumerate(levels):
        if level.rms_db < threshold_db:
            continue
        low = bisect.bisect_left(times, level.time_seconds - neighborhood_seconds)
        high = bisect.bisect_right(times, level.time_seconds + neighborhood_seconds)
        window = levels[low:high]
        window_max = max(item.rms_db for item in window)
        if level.rms_db != window_max:
            continue
        first_index = low + next(
            offset for offset, item in enumerate(window) if item.rms_db == window_max
        )
        if first_index == index:
            peaks.append(AudioPeak(time_seconds=level.time_seconds, rms_db=level.rms_db))
    return peaks


def speech_density_windows(
    speech_spans: list[tuple[float, float]],
    *,
    total_duration: float,
    window_seconds: float,
) -> list[DensityWindow]:
    """Coverage of speech per fixed window across the video."""
    if total_duration <= 0:
        return []
    windows: list[DensityWindow] = []
    start = 0.0
    while start < total_duration:
        end = min(start + window_seconds, total_duration)
        overlap = sum(
            max(0.0, min(span_end, end) - max(span_start, start))
            for span_start, span_end in speech_spans
        )
        windows.append(
            DensityWindow(start_seconds=start, end_seconds=end, density=overlap / window_seconds)
        )
        start = end
    return windows


def rms_statistics(levels: list[AudioLevel]) -> dict[str, float]:
    """Summary statistics over the level series (dBFS)."""
    if not levels:
        return {"mean": 0.0, "min": 0.0, "max": 0.0}
    values = [level.rms_db for level in levels]
    return {"mean": sum(values) / len(values), "min": min(values), "max": max(values)}
