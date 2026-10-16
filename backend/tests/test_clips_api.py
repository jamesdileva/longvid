"""Tests for automatic clipping: clip model, generation, and batch selection."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.api.clips import _select_candidates
from app.database import get_sessionmaker
from app.models.candidate import CandidateStatus, ClipCandidate
from app.providers.transcription.base import SegmentResult
from app.schemas.clips import ClipGenerateRequest
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


@pytest.fixture()
def db_session() -> Iterator:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def create_project(client, name: str = "Clipping") -> dict:
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


def prepare_with_candidates(client, narrate_video: Path) -> tuple[dict, dict]:
    """Full chain up to generated candidates for a video."""
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
    return project, video


class TestClipSelection:
    def _candidate(self, cid: int, score: float, status=CandidateStatus.PENDING) -> ClipCandidate:
        candidate = ClipCandidate(
            video_id=1,
            start_seconds=float(cid),
            end_seconds=float(cid) + 10,
            overall_score=score,
            status=status,
        )
        candidate.id = cid
        return candidate

    def _pool(self) -> list[ClipCandidate]:
        return [self._candidate(cid, 1.0 - cid / 10) for cid in range(1, 8)]

    def test_top5_limits_to_five(self) -> None:
        selected = _select_candidates(self._pool(), ClipGenerateRequest(selection="top5"), set())
        assert [candidate.id for candidate in selected] == [1, 2, 3, 4, 5]

    def test_top10_returns_all_when_fewer(self) -> None:
        selected = _select_candidates(self._pool(), ClipGenerateRequest(selection="top10"), set())
        assert len(selected) == 7

    def test_all_returns_everything(self) -> None:
        selected = _select_candidates(self._pool(), ClipGenerateRequest(selection="all"), set())
        assert len(selected) == 7

    def test_accepted_filters_by_status(self) -> None:
        pool = [
            self._candidate(1, 0.9, CandidateStatus.ACCEPTED),
            self._candidate(2, 0.8, CandidateStatus.PENDING),
            self._candidate(3, 0.7, CandidateStatus.ACCEPTED),
        ]
        selected = _select_candidates(pool, ClipGenerateRequest(selection="accepted"), set())
        assert [candidate.id for candidate in selected] == [1, 3]

    def test_excludes_already_clipped(self) -> None:
        selected = _select_candidates(self._pool(), ClipGenerateRequest(selection="top5"), {1, 2})
        assert [candidate.id for candidate in selected] == [3, 4, 5]

    def test_explicit_candidate_ids_win(self) -> None:
        request = ClipGenerateRequest(selection="all", candidate_ids=[6, 4])
        selected = _select_candidates(self._pool(), request, set())
        assert [candidate.id for candidate in selected] == [4, 6]


@requires_ffmpeg
class TestClipGeneration:
    def test_renders_clip_file(self, client, narrate_video: Path) -> None:
        project, video = prepare_with_candidates(client, narrate_video)

        response = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["clip_count"] >= 1

        job = run_job_settle(client, body["job_id"])
        assert job["status"] == "completed", job.get("error")

        clips = client.get(f"/api/videos/{video['id']}/clips").json()
        assert clips
        clip = clips[0]
        assert clip["status"] == "ready"
        assert clip["video_id"] == video["id"]
        assert clip["start_seconds"] < clip["end_seconds"]
        assert clip["duration_seconds"] == pytest.approx(
            clip["end_seconds"] - clip["start_seconds"]
        )
        assert clip["editing_profile"] == "clean"
        assert clip["file_url"] == f"/api/clips/{clip['id']}/file"

        streamed = client.get(clip["file_url"])
        assert streamed.status_code == 200
        assert streamed.headers["content-type"] == "video/mp4"
        assert streamed.content[4:8] == b"ftyp"

        project_clips = client.get(f"/api/projects/{project['id']}/clips").json()
        assert len(project_clips) == len(clips)
        assert client.get(f"/api/projects/{project['id']}").json()["clip_count"] == len(clips)

    def test_duplicate_generation_skips_clipped_candidates(
        self, client, narrate_video: Path
    ) -> None:
        _, video = prepare_with_candidates(client, narrate_video)
        first = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        run_job_settle(client, first.json()["job_id"])

        second = client.post(f"/api/videos/{video['id']}/generate-clips", json={})

        assert second.status_code == 409

    def test_generate_without_candidates_conflicts(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        response = client.post(f"/api/videos/{video['id']}/generate-clips", json={})

        assert response.status_code == 409

    def test_update_and_delete_clip(self, client, narrate_video: Path) -> None:
        _, video = prepare_with_candidates(client, narrate_video)
        created = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        run_job_settle(client, created.json()["job_id"])
        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]

        renamed = client.patch(f"/api/clips/{clip['id']}", json={"title": "Best play"})
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "Best play"

        assert client.delete(f"/api/clips/{clip['id']}").status_code == 204
        assert client.get(f"/api/clips/{clip['id']}").status_code == 404

    def test_deleting_video_removes_clips(self, client, narrate_video: Path) -> None:
        project, video = prepare_with_candidates(client, narrate_video)
        created = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        run_job_settle(client, created.json()["job_id"])

        assert client.delete(f"/api/videos/{video['id']}").status_code == 204
        assert client.get(f"/api/projects/{project['id']}/clips").json() == []

    def test_unknown_clip_returns_404(self, client) -> None:
        assert client.get("/api/clips/999999").status_code == 404
        assert client.get("/api/clips/999999/file").status_code == 404
        assert client.delete("/api/clips/999999").status_code == 404


def run_job_settle(client, job_id: int, timeout: float = 120.0) -> dict:
    """Poll an already-created job until it settles."""
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} never settled (last: {job})")
