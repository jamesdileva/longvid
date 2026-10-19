"""Pacing (roadmap 12.1).

Analyze a clip's speech density, dead air and scene-change rate, then decide how
tightly to pace it. Profiles carry a pacing *style*:

* ``relaxed``  - no tightening (leave the natural cut alone).
* ``standard`` - cut clearly dead air (silence runs >= 1.2s), keep 0.25s breathing room.
* ``punchy``   - cut aggressively (runs >= 0.6s), keep 0.15s breathing room.

The decision is pure and deterministic. When runs are cut, the module also
builds the matching FFmpeg ``select``/``setpts`` (video) and
``aselect``/``asetpts`` (audio) filter strings that remove those spans and
compact the timeline, so the render stays reproducible from the plan (§21/§24).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.editing.profiles import EditingProfile

# Transcript segments as (start, end, text); silence runs as (start, end).
Segments = list[tuple[float, float, str]]
Silences = list[tuple[float, float]]

PACING_STYLES = ("relaxed", "standard", "punchy")

# style -> (min dead-air run seconds, breathing room kept on each side), or None.
_STYLE_PACING: dict[str, tuple[float, float] | None] = {
    "relaxed": None,
    "standard": (1.2, 0.25),
    "punchy": (0.6, 0.15),
}


@dataclass(frozen=True)
class PacingDecision:
    """Pacing analysis plus the spans to remove (clip-relative)."""

    style: str
    speech_ratio: float
    silence_ratio: float
    scene_changes_per_minute: float
    dead_air_runs: tuple[tuple[float, float], ...]
    silence_removed_seconds: float

    @property
    def applied(self) -> bool:
        """True when at least one dead-air span is being cut."""
        return bool(self.dead_air_runs)

    def video_filter(self) -> str | None:
        """FFmpeg video filter that drops the dead-air spans, or ``None``."""
        condition = self._condition()
        if condition is None:
            return None
        return f"select='not({condition})',setpts=N/FRAME_RATE/TB"

    def audio_filter(self) -> str | None:
        """FFmpeg audio filter that drops the dead-air spans, or ``None``."""
        condition = self._condition()
        if condition is None:
            return None
        return f"aselect='not({condition})',asetpts=N/SR/TB"

    def to_dict(self) -> dict:
        """JSON-serialisable record stored on the editing plan."""
        return {
            "style": self.style,
            "speech_ratio": round(self.speech_ratio, 3),
            "silence_ratio": round(self.silence_ratio, 3),
            "scene_changes_per_minute": round(self.scene_changes_per_minute, 2),
            "dead_air_runs": [
                [round(start, 3), round(end, 3)] for start, end in self.dead_air_runs
            ],
            "silence_removed_seconds": round(self.silence_removed_seconds, 3),
            "applied": self.applied,
            "video_filter": self.video_filter(),
            "audio_filter": self.audio_filter(),
        }

    def _condition(self) -> str | None:
        if not self.dead_air_runs:
            return None
        return "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in self.dead_air_runs)


def pacing_plan(
    profile: EditingProfile,
    *,
    start_seconds: float,
    end_seconds: float,
    segments: Segments = (),
    silences: Silences = (),
    scene_times: list[float] | None = None,
    max_removed_ratio: float,
) -> PacingDecision | None:
    """Resolve the pacing decision for a clip range, or ``None`` when relaxed.

    ``segments``/``silences`` are absolute source times; the returned dead-air
    spans are clip-relative. Total removal is capped at ``max_removed_ratio`` of
    the clip duration so pacing never guts the clip.
    """
    settings = _STYLE_PACING.get(profile.pacing)
    if settings is None:
        return None

    duration = max(end_seconds - start_seconds, 0.0)
    speech_time = _overlap_total(segments, start_seconds, end_seconds)
    silence_time = _overlap_total(silences, start_seconds, end_seconds)
    scene_count = sum(1 for moment in (scene_times or []) if start_seconds < moment < end_seconds)
    speech_ratio = speech_time / duration if duration > 0 else 0.0
    silence_ratio = silence_time / duration if duration > 0 else 0.0
    scene_rate = (scene_count / duration * 60.0) if duration > 0 else 0.0

    min_silence, keep = settings
    runs = _dead_air_runs(
        silences,
        start_seconds,
        end_seconds,
        min_silence=min_silence,
        keep=keep,
        budget=max_removed_ratio * duration,
    )
    removed = sum(run_end - run_start for run_start, run_end in runs)
    return PacingDecision(
        style=profile.pacing,
        speech_ratio=speech_ratio,
        silence_ratio=silence_ratio,
        scene_changes_per_minute=scene_rate,
        dead_air_runs=tuple(runs),
        silence_removed_seconds=removed,
    )


def _dead_air_runs(
    silences: Silences,
    start: float,
    end: float,
    *,
    min_silence: float,
    keep: float,
    budget: float,
) -> list[tuple[float, float]]:
    """Clip-relative spans to remove, in order, within the removal budget.

    Silence runs come from the low-threshold RMS detector, so a run means the
    audio is genuinely below the silence floor — transcript segmentation (which
    is contiguous) is deliberately not used to veto a cut.
    """
    runs: list[tuple[float, float]] = []
    removed = 0.0
    for run_start, run_end in sorted(silences):
        begin = max(run_start, start)
        finish = min(run_end, end)
        if finish - begin < min_silence:
            continue
        span_start = begin + keep
        span_end = finish - keep
        length = span_end - span_start
        if length <= 0 or removed + length > budget:
            continue
        runs.append((span_start - start, span_end - start))
        removed += length
    return runs


def _overlap_total(spans: Silences | Segments, start: float, end: float) -> float:
    """Total overlap of ``(start, end)`` spans with the clip range."""
    total = 0.0
    for span_start, span_end, *_ in spans:
        total += max(min(span_end, end) - max(span_start, start), 0.0)
    return total
