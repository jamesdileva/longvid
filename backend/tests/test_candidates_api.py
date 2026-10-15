"""Tests for the candidate generation API chain (roadmap 7.4/7.5)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database import get_sessionmaker
from app.models.processing import JobType
from app.providers.transcription.base import SegmentResult
from app.services import jobs as job_service
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from tests.conftest import requires_ffmpeg

TERMINAL = {"completed", "failed", "cancelled"}


@pytest.fixture(scope="session")
def narrate_video(tmp_path_factory) -> Path:
    """12s video: 6s of tone then 6s of silence."""
    import subprocess

    path = tmp_path_factory.mktemp("narrate") / "narrate.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=12:size=320x240:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=6",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:d=6",
            "-filter_complex",
            "[1:a][2:a]concat=n=2:v=0:a=1[outa]",
            "-map",
            "0:v",
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


def seed_transcript(client, video_id: int, marker_text: str) -> None:
    """Replace the transcript with fixed text (the fake LLM keys off [HIGHLIGHT])."""
    session = get_sessionmaker()()
    try:
        video = video_service.get_video(session, video_id)
        assert video is not None
        duration = video.duration_seconds or 12.0
        segments = [
            SegmentResult(0.0, duration / 3, f"[HIGHLIGHT] {marker_text} part one"),
            SegmentResult(duration / 3, duration * 2 / 3, f"[HIGHLIGHT] {marker_text} part two"),
            SegmentResult(duration * 2 / 3, duration, f"[HIGHLIGHT] {marker_text} part three"),
        ]
        transcript_service.replace_transcript(session, video, segments)
    finally:
        session.close()


@requires_ffmpeg
class TestGenerateCandidates:
    def test_generates_sorted_scored_candidates(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        assert run_job(client, video["id"], "extract_audio")["status"] == "completed"
        assert run_job(client, video["id"], "transcribe")["status"] == "completed"
        seed_transcript(client, video["id"], "what a moment")
        assert run_job(client, video["id"], "analyze_events")["status"] == "completed"
        generated = run_job(client, video["id"], "generate_candidates")
        assert generated["status"] == "completed", generated.get("error")
        assert generated["progress"] == 1.0

        candidates = client.get(f"/api/videos/{video['id']}/candidates").json()
        assert candidates
        scores = [candidate["overall_score"] for candidate in candidates]
        assert scores == sorted(scores, reverse=True)

        first = candidates[0]
        assert first["video_id"] == video["id"]
        assert first["start_seconds"] < first["end_seconds"]
        assert first["start_seconds"] >= 0
        assert first["end_seconds"] <= 12.1
        assert first["semantic_score"] == pytest.approx(0.9)
        assert first["source"] == "fake"
        assert first["reason"]
        assert first["category"] == "reaction"
        # Weighted score fields all present.
        assert set(first) >= {
            "audio_score",
            "visual_score",
            "context_score",
            "standalone_score",
            "novelty_score",
        }

    def test_generation_without_transcript_yields_no_candidates(
        self, client, narrate_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        assert run_job(client, video["id"], "extract_audio")["status"] == "completed"
        assert run_job(client, video["id"], "analyze_events")["status"] == "completed"
        assert run_job(client, video["id"], "generate_candidates")["status"] == "completed"

        assert client.get(f"/api/videos/{video['id']}/candidates").json() == []

    def test_generation_without_audio_fails(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        job = run_job(client, video["id"], "generate_candidates")

        assert job["status"] == "failed"
        assert "Extract audio" in job["error"]

    def test_generate_endpoint_returns_202(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)
        assert run_job(client, video["id"], "extract_audio")["status"] == "completed"

        response = client.post(f"/api/videos/{video['id']}/generate-candidates")

        assert response.status_code == 202
        assert response.json()["status"] == "queued"

    def test_duplicate_generation_rejected(self, client, db_session, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        job_service.create_job(db_session, video["id"], JobType.GENERATE_CANDIDATES)
        response = client.post(f"/api/videos/{video['id']}/generate-candidates")

        assert response.status_code == 409

    def test_candidates_are_replaced_on_rerun(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "transcribe")
        seed_transcript(client, video["id"], "again")
        run_job(client, video["id"], "analyze_events")
        run_job(client, video["id"], "generate_candidates")
        first = client.get(f"/api/videos/{video['id']}/candidates").json()

        run_job(client, video["id"], "generate_candidates")
        second = client.get(f"/api/videos/{video['id']}/candidates").json()

        assert len(first) == len(second)


@requires_ffmpeg
class TestCandidateReview:
    def test_accept_and_reject(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "transcribe")
        seed_transcript(client, video["id"], "review")
        run_job(client, video["id"], "analyze_events")
        run_job(client, video["id"], "generate_candidates")
        candidate = client.get(f"/api/videos/{video['id']}/candidates").json()[0]

        accepted = client.patch(f"/api/candidates/{candidate['id']}", json={"status": "accepted"})
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        rejected = client.patch(f"/api/candidates/{candidate['id']}", json={"status": "rejected"})
        assert rejected.json()["status"] == "rejected"

    def test_patch_unknown_candidate_returns_404(self, client) -> None:
        response = client.patch("/api/candidates/999999", json={"status": "accepted"})
        assert response.status_code == 404

    def test_get_unknown_candidate_returns_404(self, client) -> None:
        assert client.get("/api/candidates/999999").status_code == 404


@requires_ffmpeg
class TestProjectCandidates:
    def test_project_candidates_listing(self, client, narrate_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "transcribe")
        seed_transcript(client, video["id"], "project")
        run_job(client, video["id"], "analyze_events")
        run_job(client, video["id"], "generate_candidates")

        video_candidates = client.get(f"/api/videos/{video['id']}/candidates").json()
        project_candidates = client.get(f"/api/projects/{project['id']}/candidates").json()

        assert len(project_candidates) == len(video_candidates)

    def test_unknown_project_returns_404(self, client) -> None:
        assert client.get(f"/api/projects/{'0' * 32}/candidates").status_code == 404
