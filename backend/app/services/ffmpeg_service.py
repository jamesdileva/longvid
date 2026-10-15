"""FFmpeg/FFprobe service — the single gateway to external media tools.

Per docs/architecture.md, every FFmpeg invocation goes through this module,
always with argument arrays (never shell strings). Generated files stay inside
the project workspace; user originals are never modified.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.utils.files import unique_filename

_PROBE_TIMEOUT = 60
_FFMPEG_TIMEOUT = 300
_WAV_HEADER_SIZE = 44


class FFmpegError(RuntimeError):
    """Raised when an external media command fails."""


@dataclass(frozen=True)
class MediaInfo:
    """Normalized media metadata produced by ffprobe."""

    duration_seconds: float
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    sample_rate: int | None
    channels: int | None
    file_size_bytes: int
    format_name: str


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        binary = command[0]
        raise FFmpegError(
            f"'{binary}' not found. Install FFmpeg or set the LONGVID_FFMPEG_PATH/"
            "LONGVID_FFPROBE_PATH environment variables."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"'{command[0]}' timed out after {timeout}s") from exc


def _parse_fps(raw: str | None) -> float | None:
    """Parse ffprobe's fraction fps strings like '30000/1001'."""
    if not raw or raw in {"0/0", "N/A"}:
        return None
    try:
        if "/" in raw:
            numerator, denominator = raw.split("/", maxsplit=1)
            if float(denominator) == 0:
                return None
            return round(float(numerator) / float(denominator), 3)
        return float(raw)
    except (TypeError, ValueError):
        return None


def probe_file(path: Path) -> MediaInfo:
    """Extract normalized media metadata. Raises FFmpegError on failure."""
    settings = get_settings()
    if not path.is_file():
        raise FFmpegError(f"Media file does not exist: {path}")

    result = _run(
        [
            settings.ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        timeout=_PROBE_TIMEOUT,
    )
    if result.returncode != 0:
        raise FFmpegError(f"ffprobe failed: {result.stderr.strip() or result.stdout.strip()}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FFmpegError("ffprobe returned unreadable output") from exc

    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    if video is None:
        raise FFmpegError(f"No video stream found in {path.name}")
    if "duration" not in fmt:
        raise FFmpegError(f"Could not determine duration of {path.name}")

    return MediaInfo(
        duration_seconds=float(fmt["duration"]),
        width=video.get("width"),
        height=video.get("height"),
        fps=_parse_fps(video.get("r_frame_rate")),
        video_codec=video.get("codec_name"),
        audio_codec=audio.get("codec_name") if audio else None,
        sample_rate=int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
        channels=audio.get("channels") if audio else None,
        file_size_bytes=int(fmt.get("size", 0)),
        format_name=fmt.get("format_name", ""),
    )


def generate_thumbnail(video_path: Path, output_path: Path, at_seconds: float, width: int) -> Path:
    """Capture a single frame as JPEG into the workspace thumbnails dir."""
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        [
            settings.ffmpeg_path,
            "-y",
            "-ss",
            f"{max(at_seconds, 0):.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2",
            str(output_path),
        ],
        timeout=_FFMPEG_TIMEOUT,
    )
    if result.returncode != 0 or not output_path.is_file():
        raise FFmpegError(f"Thumbnail generation failed: {result.stderr.strip()}")
    return output_path


def generate_preview(
    video_path: Path, output_path: Path, duration_seconds: float, width: int
) -> Path:
    """Render a short, low-bitrate preview clip from the start of the video."""
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    length = min(settings.preview_seconds, max(duration_seconds, 0.1))
    result = _run(
        [
            settings.ffmpeg_path,
            "-y",
            "-i",
            str(video_path),
            "-t",
            f"{length:.3f}",
            "-vf",
            f"scale={width}:-2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        timeout=_FFMPEG_TIMEOUT,
    )
    if result.returncode != 0 or not output_path.is_file():
        raise FFmpegError(f"Preview generation failed: {result.stderr.strip()}")
    return output_path


def extract_audio(video_path: Path, output_path: Path, sample_rate: int, channels: int) -> Path:
    """Extract audio as mono WAV for transcription (implementation-guide §11).

    Output is PCM s16le at the target sample rate; the source video is only
    read. Used by the EXTRACT_AUDIO pipeline stage.
    """
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = sample_rate or settings.audio_sample_rate
    channels = channels or settings.audio_channels
    result = _run(
        [
            settings.ffmpeg_path,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        timeout=_FFMPEG_TIMEOUT,
    )
    if result.returncode != 0:
        raise FFmpegError(f"Audio extraction failed: {result.stderr.strip()}")
    if not _is_valid_wav(output_path):
        raise FFmpegError("Audio extraction produced an empty or invalid WAV")
    return output_path


def cut_clip(video_path: Path, output_path: Path, start_seconds: float, end_seconds: float) -> Path:
    """Cut a time range out of a video into a new MP4 (stream copy)."""
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(end_seconds - start_seconds, 0.1)
    result = _run(
        [
            settings.ffmpeg_path,
            "-y",
            "-ss",
            f"{max(start_seconds, 0):.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.3f}",
            "-c",
            "copy",
            str(output_path),
        ],
        timeout=_FFMPEG_TIMEOUT,
    )
    if result.returncode != 0 or not output_path.is_file():
        raise FFmpegError(f"Clip cut failed: {result.stderr.strip()}")
    return output_path


def _is_valid_wav(path: Path) -> bool:
    """Cheap structural check: RIFF/WAVE header plus a plausible data size."""
    if not path.is_file() or path.stat().st_size <= _WAV_HEADER_SIZE:
        return False
    with path.open("rb") as handle:
        header = handle.read(12)
    return header[:4] == b"RIFF" and header[8:12] == b"WAVE"


def ensure_tool_available(binary: str) -> bool:
    """Check PATH for an external binary without running it."""
    return shutil.which(binary) is not None


def store_import_copy(source_path: Path, destination_dir: Path) -> Path:
    """Copy a user-selected video into a project workspace source/ dir.

    The original file is only read; the copy keeps the workspace
    self-contained and non-destructive.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / unique_filename(source_path.name)
    shutil.copy2(source_path, destination)
    return destination
