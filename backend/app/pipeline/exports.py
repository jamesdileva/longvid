"""Export rendering stage (roadmap Phase 18): clip -> delivery preset file.

Each export row is a reproducible render request; this stage transcodes every
pending/failed export for a video. A single failing export is marked failed
without aborting the rest of the batch.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.clip import ClipStatus
from app.models.export import ExportStatus
from app.models.processing import ProcessingJob
from app.services import exports as export_service
from app.services import ffmpeg_service
from app.services import jobs as job_service
from app.services.ffmpeg_service import FFmpegError
from app.services.workspace import WorkspaceError, asset_path

logger = logging.getLogger("longvid.exports")


def export_clips(db: Session, job: ProcessingJob) -> None:
    """Render all pending/failed exports for the job's video."""
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")

    pending = export_service.exports_to_render(db, video.id)
    if not pending:
        job_service.complete_job(db, job)
        return

    total = len(pending)
    for index, export in enumerate(pending):
        _render_one(db, video.project_id, export)
        job_service.raise_if_cancelled(db, job)
        job_service.update_progress(db, job, (index + 1) / total)

    job_service.complete_job(db, job)


def _render_one(db: Session, project_id: str, export) -> None:
    """Transcode one export, recording success or failure on the row."""
    export.status = ExportStatus.PROCESSING
    db.commit()

    clip = export.clip
    source = _clip_source(project_id, clip)
    if source is None:
        export.status = ExportStatus.FAILED
        export.error = "Clip file is not rendered yet"
        db.commit()
        return

    settings = export.settings or {}
    output = export_service.export_output_path(project_id, export.id)
    try:
        ffmpeg_service.export_clip(
            source,
            output,
            video_codec=export.video_codec,
            audio_codec=export.audio_codec,
            crf=int(settings.get("crf", 21)),
            encoder_preset=str(settings.get("encoder_preset", "medium")),
            audio_bitrate=str(settings.get("audio_bitrate", "192k")),
            max_width=settings.get("max_width"),
            container=export.container,
        )
        export.file_path = export_service.relative_export_path(export.id)
        export.file_size_bytes = output.stat().st_size
        export.status = ExportStatus.READY
        export.error = None
    except FFmpegError as exc:
        logger.warning("Export %s failed to render: %s", export.id, exc)
        export.status = ExportStatus.FAILED
        export.error = str(exc)
    db.commit()


def _clip_source(project_id: str, clip) -> Path | None:
    """Absolute path of a clip's rendered MP4, when it is ready."""
    if clip is None or clip.status != ClipStatus.READY or not clip.file_path:
        return None
    try:
        path = asset_path(project_id, clip.file_path)
    except WorkspaceError:
        return None
    return path if path is not None and path.is_file() else None
