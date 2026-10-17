"""Automatic trimming (roadmap 10.2).

Refines a candidate's padded range into a clip range that respects natural
boundaries:

* **Sentence boundaries** — if a boundary cuts a transcript sentence, snap it
  to the sentence start/end so clips neither open nor close mid-sentence
  (within a tolerance; a far-away boundary is kept as-is).
* **Silence removal** — if a boundary sits inside a detected silence run
  (dead air from the coarse padding), pull it toward the speech edge and keep
  only the configured pre/post-roll as breathing room.

The function is pure and deterministic so the trimming decision can be
snapshotted into the clip's editing plan (§21/§24) and replayed.
"""

from __future__ import annotations

from dataclasses import dataclass

# Transcript segments as (start, end, text); silence runs as (start, end).
Segments = list[tuple[float, float, str]]
Silences = list[tuple[float, float]]

# Silence runs come from sampled audio levels, so a run that reaches the end of
# the video usually stops one sampling step short of the actual final moment.
# A boundary just past a run's closing edge is still treated as inside it.
_SILENCE_EDGE_TOLERANCE_SECONDS = 0.25


@dataclass(frozen=True)
class TrimResult:
    """The trimmed range plus the record stored on the editing plan."""

    start_seconds: float
    end_seconds: float
    trim: dict


def trim_clip_range(
    start: float,
    end: float,
    *,
    segments: Segments,
    silences: Silences,
    duration: float,
    sentence_tolerance: float,
    pre_roll: float,
    post_roll: float,
) -> TrimResult:
    """Trim ``[start, end]`` to natural sentence/silence boundaries."""
    original = (start, end)
    if end <= start:
        return TrimResult(start, end, _record(start, end, start, end, False, False))

    new_start, sentence_start = _trim_head(
        start, end, segments, silences, pre_roll, sentence_tolerance
    )
    new_end, sentence_end = _trim_tail(
        start, end, segments, silences, post_roll, sentence_tolerance
    )

    # Never cross the video bounds or collapse the range.
    if duration > 0:
        new_start = min(max(new_start, 0.0), duration)
        new_end = min(max(new_end, 0.0), duration)
    if new_end <= new_start:
        return TrimResult(start, end, _record(start, end, start, end, False, False))

    applied = (new_start, new_end) != original
    return TrimResult(
        new_start,
        new_end,
        _record(start, end, new_start, new_end, sentence_start, sentence_end, applied),
    )


def _trim_head(
    start: float,
    end: float,
    segments: Segments,
    silences: Silences,
    pre_roll: float,
    tolerance: float,
) -> tuple[float, bool]:
    """Return (new head boundary, snapped-to-sentence flag)."""
    speech_start = _first_speech_start(start, end, segments)
    if speech_start is not None and start > speech_start:
        # The boundary cut into the opening sentence — complete it if close.
        if start - speech_start <= tolerance:
            return speech_start, True
        return start, False
    # Padding landed before the speech: keep only pre-roll of the dead air.
    run = _silence_run_containing(silences, start)
    if run is not None:
        return max(run[0], run[1] - pre_roll), False
    if speech_start is not None and speech_start - start > tolerance:
        return speech_start, True
    return start, False


def _trim_tail(
    start: float,
    end: float,
    segments: Segments,
    silences: Silences,
    post_roll: float,
    tolerance: float,
) -> tuple[float, bool]:
    """Return (new tail boundary, snapped-to-sentence flag)."""
    speech_end = _last_speech_end(start, end, segments)
    if speech_end is not None and end < speech_end:
        # The boundary cut the closing sentence short — finish it if close.
        if speech_end - end <= tolerance:
            return speech_end, True
        return end, False
    # Padding landed past the speech: keep only post-roll of the dead air.
    # The end boundary may sit exactly on the next speech onset, so the run
    # lookup includes the run's closing edge here.
    run = _silence_run_containing(
        silences, end, include_end=True, epsilon=_SILENCE_EDGE_TOLERANCE_SECONDS
    )
    if run is not None:
        return min(run[1], run[0] + post_roll), False
    if speech_end is not None and end - speech_end > tolerance:
        return speech_end, True
    return end, False


def _first_speech_start(start: float, end: float, segments: Segments) -> float | None:
    """Start of the first transcript segment overlapping the range."""
    for seg_start, seg_end, _text in sorted(segments):
        if seg_end > start and seg_start < end:
            return seg_start
    return None


def _last_speech_end(start: float, end: float, segments: Segments) -> float | None:
    """End of the last transcript segment overlapping the range."""
    result: float | None = None
    for seg_start, seg_end, _text in sorted(segments):
        if seg_end > start and seg_start < end:
            result = seg_end
    return result


def _silence_run_containing(
    silences: Silences,
    moment: float,
    *,
    include_end: bool = False,
    epsilon: float = 0.0,
) -> tuple[float, float] | None:
    """The silence run that ``moment`` falls inside (or just past), if any.

    ``include_end`` also matches a moment sitting exactly on a run's closing
    edge; ``epsilon`` extends that closing edge by a fraction of a second to
    absorb audio-level sampling gaps.
    """
    for run_start, run_end in silences:
        upper = run_end + epsilon if include_end else run_end
        inside = run_start < moment <= upper if include_end else run_start <= moment < upper
        if inside:
            return (run_start, run_end)
    return None


def _record(
    original_start: float,
    original_end: float,
    new_start: float,
    new_end: float,
    sentence_start: bool,
    sentence_end: bool,
    applied: bool | None = None,
) -> dict:
    removed = max((original_end - original_start) - (new_end - new_start), 0.0)
    if applied is None:
        applied = (new_start, new_end) != (original_start, original_end)
    return {
        "applied": applied,
        "original_start": round(original_start, 3),
        "original_end": round(original_end, 3),
        "sentence_start": sentence_start,
        "sentence_end": sentence_end,
        "silence_removed_seconds": round(removed, 3),
    }
