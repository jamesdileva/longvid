"""Background job runner.

A small thread pool executes jobs submitted by the API layer. Each job runs
in its own session; the pool is deliberately in-process because LongVid is a
single-user local application.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_sessionmaker
from app.models.processing import JobStatus, ProcessingJob
from app.services import jobs as job_service

logger = logging.getLogger("longvid.jobs")

JobHandler = Callable[[Session, ProcessingJob], None]


def run_job(job_id: int) -> None:
    """Execute one job end to end in a worker thread."""
    db = get_sessionmaker()()
    try:
        job = job_service.get_job(db, job_id)
        if job is None:
            return
        if job.status != JobStatus.QUEUED:
            # cancelled before the worker picked it up
            return

        from app.workers.handlers import HANDLERS

        handler = HANDLERS.get(job.type)
        if handler is None:
            job_service.fail_job(db, job, f"No handler registered for job type {job.type.value}")
            return

        job_service.mark_running(db, job)
        logger.info("Job %s (%s) started", job.id, job.type.value)
        handler(db, job)
        logger.info("Job %s completed", job.id)
    except job_service.JobCancelledError:
        logger.info("Job %s cancelled by user", job_id)
    except Exception as exc:  # worker failures must never kill the process
        logger.exception("Job %s failed", job_id)
        db.rollback()
        job = job_service.get_job(db, job_id)
        if job is not None and job.status == JobStatus.RUNNING:
            job_service.fail_job(db, job, str(exc))
    finally:
        db.close()


class JobQueue:
    """Thread pool wrapper with graceful shutdown."""

    def __init__(self, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, job_id: int) -> None:
        self._executor.submit(run_job, job_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    """Lazily create the process-wide job queue."""
    global _queue
    if _queue is None:
        _queue = JobQueue(get_settings().job_workers)
    return _queue


def shutdown_queue() -> None:
    """Stop accepting jobs and drop the singleton (used by tests/shutdown)."""
    global _queue
    if _queue is not None:
        _queue.shutdown()
        _queue = None
