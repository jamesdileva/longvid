"""Deterministic synthetic vision provider (tests / offline development).

Produces a plausible subject that drifts horizontally across the frame so the
dynamic-crop path can be exercised without a detector or a model download.
"""

from __future__ import annotations

from pathlib import Path

from app.providers.vision.base import SubjectSample, SubjectTrack, VisionProvider


class SyntheticVisionProvider(VisionProvider):
    """Deterministic stand-in for real face/person detection."""

    def __init__(self, sample_interval_seconds: float = 1.0) -> None:
        self._interval = max(sample_interval_seconds, 0.1)

    @property
    def name(self) -> str:
        return "synthetic"

    def is_available(self) -> bool:
        return True

    def track_subjects(self, video_path: Path, *, duration_seconds: float) -> SubjectTrack:
        if duration_seconds <= 0:
            return SubjectTrack(samples=())
        samples: list[SubjectSample] = []
        time = 0.0
        while time <= duration_seconds:
            progress = min(time / duration_seconds, 1.0)
            samples.append(
                SubjectSample(
                    time_seconds=round(time, 3),
                    x_center=round(0.35 + 0.3 * progress, 4),
                    y_center=0.5,
                    width=0.2,
                    height=0.3,
                    confidence=0.9,
                )
            )
            time += self._interval
        return SubjectTrack(samples=tuple(samples))
