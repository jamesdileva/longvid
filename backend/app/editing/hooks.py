"""Hook detection (roadmap 12.4).

Find the strongest opening moment inside a clip so the clip opens on the most
engaging sentence rather than wherever the candidate window happened to start.
The strongest sentence becomes the hook; everything after it is context and
payoff.

Scoring is deterministic and reuses the caption keyword heuristics plus the
audio-spike emphasis moments: a sentence scores for its important words, for
containing/being near an emphasis moment, and for being long enough to carry an
idea. The chosen hook is snapshotted on the editing plan; applying it simply
moves the clip start to that sentence's natural boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.editing.caption_emphasis import detect_emphasis
from app.editing.profiles import EditingProfile

Segments = list[tuple[float, float, str]]


@dataclass(frozen=True)
class HookPlan:
    """The detected opening hook for a clip."""

    hook_start_seconds: float
    hook_end_seconds: float
    hook_text: str
    original_start_seconds: float
    score: float
    applied: bool

    @property
    def skipped_seconds(self) -> float:
        """How much of the original opening was skipped to reach the hook."""
        return max(self.hook_start_seconds - self.original_start_seconds, 0.0)

    def to_dict(self) -> dict:
        """JSON-serialisable record stored on the editing plan."""
        return {
            "applied": self.applied,
            "hook_start_seconds": round(self.hook_start_seconds, 3),
            "hook_end_seconds": round(self.hook_end_seconds, 3),
            "hook_text": self.hook_text,
            "original_start_seconds": round(self.original_start_seconds, 3),
            "skipped_seconds": round(self.skipped_seconds, 3),
            "score": round(self.score, 3),
        }


def select_hook(
    profile: EditingProfile,
    *,
    segments: Segments,
    start_seconds: float,
    end_seconds: float,
    emphasis_times: list[float],
    min_opening_seconds: float,
    min_remaining_seconds: float,
    min_score: float,
    keyword_limit: int,
) -> HookPlan | None:
    """Pick the strongest sentence as the clip's opening, or ``None``.

    ``None`` when the profile does not use hooks, when there is no transcript,
    or when no sentence is strong enough. A plan with ``applied=False`` means
    the strongest sentence already opens the clip.
    """
    if not profile.hook or end_seconds <= start_seconds:
        return None

    best: tuple[float, float, float, str] | None = None
    for seg_start, seg_end, raw_text in sorted(segments):
        if seg_end <= start_seconds or seg_start >= end_seconds:
            continue
        text = " ".join(raw_text.split())
        if not text:
            continue
        score = _score(text, seg_start, seg_end, emphasis_times, keyword_limit)
        eligible = seg_start <= end_seconds - min_remaining_seconds and seg_end > start_seconds
        if not eligible:
            continue
        # Prefer the highest score; ties keep the earliest sentence.
        if best is None or score > best[2]:
            best = (seg_start, seg_end, score, text)

    if best is None or best[2] < min_score:
        return None
    hook_start, hook_end, score, text = best
    applied = hook_start > start_seconds + min_opening_seconds
    return HookPlan(
        hook_start_seconds=hook_start,
        hook_end_seconds=hook_end,
        hook_text=text,
        original_start_seconds=start_seconds,
        score=score,
        applied=applied,
    )


def _score(
    text: str,
    start_seconds: float,
    end_seconds: float,
    emphasis_times: list[float],
    keyword_limit: int,
) -> float:
    score = 0.0
    for word in detect_emphasis(text, limit=keyword_limit):
        if word.isupper() and len(word) > 1 or any(char.isdigit() for char in word):
            score += 2.0
        elif len(word) >= 7:
            score += 1.0
    if any(start_seconds - 0.5 <= moment <= end_seconds + 0.5 for moment in emphasis_times):
        score += 1.0
    if len(text.split()) >= 4:
        score += 0.5
    return score
