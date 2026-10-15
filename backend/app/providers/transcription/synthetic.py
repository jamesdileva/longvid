"""Deterministic synthetic transcription provider.

Produces fixed segments derived only from audio duration. Used by tests and
offline development so the pipeline is exercisable without model downloads.
"""

from __future__ import annotations

import wave
from pathlib import Path

from app.providers.transcription.base import SegmentResult, TranscriptionProvider

FIXED_SEGMENT_TEXTS: tuple[str, ...] = (
    "So here's where everything went wrong.",
    "Wait... hold on. No way.",
    "I thought this was impossible.",
    "Everybody stay calm, I've got this.",
    "That's the run right there!",
    "Okay, let's do that one more time.",
    "And that's how you beat the level.",
)


class SyntheticTranscriptionProvider(TranscriptionProvider):
    """Deterministic stand-in for a real ASR engine."""

    def __init__(self, segment_seconds: float = 5.0) -> None:
        self._segment_seconds = segment_seconds

    @property
    def name(self) -> str:
        return "synthetic"

    def is_available(self) -> bool:
        return True

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> list[SegmentResult]:
        duration = _wav_duration_seconds(audio_path)
        segments: list[SegmentResult] = []
        start = 0.0
        index = 0
        while start < duration - 0.05:
            end = min(start + self._segment_seconds, duration)
            segments.append(
                SegmentResult(
                    start_seconds=round(start, 3),
                    end_seconds=round(end, 3),
                    text=FIXED_SEGMENT_TEXTS[index % len(FIXED_SEGMENT_TEXTS)],
                    confidence=0.94,
                )
            )
            start = end
            index += 1
        return segments


def _wav_duration_seconds(audio_path: Path) -> float:
    """Duration of a PCM WAV via the standard library."""
    with wave.open(str(audio_path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
    if rate <= 0:
        return 0.0
    return frames / float(rate)
