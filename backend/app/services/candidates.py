"""Candidate persistence and queries."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.candidate import CandidateStatus, ClipCandidate
from app.models.video import Video
from app.services import ffmpeg_service
from app.services.ffmpeg_service import FFmpegError
from app.services.workspace import WorkspaceError, asset_path, ensure_subdir


def replace_candidates(
    db: Session, video_id: int, candidates: list[ClipCandidate]
) -> list[ClipCandidate]:
    """Replace a video's candidates with the freshly generated set."""
    db.execute(delete(ClipCandidate).where(ClipCandidate.video_id == video_id))
    db.add_all(candidates)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    return candidates


def list_video_candidates(db: Session, video_id: int) -> list[ClipCandidate]:
    """All candidates for a video, best score first."""
    stmt = select(ClipCandidate).where(ClipCandidate.video_id == video_id)
    rows = list(db.execute(stmt).scalars())
    return sorted(rows, key=lambda candidate: (-candidate.overall_score, candidate.start_seconds))


def list_project_candidates(db: Session, project_id: str) -> list[ClipCandidate]:
    """All candidates across a project's videos, best score first."""
    stmt = (
        select(ClipCandidate)
        .join(Video, Video.id == ClipCandidate.video_id)
        .where(Video.project_id == project_id)
    )
    rows = list(db.execute(stmt).scalars())
    return sorted(rows, key=lambda candidate: (-candidate.overall_score, candidate.start_seconds))


def get_candidate(db: Session, candidate_id: int) -> ClipCandidate | None:
    """One candidate by id, or ``None``."""
    return db.get(ClipCandidate, candidate_id)


def update_status(db: Session, candidate_id: int, status: CandidateStatus) -> ClipCandidate | None:
    """Record human feedback on a candidate."""
    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        return None
    candidate.status = status
    db.commit()
    db.refresh(candidate)
    return candidate


def candidate_thumbnail_dir(project_id: str, video_id: int) -> Path:
    """Directory holding a video's per-candidate thumbnails."""
    return ensure_subdir(project_id, "media/candidate-thumbs") / str(video_id)


def ensure_candidate_thumbnail(db: Session, candidate: ClipCandidate) -> Path | None:
    """Return a candidate's thumbnail frame, generating it once on demand.

    Frames are captured from the source video at the candidate's start time
    and cached under ``media/candidate-thumbs/<video_id>/``. Returns ``None``
    when the source is missing or FFmpeg cannot produce a frame.
    """
    video = db.get(Video, candidate.video_id)
    if video is None:
        return None
    try:
        source = asset_path(video.project_id, f"source/{video.relative_path}")
        output_dir = candidate_thumbnail_dir(video.project_id, video.id)
    except WorkspaceError:
        return None
    if source is None or not source.is_file():
        return None

    output = output_dir / f"{candidate.id}.jpg"
    if output.is_file():
        return output
    try:
        return ffmpeg_service.generate_thumbnail(
            source, output, max(candidate.start_seconds, 0.0), get_settings().thumbnail_width
        )
    except FFmpegError:
        return None


def clear_candidate_thumbnails(project_id: str, video_id: int) -> None:
    """Best-effort removal of a video's cached candidate thumbnails."""
    try:
        directory = candidate_thumbnail_dir(project_id, video_id)
    except WorkspaceError:
        return
    if directory.is_dir():
        shutil.rmtree(directory, ignore_errors=True)
