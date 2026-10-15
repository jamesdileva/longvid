"""Tests for the analysis (scene/event detection) API chain."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database import get_sessionmaker
from app.models.processing import JobType
from app.services import analysis as analysis_service
from app.services import jobs as job_service
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


@pytest.fixture(scope="session")
def contrast_video(tmp_path_factory) -> Path:
    """A 12s video: red then blue scenes, tone then silence."""
    if subprocess.run(["ffmpeg", "-version"], check=False, capture_output=True).returncode != 0:
        pytest.skip("ffmpeg not available")
    path = tmp_path_factory.mktemp("contrast") / "contrast.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x240:d=6:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=6:r=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:d=6",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:d=6",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1[outv];[2:a][3:a]concat=n=2:v=0:a=1[outa]",
            "-map",
            "[outv]",
            "-map",
            "[outa]",
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


def run_job(client, video_id: int, job_type: str, timeout: float = 120.0) -> dict:
    response = client.post(f"/api/videos/{video_id}/process", json={"type": job_type})
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} never settled (last: {job})")


@requires_ffmpeg
class TestAnalysisChain:
    def test_analyze_detects_scenes_and_events(self, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        extract = run_job(client, video["id"], "extract_audio")
        assert extract["status"] == "completed", extract.get("error")
        analyze = run_job(client, video["id"], "analyze_events")
        assert analyze["status"] == "completed", analyze.get("error")
        assert analyze["progress"] == 1.0

        scenes = client.get(f"/api/videos/{video['id']}/scenes").json()
        assert len(scenes) >= 2, scenes
        assert scenes[0]["position"] == 0
        assert scenes[0]["start_seconds"] == 0.0
        assert scenes[-1]["end_seconds"] == pytest.approx(12.0, abs=0.2)
        positions = [scene["position"] for scene in scenes]
        assert positions == sorted(positions)

        events = client.get(f"/api/videos/{video['id']}/events").json()
        types = {event["type"] for event in events}
        assert "scene_change" in types, types
        # second half is silent -> at least one silence event
        assert "silence" in types, types
        assert all(event["video_id"] == video["id"] for event in events)
        assert all(event["end_seconds"] <= 12.1 for event in events)

    def test_scene_change_event_payload_carries_score(self, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "analyze_events")

        events = client.get(f"/api/videos/{video['id']}/events").json()
        scene_changes = [event for event in events if event["type"] == "scene_change"]

        assert scene_changes
        assert scene_changes[0]["payload"] is not None
        assert "score" in scene_changes[0]["payload"]
        assert scene_changes[0]["source"] == "scene_detection"

    def test_events_replaced_on_reanalysis(self, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "analyze_events")
        first = client.get(f"/api/videos/{video['id']}/events").json()
        run_job(client, video["id"], "analyze_events")
        second = client.get(f"/api/videos/{video['id']}/events").json()

        assert len(second) == len(first)
        assert {e["type"] for e in second} == {e["type"] for e in first}

    def test_analyze_without_audio_fails(self, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        job = run_job(client, video["id"], "analyze_events")

        assert job["status"] == "failed"
        assert "Extract audio" in job["error"]

    def test_unknown_video_returns_404(self, client) -> None:
        assert client.get("/api/videos/999999/scenes").status_code == 404
        assert client.get("/api/videos/999999/events").status_code == 404

    def test_empty_analysis_lists(self, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        assert client.get(f"/api/videos/{video['id']}/scenes").json() == []
        assert client.get(f"/api/videos/{video['id']}/events").json() == []

    def test_duplicate_active_analysis_rejected(
        self, client, db_session, contrast_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        job_service.create_job(db_session, video["id"], JobType.ANALYZE_EVENTS)
        response = client.post(
            f"/api/videos/{video['id']}/process", json={"type": "analyze_events"}
        )
        assert response.status_code == 409


class TestReplaceScenesService:
    def test_positions_are_sequential(self, db_session, client, contrast_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], contrast_video)

        rows = analysis_service.replace_scenes(
            db_session, video["id"], [(0.0, 5.0, 0.2), (5.0, 12.0, None)]
        )

        assert [row.position for row in rows] == [0, 1]
        assert rows[0].score == 0.2
        assert rows[1].score is None
