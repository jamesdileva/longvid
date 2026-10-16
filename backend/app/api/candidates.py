"""Candidates API: generate, review, and list clip candidates."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.processing import JobType
from app.schemas import CandidateRead, CandidateStatusUpdate
from app.services import candidates as candidate_service
from app.services import jobs as job_service
from app.services import projects as project_service
from app.services import videos as video_service
from app.workers.queue import get_queue

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["candidates"])


@router.post(
    "/videos/{video_id}/generate-candidates",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_candidates(video_id: int, db: DbSession) -> dict:
    """Queue candidate generation for a video (202, poll the returned job)."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    if job_service.active_job_exists(db, video_id, JobType.GENERATE_CANDIDATES):
        raise HTTPException(status.HTTP_409_CONFLICT, "Candidate generation is already active")

    job = job_service.create_job(db, video_id, JobType.GENERATE_CANDIDATES)
    get_queue().submit(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.post(
    "/videos/{video_id}/rescore-candidates",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def rescore_candidates(video_id: int, db: DbSession) -> dict:
    """Re-score existing candidates with current weights (202)."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    if job_service.active_job_exists(db, video_id, JobType.SCORE_CANDIDATES):
        raise HTTPException(status.HTTP_409_CONFLICT, "Re-scoring is already active")

    job = job_service.create_job(db, video_id, JobType.SCORE_CANDIDATES)
    get_queue().submit(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.get("/videos/{video_id}/candidates", response_model=list[CandidateRead])
def list_video_candidates(video_id: int, db: DbSession) -> list[CandidateRead]:
    """Candidates for a video, best score first."""
    return [
        CandidateRead.model_validate(candidate)
        for candidate in candidate_service.list_video_candidates(db, video_id)
    ]


@router.get("/projects/{project_id}/candidates", response_model=list[CandidateRead])
def list_project_candidates(project_id: str, db: DbSession) -> list[CandidateRead]:
    """All candidates across a project's videos, best score first."""
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return [
        CandidateRead.model_validate(candidate)
        for candidate in candidate_service.list_project_candidates(db, project_id)
    ]


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: DbSession) -> CandidateRead:
    """One candidate by id."""
    candidate = candidate_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return CandidateRead.model_validate(candidate)


@router.get("/candidates/{candidate_id}/thumbnail")
def get_candidate_thumbnail(candidate_id: int, db: DbSession) -> FileResponse:
    """Serve a frame from the candidate's start time (generated on demand)."""
    candidate = candidate_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    path = candidate_service.ensure_candidate_thumbnail(db, candidate)
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thumbnail not available")
    return FileResponse(path, media_type="image/jpeg")


@router.patch("/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate_status(
    candidate_id: int, payload: CandidateStatusUpdate, db: DbSession
) -> CandidateRead:
    """Record human feedback (accepted/rejected) on a candidate."""
    candidate = candidate_service.update_status(db, candidate_id, payload.status)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return CandidateRead.model_validate(candidate)
