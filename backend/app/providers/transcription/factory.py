"""Provider registry."""

from __future__ import annotations

from app.config import Settings
from app.providers.transcription.base import TranscriptionProvider
from app.providers.transcription.synthetic import SyntheticTranscriptionProvider
from app.providers.transcription.whisper import FasterWhisperProvider

_PROVIDERS: dict[str, type[TranscriptionProvider]] = {
    "whisper": FasterWhisperProvider,
    "synthetic": SyntheticTranscriptionProvider,
}


class ProviderUnavailableError(RuntimeError):
    """Raised when the configured provider cannot be used."""


def get_transcription_provider(settings: Settings) -> TranscriptionProvider:
    """Instantiate the configured provider, verifying it is usable."""
    provider_cls = _PROVIDERS.get(settings.transcription_provider)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise ProviderUnavailableError(
            f"Unknown transcription provider '{settings.transcription_provider}'. "
            f"Available: {available}."
        )
    provider = _build(provider_cls, settings)
    if not provider.is_available():
        raise ProviderUnavailableError(
            f"Transcription provider '{settings.transcription_provider}' is not available. "
            "Install it (pip install backend[whisper]) or set "
            "LONGVID_TRANSCRIPTION_PROVIDER=synthetic."
        )
    return provider


def _build(provider_cls: type[TranscriptionProvider], settings: Settings) -> TranscriptionProvider:
    if provider_cls is FasterWhisperProvider:
        return FasterWhisperProvider(
            model_size=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    if provider_cls is SyntheticTranscriptionProvider:
        return SyntheticTranscriptionProvider(segment_seconds=settings.synthetic_segment_seconds)
    return provider_cls()
