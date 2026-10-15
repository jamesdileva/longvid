"""faster-whisper provider — the default local transcription engine.

The model is loaded lazily on first use and downloaded on demand. Installing
the optional dependency::

    pip install backend[whisper]
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

from app.providers.transcription.base import SegmentResult, TranscriptionProvider


class FasterWhisperProvider(TranscriptionProvider):
    """Local Whisper inference via faster-whisper (CTranslate2)."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    @property
    def name(self) -> str:
        return "whisper"

    def is_available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> list[SegmentResult]:
        if self._model is None:
            self._load_model()

        segments, _info = self._model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
        )
        results: list[SegmentResult] = []
        for segment in segments:
            confidence = None
            # faster-whisper renamed avg_log_prob to avg_logprob in v1.1+.
            log_prob = getattr(segment, "avg_logprob", None)
            if log_prob is None:
                log_prob = getattr(segment, "avg_log_prob", None)
            if log_prob is not None:
                confidence = round(math.exp(log_prob), 4)
            results.append(
                SegmentResult(
                    start_seconds=round(segment.start, 3),
                    end_seconds=round(segment.end, 3),
                    text=segment.text.strip(),
                    confidence=confidence,
                )
            )
        return results

    def _load_model(self) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self._model_size, device=self._device, compute_type=self._compute_type
        )
