"""Tests for transcription providers and the provider factory."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

from app.config import Settings
from app.providers.transcription import (
    FasterWhisperProvider,
    ProviderUnavailableError,
    SyntheticTranscriptionProvider,
    get_transcription_provider,
)
from tests.conftest import requires_ffmpeg


def _make_wav(path: Path, seconds: float) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", str(path)],
        check=True,
        capture_output=True,
    )
    return path


@requires_ffmpeg
class TestSyntheticProvider:
    def test_produces_deterministic_fixed_length_segments(self, tmp_path: Path) -> None:
        wav = _make_wav(tmp_path / "tone.wav", 12.0)
        provider = SyntheticTranscriptionProvider(segment_seconds=5.0)

        segments = provider.transcribe(wav)
        repeat = provider.transcribe(wav)

        assert len(segments) == 3  # 0-5, 5-10, 10-12
        assert [s.start_seconds for s in segments] == [0.0, 5.0, 10.0]
        assert segments[0].end_seconds == 5.0
        assert segments[-1].end_seconds == pytest.approx(12.0, abs=0.05)
        assert all(s.confidence == 0.94 for s in segments)
        assert segments == repeat  # deterministic
        assert segments[0].text  # non-empty fixed text

    def test_cycles_fixed_texts(self, tmp_path: Path) -> None:
        wav = _make_wav(tmp_path / "long.wav", 40.0)
        provider = SyntheticTranscriptionProvider(segment_seconds=5.0)

        texts = [s.text for s in provider.transcribe(wav)]

        assert len(texts) == 8
        assert texts[0] == texts[7]  # cycles through the fixed list

    def test_is_always_available(self) -> None:
        assert SyntheticTranscriptionProvider().is_available()
        assert SyntheticTranscriptionProvider().name == "synthetic"


class TestFactory:
    def test_returns_synthetic_when_configured(self) -> None:
        settings = Settings(transcription_provider="synthetic")

        provider = get_transcription_provider(settings)

        assert provider.name == "synthetic"

    def test_rejects_unknown_provider(self) -> None:
        settings = Settings(transcription_provider="carrier-pigeon")

        with pytest.raises(ProviderUnavailableError):
            get_transcription_provider(settings)

    def test_whisper_availability_matches_installation(self) -> None:
        installed = importlib.util.find_spec("faster_whisper") is not None
        assert FasterWhisperProvider().is_available() == installed

        settings = Settings(transcription_provider="whisper")
        if installed:
            provider = get_transcription_provider(settings)
            assert isinstance(provider, FasterWhisperProvider)
        else:
            with pytest.raises(ProviderUnavailableError):
                get_transcription_provider(settings)
