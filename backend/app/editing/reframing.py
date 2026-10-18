"""Dynamic (subject-following) crop (roadmap 11.3).

Given a static :class:`~app.editing.framing.Framing` (crop size) and a subject
track, build a smooth camera path: the crop window follows the subject's
horizontal/vertical position over the clip, clamped to the frame and smoothed
(and decimated to a bounded number of waypoints) so the movement reads as a
gentle pan rather than a jitter.

The result is a pure FFmpeg ``crop`` expression over time, then the usual
``scale``/``setsar`` — recorded in the plan so the render is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.editing.framing import Framing, framing_plan
from app.editing.profiles import EditingProfile
from app.providers.vision import SubjectSample, SubjectTrack

# Ignore sub-pixel drift: below this the crop is effectively static.
_MOVEMENT_EPSILON = 1.0


@dataclass(frozen=True)
class DynamicFraming:
    """A subject-following crop defined by time-stamped crop top-left corners."""

    target_width: int
    target_height: int
    crop_width: int
    crop_height: int
    keyframes: tuple[tuple[float, float, float], ...]

    def filter_chain(self) -> str:
        """``crop`` with time expressions, then scale and square pixels."""
        times = [keyframe[0] for keyframe in self.keyframes]
        xs = [keyframe[1] for keyframe in self.keyframes]
        ys = [keyframe[2] for keyframe in self.keyframes]
        return (
            f"crop={self.crop_width}:{self.crop_height}:'{_axis_expr(times, xs)}':"
            f"'{_axis_expr(times, ys)}',scale={self.target_width}:{self.target_height},setsar=1"
        )

    def to_dict(self) -> dict:
        return {
            "target_width": self.target_width,
            "target_height": self.target_height,
            "crop_width": self.crop_width,
            "crop_height": self.crop_height,
            "dynamic": True,
            "keyframes": [list(keyframe) for keyframe in self.keyframes],
            "filter": self.filter_chain(),
        }


def dynamic_framing(
    profile: EditingProfile,
    *,
    source_width: int | None,
    source_height: int | None,
    track: SubjectTrack,
    start_seconds: float,
    end_seconds: float,
    smooth_window_seconds: float,
    max_keyframes: int,
) -> DynamicFraming | None:
    """Resolve a subject-following crop, or ``None`` to use a static crop.

    Returns ``None`` when the profile needs no reframing, the track has no
    samples in the clip range, or the subject barely moves.
    """
    base = framing_plan(profile, source_width=source_width, source_height=source_height)
    if base is None or source_width is None or source_height is None:
        return None

    samples = [
        sample
        for sample in track.samples
        if start_seconds - 0.001 <= sample.time_seconds <= end_seconds + 0.001
    ]
    if not samples:
        return None

    points = [
        _point(base, sample.time_seconds - start_seconds, source_width, source_height, sample)
        for sample in samples
    ]
    smoothed = _smooth(points, smooth_window_seconds)
    keyframes = _decimate(smoothed, max_keyframes)
    if len(keyframes) < 2 or not _moves(keyframes):
        return None

    return DynamicFraming(
        target_width=base.target_width,
        target_height=base.target_height,
        crop_width=base.crop_width,
        crop_height=base.crop_height,
        keyframes=tuple(keyframes),
    )


def _point(
    base: Framing,
    time_seconds: float,
    source_width: int,
    source_height: int,
    sample: SubjectSample,
) -> tuple[float, float, float]:
    x = _clamp(
        sample.x_center * source_width - base.crop_width / 2, 0, source_width - base.crop_width
    )
    y = _clamp(
        sample.y_center * source_height - base.crop_height / 2, 0, source_height - base.crop_height
    )
    return (max(time_seconds, 0.0), x, y)


def _smooth(
    points: list[tuple[float, float, float]], window_seconds: float
) -> list[tuple[float, float, float]]:
    """Box-average the crop position over a symmetric time window."""
    smoothed: list[tuple[float, float, float]] = []
    for time, _, _ in points:
        near = [p for p in points if abs(p[0] - time) <= window_seconds / 2]
        x = sum(p[1] for p in near) / len(near)
        y = sum(p[2] for p in near) / len(near)
        smoothed.append((time, x, y))
    return smoothed


def _decimate(points: list[tuple], max_keyframes: int) -> list[tuple]:
    """Reduce to at most ``max_keyframes`` evenly spaced waypoints (keep ends)."""
    if max_keyframes < 2 or len(points) <= max_keyframes:
        return points
    last = len(points) - 1
    indices = sorted({round(i * last / (max_keyframes - 1)) for i in range(max_keyframes)})
    return [points[index] for index in indices]


def _moves(keyframes: list[tuple]) -> bool:
    xs = [keyframe[1] for keyframe in keyframes]
    ys = [keyframe[2] for keyframe in keyframes]
    return max(xs) - min(xs) > _MOVEMENT_EPSILON or max(ys) - min(ys) > _MOVEMENT_EPSILON


def _axis_expr(times: list[float], values: list[float]) -> str:
    """Piecewise-linear FFmpeg expression of ``value(t)``."""
    expr = f"{values[-1]:.3f}"
    for i in range(len(times) - 2, -1, -1):
        t0, t1 = times[i], times[i + 1]
        v0, v1 = values[i], values[i + 1]
        span = max(t1 - t0, 0.001)
        segment = f"({v0:.3f}+({v1:.3f}-{v0:.3f})*(t-{t0:.3f})/{span:.3f})"
        expr = f"if(lt(t,{t1:.3f}),{segment},{expr})"
    return f"if(lt(t,{times[0]:.3f}),{values[0]:.3f},{expr})"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
