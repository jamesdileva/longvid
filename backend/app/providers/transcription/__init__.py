"""Transcription providers behind a replaceable interface."""

from app.providers.transcription.base import SegmentResult, TranscriptionProvider
from app.providers.transcription.factory import (
    ProviderUnavailableError,
    get_transcription_provider,
)
from app.providers.transcription.synthetic import SyntheticTranscriptionProvider
from app.providers.transcription.whisper import FasterWhisperProvider

__all__ = [
    "FasterWhisperProvider",
    "ProviderUnavailableError",
    "SegmentResult",
    "SyntheticTranscriptionProvider",
    "TranscriptionProvider",
    "get_transcription_provider",
]
