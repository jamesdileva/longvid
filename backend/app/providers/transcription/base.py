"""Transcription provider interface (architecture §8).

The application depends on this protocol, never on a specific engine.
Implementations: Faster-Whisper (default) and a deterministic synthetic
provider for tests and offline development.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SegmentResult:
    """One transcript segment in seconds from the start of the audio."""

    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None


class TranscriptionProvider(abc.ABC):
    """Local speech-to-text behind a replaceable interface."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier used in logs and settings."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether the provider's runtime dependencies are usable."""

    @abc.abstractmethod
    def transcribe(self, audio_path: Path, *, language: str | None = None) -> list[SegmentResult]:
        """Transcribe an audio file into ordered segments."""
