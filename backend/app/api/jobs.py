"""Jobs API: track and cancel background work enqueued elsewhere."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JobRead
from app.services import jobs as job_service

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: DbSession) -> JobRead:
    """Poll a job's status and progress."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return JobRead.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job(job_id: int, db: DbSession) -> JobRead:
    """Cancel a queued or running job."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    try:
        job = job_service.cancel_job(db, job)
    except job_service.JobStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return JobRead.model_validate(job)


@router.get("/video/{video_id}", response_model=list[JobRead])
def list_video_jobs(video_id: int, db: DbSession) -> list[JobRead]:
    """All jobs for a video, newest first."""
    return [JobRead.model_validate(j) for j in job_service.list_video_jobs(db, video_id)]
