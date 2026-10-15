"""Tests for the transcript API and the transcribe pipeline stage."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database import get_sessionmaker
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


@pytest.fixture()
def db_session() -> Iterator:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def create_project(client, name: str = "Gaming Session") -> dict:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def import_video(client, project_id: str, path: Path) -> dict:
    response = client.post(f"/api/projects/{project_id}/videos", json={"path": str(path)})
    assert response.status_code == 201
    return response.json()


def start_job(client, video_id: int, job_type: str) -> dict:
    response = client.post(f"/api/videos/{video_id}/process", json={"type": job_type})
    assert response.status_code == 202
    return response.json()


def wait_for_job(client, job_id: int, timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} never settled (last: {job})")


def transcribe_video(client, project_id: str, video_id: int, data_dir: Path) -> dict:
    """Run audio extraction then transcription, waiting for both to settle."""
    extract = start_job(client, video_id, "extract_audio")
    extract_final = wait_for_job(client, extract["id"])
    assert extract_final["status"] == "completed", extract_final.get("error")

    transcribe = start_job(client, video_id, "transcribe")
    transcribe_final = wait_for_job(client, transcribe["id"])
    return transcribe_final


@requires_ffmpeg
class TestTranscriptApi:
    def test_transcript_returns_ordered_segments(
        self, client, data_dir: Path, synthetic_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        final = transcribe_video(client, project["id"], video["id"], data_dir)
        assert final["status"] == "completed", final.get("error")

        response = client.get(f"/api/videos/{video['id']}/transcript")
        assert response.status_code == 200
        transcript = response.json()

        audio_duration = 2.0  # synthetic fixture
        segments = transcript["segments"]
        assert len(segments) >= 1
        assert [s["position"] for s in segments] == list(range(len(segments)))
        assert all(s["text"] for s in segments)
        assert all(0 <= s["start_seconds"] < s["end_seconds"] for s in segments)
        assert all(s["end_seconds"] <= audio_duration + 0.1 for s in segments)
        assert transcript["video_id"] == video["id"]

    def test_transcript_missing_before_transcription(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        response = client.get(f"/api/videos/{video['id']}/transcript")

        assert response.status_code == 404
        assert "No transcript" in response.json()["detail"]

    def test_transcript_unknown_video_returns_404(self, client) -> None:
        assert client.get("/api/videos/999999/transcript").status_code == 404

    def test_transcribe_without_audio_fails(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        job = start_job(client, video["id"], "transcribe")
        final = wait_for_job(client, job["id"])

        assert final["status"] == "failed"
        assert "Extract audio" in final["error"]

    def test_re_transcription_replaces_segments(
        self, client, data_dir: Path, synthetic_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        transcribe_video(client, project["id"], video["id"], data_dir)
        first = client.get(f"/api/videos/{video['id']}/transcript").json()

        second_job = start_job(client, video["id"], "transcribe")
        second_final = wait_for_job(client, second_job["id"])
        assert second_final["status"] == "completed", second_final.get("error")
        second = client.get(f"/api/videos/{video['id']}/transcript").json()

        # Re-running replaces the transcript: no duplicated or stale segments.
        assert len(second["segments"]) == len(first["segments"])
        assert [s["position"] for s in second["segments"]] == [
            s["position"] for s in first["segments"]
        ]
        assert [s["text"] for s in second["segments"]] == [s["text"] for s in first["segments"]]
        assert second["created_at"] >= first["created_at"]
