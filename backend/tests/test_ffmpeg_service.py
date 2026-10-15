"""Tests for the FFmpeg service: probe, thumbnail, and preview generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.services import ffmpeg_service
from app.services.ffmpeg_service import FFmpegError
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
class TestProbeFile:
    def test_extracts_video_and_audio_metadata(self, synthetic_video: Path) -> None:
        info = ffmpeg_service.probe_file(synthetic_video)

        assert info.width == 320
        assert info.height == 240
        assert info.fps == pytest.approx(10.0, abs=0.2)
        assert 1.7 <= info.duration_seconds <= 2.5
        assert info.video_codec == "h264"
        assert info.audio_codec == "aac"
        assert info.channels == 1
        assert info.sample_rate == 44100
        assert info.file_size_bytes > 0

    def test_parses_fractional_fps(self) -> None:
        assert ffmpeg_service._parse_fps("30000/1001") == pytest.approx(29.97, abs=0.01)
        assert ffmpeg_service._parse_fps("30") == 30.0
        assert ffmpeg_service._parse_fps("0/0") is None
        assert ffmpeg_service._parse_fps(None) is None
        assert ffmpeg_service._parse_fps("garbage") is None

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FFmpegError):
            ffmpeg_service.probe_file(tmp_path / "does-not-exist.mp4")


@requires_ffmpeg
class TestGenerateThumbnail:
    def test_creates_jpeg(self, synthetic_video: Path, tmp_path: Path) -> None:
        out = tmp_path / "thumb.jpg"

        result = ffmpeg_service.generate_thumbnail(synthetic_video, out, at_seconds=1.0, width=320)

        assert result.is_file()
        assert result.stat().st_size > 0
        assert result.read_bytes()[:2] == b"\xff\xd8"


@requires_ffmpeg
class TestGeneratePreview:
    def test_creates_short_mp4(self, synthetic_video: Path, tmp_path: Path) -> None:
        out = tmp_path / "preview.mp4"

        result = ffmpeg_service.generate_preview(
            synthetic_video, out, duration_seconds=2.0, width=480
        )

        assert result.is_file()
        assert result.stat().st_size > 0
        info = ffmpeg_service.probe_file(result)
        assert info.duration_seconds <= 4.1

    def test_preview_length_capped_by_source(self, synthetic_video: Path, tmp_path: Path) -> None:
        out = tmp_path / "preview2.mp4"

        # 2s source, settings.preview_seconds=4 -> the whole clip, nothing more
        ffmpeg_service.generate_preview(synthetic_video, out, duration_seconds=2.0, width=240)

        info = ffmpeg_service.probe_file(out)
        assert info.duration_seconds <= 2.5


@requires_ffmpeg
class TestExtractAudio:
    def test_produces_mono_16khz_wav(self, synthetic_video: Path, tmp_path: Path) -> None:
        out = tmp_path / "audio.wav"

        result = ffmpeg_service.extract_audio(synthetic_video, out, sample_rate=16000, channels=1)

        assert result.is_file()
        header = result.read_bytes()[:12]
        assert header[:4] == b"RIFF"
        assert header[8:12] == b"WAVE"

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=sample_rate,channels",
                "-of",
                "json",
                str(result),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        streams = json.loads(probe.stdout)["streams"]
        assert streams[0]["sample_rate"] == "16000"
        assert streams[0]["channels"] == 1

    def test_video_without_audio_raises(self, tmp_path: Path) -> None:
        silent = tmp_path / "silent.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=1:size=160x120:rate=5",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(silent),
            ],
            check=True,
            capture_output=True,
        )

        with pytest.raises(FFmpegError):
            ffmpeg_service.extract_audio(silent, tmp_path / "out.wav", 16000, 1)


@requires_ffmpeg
class TestStoreImportCopy:
    def test_copies_without_touching_original(self, synthetic_video: Path, tmp_path: Path) -> None:
        original_bytes = synthetic_video.read_bytes()

        stored = ffmpeg_service.store_import_copy(synthetic_video, tmp_path / "source")

        assert stored.is_file()
        assert stored.read_bytes() == original_bytes
        assert stored.name.endswith(".mp4")
        assert stored != synthetic_video
