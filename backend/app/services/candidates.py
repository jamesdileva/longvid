"""Candidate persistence and queries."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.candidate import CandidateStatus, ClipCandidate


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
    from app.models.video import Video

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
