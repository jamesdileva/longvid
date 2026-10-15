"""Processing job service: state transitions for the background job system.

Jobs never block HTTP requests (architecture §19). Workers move jobs
queued -> running -> completed/failed; users can cancel queued jobs.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing import JobStatus, JobType, ProcessingJob
from app.utils.time import utcnow

ACTIVE_STATUSES = (JobStatus.QUEUED, JobStatus.RUNNING)


class JobStateError(RuntimeError):
    """Raised when a transition is not allowed for the job's current state."""


def create_job(db: Session, video_id: int, job_type: JobType) -> ProcessingJob:
    """Create and persist a queued job for a video."""
    job = ProcessingJob(video_id=video_id, type=job_type, status=JobStatus.QUEUED, progress=0.0)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> ProcessingJob | None:
    """One job by id, or ``None``."""
    return db.get(ProcessingJob, job_id)


def list_video_jobs(db: Session, video_id: int) -> list[ProcessingJob]:
    """All jobs for a video, newest first."""
    stmt = select(ProcessingJob).where(ProcessingJob.video_id == video_id)
    return list(db.execute(stmt).scalars())


def active_job_exists(db: Session, video_id: int, job_type: JobType) -> bool:
    """True when a queued/running job of this type already exists."""
    stmt = select(ProcessingJob).where(
        ProcessingJob.video_id == video_id,
        ProcessingJob.type == job_type,
        ProcessingJob.status.in_(ACTIVE_STATUSES),
    )
    return db.execute(stmt).first() is not None


def mark_running(db: Session, job: ProcessingJob) -> ProcessingJob:
    """Move a queued job to running and stamp the start time."""
    if job.status != JobStatus.QUEUED:
        raise JobStateError(f"Job {job.id} is {job.status.value}, cannot start")
    job.status = JobStatus.RUNNING
    job.started_at = utcnow()
    job.progress = 0.0
    db.commit()
    db.refresh(job)
    return job


def update_progress(db: Session, job: ProcessingJob, progress: float) -> ProcessingJob:
    """Set clamped job progress (0..1)."""
    job.progress = min(max(progress, 0.0), 1.0)
    db.commit()
    db.refresh(job)
    return job


def complete_job(db: Session, job: ProcessingJob) -> ProcessingJob:
    """Mark a running job completed at 100%."""
    job.status = JobStatus.COMPLETED
    job.progress = 1.0
    job.completed_at = utcnow()
    job.error = None
    db.commit()
    db.refresh(job)
    return job


def fail_job(db: Session, job: ProcessingJob, error: str) -> ProcessingJob:
    """Mark a running job failed with an error message."""
    job.status = JobStatus.FAILED
    job.error = error[:2000]
    job.completed_at = utcnow()
    db.commit()
    db.refresh(job)
    return job


def cancel_job(db: Session, job: ProcessingJob) -> ProcessingJob:
    """Cancel a job. Queued jobs never run; running jobs stop at the next check."""
    if job.status not in ACTIVE_STATUSES:
        raise JobStateError(f"Job {job.id} is {job.status.value}, cannot cancel")
    job.status = JobStatus.CANCELLED
    job.completed_at = utcnow()
    db.commit()
    db.refresh(job)
    return job


def raise_if_cancelled(db: Session, job: ProcessingJob) -> None:
    """Abort a running stage cooperatively when the job was cancelled."""
    db.refresh(job)
    if job.status == JobStatus.CANCELLED:
        raise JobCancelledError(f"Job {job.id} was cancelled")


class JobCancelledError(RuntimeError):
    """Raised inside handlers when a cooperative cancellation is detected."""
