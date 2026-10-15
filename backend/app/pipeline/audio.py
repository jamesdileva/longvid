"""The audio extraction pipeline stage (implementation-guide §11).

Produces the mono 16 kHz WAV that the Whisper stage (Sprint 5) consumes.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.processing import ProcessingJob
from app.services import ffmpeg_service
from app.services import jobs as job_service
from app.services.workspace import WorkspaceError, ensure_subdir, workspace_path


def extract_audio(db: Session, job: ProcessingJob) -> None:
    """Extract mono 16 kHz WAV from a video and persist its workspace path."""
    settings = get_settings()
    job_service.update_progress(db, job, 0.1)

    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")

    try:
        source_dir = workspace_path(video.project_id) / "source"
        source = source_dir / video.relative_path
        audio_dir = ensure_subdir(video.project_id, "media/audio")
    except WorkspaceError as exc:
        raise ValueError(f"Video source not accessible: {exc}") from exc

    if not source.is_file():
        raise ValueError(f"Source file missing: {source.name}")

    output = audio_dir / f"{video.id}.wav"
    ffmpeg_service.extract_audio(
        source, output, settings.audio_sample_rate, settings.audio_channels
    )

    job_service.raise_if_cancelled(db, job)  # cooperative stop before persisting
    job_service.update_progress(db, job, 0.9)

    video.audio_path = f"media/audio/{video.id}.wav"
    db.commit()
    job_service.complete_job(db, job)
