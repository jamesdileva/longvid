"""Test fixtures and path bootstrapping for the backend suite.

Every test runs against an isolated data directory (tmp_path) with a fresh
SQLite database, and fully deterministic time — no wall-clock dependencies.
Media tests use tiny synthetic 2-second clips generated with FFmpeg.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.database import init_db, reset_caches
from app.main import create_app

FFMPEG_MISSING = shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None

requires_ffmpeg = pytest.mark.skipif(FFMPEG_MISSING, reason="ffmpeg/ffprobe not on PATH")


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """A deterministic 2s 320x240 10fps video with a sine audio track."""
    if FFMPEG_MISSING:
        pytest.skip("ffmpeg/ffprobe not available")
    path = tmp_path_factory.mktemp("media") / "synthetic_clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch) -> Iterator[None]:
    """Point the app at a throwaway data dir and clear cached settings/engine."""
    monkeypatch.setenv("LONGVID_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_caches()
    init_db()
    yield
    get_settings.cache_clear()
    reset_caches()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient with lifespan (database initialized) as a context manager."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def data_dir() -> Path:
    """The isolated data directory for the current test."""
    return get_settings().data_dir
