"""Tests for the processing jobs API and worker behavior."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database import get_sessionmaker
from app.models.processing import JobType
from app.services import jobs as job_service
from app.workers.queue import run_job
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


@pytest.fixture()
def db_session() -> Iterator:
    """Plain session bound to the current (test) engine."""
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


def wait_for_job(client, job_id: int, timeout: float = 30.0) -> dict:
    """Poll a job until it reaches a terminal state."""
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} never settled (last: {job})")


def probe_audio_streams(path: Path) -> dict:
    result = subprocess.run(
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
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        raise AssertionError("No audio stream found")
    return streams[0]


@requires_ffmpeg
class TestProcessVideo:
    def test_extract_audio_completes_and_persists(
        self, client, data_dir: Path, synthetic_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        response = client.post(f"/api/videos/{video['id']}/process", json={"type": "extract_audio"})

        assert response.status_code == 202
        job = response.json()
        assert job["status"] == "queued"
        assert job["type"] == "extract_audio"
        assert job["progress"] == 0.0

        final = wait_for_job(client, job["id"])
        assert final["status"] == "completed", final.get("error")
        assert final["progress"] == 1.0
        assert final["started_at"] is not None
        assert final["completed_at"] is not None

        detail = client.get(f"/api/videos/{video['id']}").json()
        assert detail["audio_path"] == f"media/audio/{video['id']}.wav"

        wav = data_dir / project["workspace_path"] / f"media/audio/{video['id']}.wav"
        assert wav.is_file()
        stream = probe_audio_streams(wav)
        assert int(stream["sample_rate"]) == 16000
        assert int(stream["channels"]) == 1

    def test_duplicate_active_job_returns_409(
        self, client, db_session, synthetic_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        # Create an active job directly so the endpoint guard is deterministic.
        job_service.create_job(db_session, video["id"], JobType.EXTRACT_AUDIO)

        response = client.post(f"/api/videos/{video['id']}/process", json={"type": "extract_audio"})
        assert response.status_code == 409

    def test_unknown_video_returns_404(self, client) -> None:
        response = client.post("/api/videos/999999/process", json={"type": "extract_audio"})
        assert response.status_code == 404


class TestCancelJob:
    def test_cancelled_job_never_runs(
        self, client, data_dir: Path, synthetic_video: Path, db_session
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        job = job_service.create_job(db_session, video["id"], JobType.EXTRACT_AUDIO)

        response = client.post(f"/api/jobs/{job.id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        # Running the worker after cancellation must not start the job.
        run_job(job.id)

        final = client.get(f"/api/jobs/{job.id}").json()
        assert final["status"] == "cancelled"
        assert final["started_at"] is None
        wav = data_dir / project["workspace_path"] / f"media/audio/{video['id']}.wav"
        assert not wav.exists()

    def test_cancel_unknown_job_returns_404(self, client) -> None:
        assert client.post("/api/jobs/999999/cancel").status_code == 404

    def test_cancel_completed_job_returns_409(
        self, client, synthetic_video: Path, db_session
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        job = job_service.create_job(db_session, video["id"], JobType.EXTRACT_AUDIO)
        job_service.mark_running(db_session, job)
        job_service.complete_job(db_session, job)
        job_id = job.id

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 409


class TestVideoJobs:
    def test_lists_video_jobs(self, client, synthetic_video: Path, db_session) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video)

        job_service.create_job(db_session, video["id"], JobType.EXTRACT_AUDIO)
        job_service.create_job(db_session, video["id"], JobType.EXTRACT_AUDIO)

        response = client.get(f"/api/jobs/video/{video['id']}")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_openapi_exposes_job_routes(self, client) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/videos/{video_id}/process" in paths
        assert "/api/jobs/{job_id}/cancel" in paths
        assert "/api/jobs/video/{video_id}" in paths
