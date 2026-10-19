"""Tests for the exports API and pipeline (roadmap Phase 18; guide §24)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app import __version__
from app.database import get_sessionmaker
from app.providers.transcription.base import SegmentResult
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


def create_project(client) -> dict:
    response = client.post("/api/projects", json={"name": "Exports"})
    assert response.status_code == 201
    return response.json()


def import_video(client, project_id: str, path: Path) -> dict:
    response = client.post(f"/api/projects/{project_id}/videos", json={"path": str(path)})
    assert response.status_code == 201
    return response.json()


def run_job(client, video_id: int, job_type: str, timeout: float = 120.0) -> dict:
    response = client.post(f"/api/videos/{video_id}/process", json={"type": job_type})
    assert response.status_code == 202, response.text
    return settle(client, response.json()["id"], timeout=timeout)


def settle(client, job_id: int, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} never settled (last: {job})")


@pytest.fixture()
def ready_clip(client, narrate_video: Path) -> tuple[dict, dict, dict]:
    """A project/video with one rendered clip ready to export."""
    project = create_project(client)
    video = import_video(client, project["id"], narrate_video)
    run_job(client, video["id"], "extract_audio")
    run_job(client, video["id"], "transcribe")
    session = get_sessionmaker()()
    try:
        row = video_service.get_video(session, video["id"])
        assert row is not None
        duration = row.duration_seconds or 12.0
        transcript_service.replace_transcript(
            session,
            row,
            [
                SegmentResult(0.0, duration / 2, "[HIGHLIGHT] a big moment"),
                SegmentResult(duration / 2, duration, "[HIGHLIGHT] another moment"),
            ],
        )
    finally:
        session.close()
    run_job(client, video["id"], "analyze_events")
    run_job(client, video["id"], "generate_candidates")

    queued = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
    assert queued.status_code == 202, queued.text
    job = settle(client, queued.json()["job_id"])
    assert job["status"] == "completed", job.get("error")

    clips = client.get(f"/api/videos/{video['id']}/clips").json()
    ready = next(clip for clip in clips if clip["status"] == "ready")
    return project, video, ready


class TestExportPresetsEndpoint:
    def test_lists_catalog(self, client) -> None:
        response = client.get("/api/export-presets")
        assert response.status_code == 200
        keys = [preset["key"] for preset in response.json()]
        assert keys[0] == "youtube"
        assert {"youtube_shorts", "tiktok", "instagram_reels", "archive"} <= set(keys)


@requires_ffmpeg
class TestExportRendering:
    def test_renders_and_streams_export(self, client, ready_clip) -> None:
        project, _, clip = ready_clip

        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "youtube"})
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["status"] == "pending"

        job = settle(client, body["job_id"])
        assert job["status"] == "completed", job.get("error")

        export = client.get(f"/api/exports/{body['export_id']}").json()
        assert export["status"] == "ready"
        assert export["clip_id"] == clip["id"]
        assert export["project_id"] == project["id"]
        assert export["preset"] == "youtube"
        assert export["container"] == "mp4"
        assert export["video_codec"] == "h264"
        assert export["audio_codec"] == "aac"
        assert export["file_url"] == f"/api/exports/{export['id']}/file"

        # Reproducibility metadata (guide §24).
        assert export["app_version"] == __version__
        assert export["editing_profile"] == clip["editing_profile"]
        assert export["plan_snapshot"] == clip["editing_plan"]
        assert export["settings"]["crf"] == 20
        assert export["file_size_bytes"] > 0

        streamed = client.get(export["file_url"])
        assert streamed.status_code == 200
        assert streamed.headers["content-type"] == "video/mp4"
        assert streamed.content[4:8] == b"ftyp"

    def test_archive_preset_renders_hevc(self, client, ready_clip) -> None:
        _, _, clip = ready_clip
        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "archive"})
        assert response.status_code == 202, response.text
        settle(client, response.json()["job_id"])

        export = client.get(f"/api/exports/{response.json()['export_id']}").json()
        assert export["status"] == "ready", export.get("error")
        assert export["video_codec"] == "h265"
        assert export["settings"]["max_width"] is None

    def test_project_exports_are_listed(self, client, ready_clip) -> None:
        project, _, clip = ready_clip
        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "tiktok"})
        settle(client, response.json()["job_id"])

        listed = client.get(f"/api/projects/{project['id']}/exports").json()
        assert [export["id"] for export in listed] == [response.json()["export_id"]]

    def test_unknown_preset_is_rejected(self, client, ready_clip) -> None:
        _, _, clip = ready_clip
        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "vimeo"})
        assert response.status_code == 400

    def test_deleting_clip_removes_its_exports(self, client, ready_clip) -> None:
        project, _, clip = ready_clip
        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "youtube"})
        settle(client, response.json()["job_id"])
        export_id = response.json()["export_id"]

        assert client.delete(f"/api/clips/{clip['id']}").status_code == 204
        assert client.get(f"/api/exports/{export_id}").status_code == 404
        assert client.get(f"/api/projects/{project['id']}/exports").json() == []


@requires_ffmpeg
class TestExportValidation:
    def test_export_unknown_clip_is_404(self, client) -> None:
        response = client.post("/api/clips/999999/export", json={"preset": "youtube"})
        assert response.status_code == 404

    def test_get_unknown_export_is_404(self, client) -> None:
        assert client.get("/api/exports/999999").status_code == 404
        assert client.get("/api/exports/999999/file").status_code == 404

    def test_list_exports_unknown_project_is_404(self, client) -> None:
        assert client.get("/api/projects/" + "0" * 32 + "/exports").status_code == 404

    def test_export_of_unrendered_clip_conflicts(self, client, ready_clip) -> None:
        _, _, clip = ready_clip
        session = get_sessionmaker()()
        try:
            from app.models.clip import Clip, ClipStatus

            row = session.get(Clip, clip["id"])
            assert row is not None
            row.status = ClipStatus.PENDING
            session.commit()
        finally:
            session.close()

        response = client.post(f"/api/clips/{clip['id']}/export", json={"preset": "youtube"})
        assert response.status_code == 409
