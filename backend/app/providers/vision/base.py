"""Vision provider interface (architecture §23 smart reframing).

The reframing engine depends on this protocol, never on a specific detector.
Implementations: an OpenCV Haar-cascade face detector (default) and a
deterministic synthetic provider for tests and offline development.

Samples are expressed in *normalized* source-frame coordinates (0..1) so they
are independent of resolution.
"""

from __future__ import annotations

import abc
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubjectSample:
    """One detected subject at a point in time (normalized frame coords)."""

    time_seconds: float
    x_center: float
    y_center: float
    width: float
    height: float
    confidence: float = 1.0


@dataclass(frozen=True)
class SubjectTrack:
    """The subject(s) observed across a video, in time order."""

    samples: tuple[SubjectSample, ...]

    @property
    def is_empty(self) -> bool:
        return not self.samples

    def to_dict(self) -> dict:
        return {"samples": [asdict(sample) for sample in self.samples]}

    @classmethod
    def from_dict(cls, payload: dict | None) -> SubjectTrack:
        if not payload:
            return cls(samples=())
        samples = tuple(
            SubjectSample(
                time_seconds=float(item["time_seconds"]),
                x_center=float(item["x_center"]),
                y_center=float(item["y_center"]),
                width=float(item["width"]),
                height=float(item["height"]),
                confidence=float(item.get("confidence", 1.0)),
            )
            for item in payload.get("samples", [])
        )
        return cls(samples=samples)


class VisionProvider(abc.ABC):
    """Subject detection/tracking behind a replaceable interface."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier used in logs and settings."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether the provider's runtime dependencies are usable."""

    @abc.abstractmethod
    def track_subjects(self, video_path: Path, *, duration_seconds: float) -> SubjectTrack:
        """Detect and track subjects across a video file."""
