"""Semantic windowing (implementation-guide §17).

Groups transcript segments (split at scene boundaries) into bounded windows
and attaches the audio events and scenes that overlap them, producing the
compact structured text the LLM classifies — never raw video.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_TRANSCRIPT_CHARS = 4000


@dataclass(frozen=True)
class WindowEvent:
    """A compact event descriptor attached to a window."""

    type: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None


@dataclass(frozen=True)
class SemanticWindow:
    """One analysis window with everything the model needs."""

    start_seconds: float
    end_seconds: float
    transcript: str
    events: list[WindowEvent] = field(default_factory=list)
    scene_count: int = 0

    def render_prompt(self, guidance: str | None = None) -> str:
        """The structured prompt text sent to the LLM.

        ``guidance`` is the selected content profile's focus (roadmap Phase 13);
        it steers what counts as a highlight without changing the window data.
        """
        lines = [
            "VIDEO WINDOW",
            f"Start: {_format_clock(self.start_seconds)}",
            f"End:   {_format_clock(self.end_seconds)}",
            "",
            "Transcript:",
            self.transcript or "(no transcript)",
            "",
            "Audio/scene events:",
        ]
        if self.events:
            lines.extend(
                f"- {event.type} at {_format_clock(event.start_seconds)}"
                + (f" (confidence {event.confidence:.2f})" if event.confidence is not None else "")
                for event in self.events
            )
        else:
            lines.append("- none detected")
        lines.extend(
            [
                "",
                f"Scene changes in window: {self.scene_count}",
            ]
        )
        if guidance:
            lines.extend(["", "Content focus:", guidance])
        lines.extend(["", "Is this a highlight worth clipping?"])
        return "\n".join(lines)


def build_windows(
    segments: list[tuple[float, float, str]],
    events: list[WindowEvent],
    *,
    duration_seconds: float,
    window_seconds: float,
    scene_boundaries: list[float] | None = None,
) -> list[SemanticWindow]:
    """Group transcript segments into windows, splitting at scene boundaries.

    ``segments`` are (start, end, text); ``events`` overlap-test against the
    window. Windows without any transcript text are skipped — nothing to
    judge semantically.
    """
    if duration_seconds <= 0 or not segments:
        return []

    ordered = sorted(segments, key=lambda segment: segment[0])
    cuts = [boundary for boundary in (scene_boundaries or []) if 0 < boundary < duration_seconds]

    windows: list[SemanticWindow] = []
    current_start = 0.0
    current: list[tuple[float, float, str]] = []

    def flush(end: float) -> None:
        nonlocal current, current_start
        if current:
            text = "\n".join(
                f"[{_format_clock(start)}] {text_line}" for start, _end, text_line in current
            )
            windows.append(
                SemanticWindow(
                    start_seconds=round(current_start, 3),
                    end_seconds=round(end, 3),
                    transcript=text[:MAX_TRANSCRIPT_CHARS],
                    events=_events_between(events, current_start, end),
                    scene_count=_count_cuts(cuts, current_start, end),
                )
            )
        current = []
        current_start = end

    for start, end, text in ordered:
        # Start a new window when crossing a scene boundary, the time budget,
        # or a transcript gap.
        if current and (
            any(current_start < cut <= start for cut in cuts)
            or start - current_start >= window_seconds
        ):
            flush(min(start, duration_seconds))
        current.append((start, end, text))
    flush(min(ordered[-1][1], duration_seconds) if ordered else duration_seconds)
    return windows


def _events_between(events: list[WindowEvent], start: float, end: float) -> list[WindowEvent]:
    return [event for event in events if event.start_seconds < end and event.end_seconds >= start]


def _count_cuts(cuts: list[float], start: float, end: float) -> int:
    return sum(1 for cut in cuts if start < cut < end)


def _format_clock(seconds: float) -> str:
    total = max(int(seconds), 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
