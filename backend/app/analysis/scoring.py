"""Candidate scoring (implementation-guide §16).

A weighted sum of six normalized signals; weights come from settings so the
balance can be tuned without code changes. All functions are pure.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic": 0.30,
    "audio": 0.15,
    "visual": 0.15,
    "context": 0.15,
    "standalone": 0.15,
    "novelty": 0.10,
}


@dataclass(frozen=True)
class CandidateSignals:
    """Normalized [0,1] signals describing a candidate."""

    semantic: float = 0.0
    audio: float = 0.0
    visual: float = 0.0
    context: float = 0.0
    standalone: float = 0.0
    novelty: float = 1.0


def score_candidate(signals: CandidateSignals, weights: dict[str, float]) -> float:
    """Weighted score in [0,1]. Unknown weight keys are ignored."""
    values = {
        "semantic": signals.semantic,
        "audio": signals.audio,
        "visual": signals.visual,
        "context": signals.context,
        "standalone": signals.standalone,
        "novelty": signals.novelty,
    }
    total_weight = 0.0
    total = 0.0
    for key, weight in weights.items():
        if key not in values or weight <= 0:
            continue
        clamped = min(max(values[key], 0.0), 1.0)
        total += clamped * weight
        total_weight += weight
    if total_weight <= 0:
        return 0.0
    return round(min(total / total_weight, 1.0), 4)


def audio_signal(*, audio_event_count: int, speech_density: float) -> float:
    """Audio signal from event density and speech coverage."""
    event_component = min(audio_event_count / 3.0, 1.0)
    return clamp01(0.6 * min(speech_density, 1.0) + 0.4 * event_component)


def visual_signal(*, scene_change_count: int, duration_seconds: float) -> float:
    """Visual signal from scene-change frequency relative to duration."""
    if duration_seconds <= 0:
        return 0.0
    return clamp01(min((scene_change_count / duration_seconds) * 30.0, 1.0))


def context_signal(*, speech_coverage: float) -> float:
    """How much speech surrounds the window (0-1 transcript coverage)."""
    return clamp01(speech_coverage)


def standalone_signal(
    *,
    speech_coverage: float,
    starts_on_silence: bool,
    ends_on_silence: bool,
    duration_seconds: float,
    min_seconds: float,
    max_seconds: float,
) -> float:
    """Standalone watchability: speech-heavy, clean cuts, sane duration.

    Component weights sum to 1.0 so distinct combinations stay distinguishable.
    """
    coverage = 0.3 * clamp01(speech_coverage)
    cuts = (0.15 if starts_on_silence else 0.0) + (0.15 if ends_on_silence else 0.0)
    duration = 0.4 * _duration_fit(duration_seconds, min_seconds, max_seconds)
    return clamp01(coverage + cuts + duration)


def novelty_signal(overlap_with_selected: float) -> float:
    """Novelty penalty: 1.0 means no overlap with already-picked candidates."""
    return clamp01(1.0 - overlap_with_selected)


def clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _duration_fit(duration: float, min_seconds: float, max_seconds: float) -> float:
    if duration <= 0:
        return 0.0
    if duration < min_seconds:
        return duration / min_seconds
    if duration > max_seconds:
        return max(max_seconds / duration, 0.0)
    return 1.0
