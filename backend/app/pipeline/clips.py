"""Clip rendering stage (roadmap 9.2): candidates -> MP4 files.

Each clip row is a timeline definition; this stage renders every pending clip
for a video with FFmpeg. A single failing clip is marked failed without
aborting the rest of the batch.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.clip import ClipStatus
from app.models.processing import ProcessingJob
from app.services import clips as clip_service
from app.services import ffmpeg_service
from app.services import jobs as job_service
from app.services.ffmpeg_service import FFmpegError
from app.services.workspace import WorkspaceError, asset_path

logger = logging.getLogger("longvid.clips")


def generate_clips(db: Session, job: ProcessingJob) -> None:
    """Render all pending/failed clips for the job's video."""
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")

    try:
        source = asset_path(video.project_id, f"source/{video.relative_path}")
    except WorkspaceError as exc:
        raise ValueError(f"Video source not accessible: {exc}") from exc
    if source is None or not source.is_file():
        raise ValueError(f"Source file missing: {video.relative_path}")

    pending = clip_service.clips_to_render(db, video.id)
    if not pending:
        job_service.complete_job(db, job)
        return

    total = len(pending)
    for index, clip in enumerate(pending):
        clip.status = ClipStatus.GENERATING
        db.commit()

        output = clip_service.clip_output_path(video.project_id, clip.id)
        try:
            ffmpeg_service.cut_clip(source, output, clip.start_seconds, clip.end_seconds)
            clip.file_path = clip_service.relative_clip_path(clip.id)
            clip.file_size_bytes = output.stat().st_size
            clip.status = ClipStatus.READY
            clip.error = None
        except FFmpegError as exc:
            logger.warning("Clip %s failed to render: %s", clip.id, exc)
            clip.status = ClipStatus.FAILED
            clip.error = str(exc)
        db.commit()

        job_service.raise_if_cancelled(db, job)
        job_service.update_progress(db, job, (index + 1) / total)

    job_service.complete_job(db, job)
