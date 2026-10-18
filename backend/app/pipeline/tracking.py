"""Subject tracking stage (roadmap 11.3): store a subject track on the video.

Runs the configured vision provider over the source and persists the result as
``video.subject_track``. Clip creation later turns that track into a smooth
dynamic crop. If the provider's optional dependency is missing the stage
degrades gracefully to an empty track so the video still works with the static
center crop (architecture §23).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.processing import ProcessingJob
from app.providers.vision import SubjectTrack, VisionProviderUnavailableError, get_vision_provider
from app.services import jobs as job_service
from app.services.workspace import WorkspaceError, asset_path

logger = logging.getLogger("longvid.tracking")


def track_subjects(db: Session, job: ProcessingJob) -> None:
    """Detect subject positions across the job's video and store the track."""
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")

    try:
        source = asset_path(video.project_id, f"source/{video.relative_path}")
    except WorkspaceError as exc:
        raise ValueError(f"Video source not accessible: {exc}") from exc
    if source is None or not source.is_file():
        raise ValueError(f"Source file missing: {video.relative_path}")

    settings = get_settings()
    provider_name = settings.vision_provider
    try:
        provider = get_vision_provider(settings)
        track = provider.track_subjects(source, duration_seconds=video.duration_seconds or 0.0)
        provider_name = provider.name
    except VisionProviderUnavailableError as exc:
        logger.warning("Vision provider unavailable, storing empty track: %s", exc)
        track = SubjectTrack(samples=())

    video.subject_track = {"provider": provider_name, **track.to_dict()}
    job_service.update_progress(db, job, 1.0)
    db.commit()
    job_service.complete_job(db, job)
