"""Dynamic zoom (roadmap 12.2).

Detect emphasis moments inside a clip and apply a subtle punch-in zoom around
each one. Emphasis comes from the deterministic analysis events (audio spikes —
loud transients above the peak threshold); each spike becomes a short, smooth
triangular zoom pulse.

The rendered effect uses FFmpeg's ``zoompan`` filter (a per-frame zoom
expression over the input frame count); the pulses and the resulting filter are
recorded on the plan so the render is reproducible (guide §21/§24). The zoom is
applied to the already-framed frame, so it magnifies the target composition.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.editing.profiles import EditingProfile

# Below this the pulse is effectively invisible; also used to merge pulses.
_MIN_PULSE_SECONDS = 0.2


@dataclass(frozen=True)
class ZoomPulse:
    """A single punch-in: clip-relative span plus its peak magnification."""

    start_seconds: float
    end_seconds: float
    scale: float


@dataclass(frozen=True)
class ZoomPlan:
    """Resolved dynamic zoom for a clip."""

    target_width: int
    target_height: int
    fps: float
    scale: float
    pulses: tuple[ZoomPulse, ...]

    def filter_chain(self) -> str:
        """``zoompan`` filter applying the pulses, centered on the frame."""
        expr = _zoom_expression(self.pulses, self.fps, self.scale)
        return (
            f"zoompan=z='{expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={self.target_width}x{self.target_height}:fps={self.fps:.5f}"
        )

    def to_dict(self) -> dict:
        """JSON-serialisable record stored on the editing plan."""
        return {
            "scale": round(self.scale, 4),
            "fps": round(self.fps, 3),
            "target_width": self.target_width,
            "target_height": self.target_height,
            "pulses": [
                [round(pulse.start_seconds, 3), round(pulse.end_seconds, 3), round(pulse.scale, 4)]
                for pulse in self.pulses
            ],
            "filter": self.filter_chain(),
        }


def zoom_plan(
    profile: EditingProfile,
    *,
    emphasis_times: list[float],
    start_seconds: float,
    end_seconds: float,
    target_width: int | None,
    target_height: int | None,
    fps: float | None,
    scale: float,
    lead_seconds: float,
    hold_seconds: float,
    max_pulses: int,
) -> ZoomPlan | None:
    """Resolve a dynamic zoom plan, or ``None`` when there is nothing to zoom.

    Returns ``None`` when the profile has no zoom, the target size/fps are
    unknown, or no emphasis moment falls inside the clip.
    """
    if not profile.zoom or target_width is None or target_height is None or not fps:
        return None
    duration = max(end_seconds - start_seconds, 0.0)
    if duration <= 0:
        return None

    spans: list[tuple[float, float]] = []
    for moment in sorted(emphasis_times):
        if moment < start_seconds or moment > end_seconds:
            continue
        begin = max(moment - lead_seconds, start_seconds) - start_seconds
        finish = min(moment + hold_seconds, end_seconds) - start_seconds
        if finish - begin < _MIN_PULSE_SECONDS:
            continue
        spans.append((begin, finish))

    merged = _merge(spans)[:max_pulses]
    if not merged:
        return None
    return ZoomPlan(
        target_width=target_width,
        target_height=target_height,
        fps=fps,
        scale=scale,
        pulses=tuple(
            ZoomPulse(start_seconds=begin, end_seconds=finish, scale=scale)
            for begin, finish in merged
        ),
    )


def _merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge overlapping/adjacent spans into a sorted disjoint list."""
    merged: list[list[float]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(span[0], span[1]) for span in merged]


def _zoom_expression(pulses: tuple[ZoomPulse, ...], fps: float, peak: float) -> str:
    """Nested ``if`` of triangular zoom pulses over the frame number.

    ``zoompan`` exposes the input frame count (``in``), not time, so time is
    reconstructed as ``in / fps``. Outside every pulse the zoom is exactly 1.
    """
    time = f"(in/{fps:.5f})"
    expr = "1"
    for pulse in reversed(pulses):
        mid = (pulse.start_seconds + pulse.end_seconds) / 2
        half = max((pulse.end_seconds - pulse.start_seconds) / 2, 0.001)
        ramp = f"(1+({peak:.4f}-1)*(1-abs(({time}-{mid:.3f})/{half:.3f})))"
        expr = (
            f"if(between({time},{pulse.start_seconds:.3f},{pulse.end_seconds:.3f}),{ramp},{expr})"
        )
    return expr
