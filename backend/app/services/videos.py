"""Video ingest: import local files into a project workspace.

Import deliberately performs no AI analysis (see implementation-guide.md §9).
Steps: validate -> copy -> probe -> thumbnail -> preview -> persist.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.project import Project
from app.models.video import Video, VideoStatus
from app.services import ffmpeg_service
from app.services.workspace import WorkspaceError, ensure_subdir, workspace_path
from app.utils.time import utcnow


class VideoImportError(ValueError):
    """Raised when a file cannot be imported as a project video."""


def list_videos(db: Session, project_id: str) -> list[Video]:
    """All videos of a project, newest first."""
    stmt = select(Video).where(Video.project_id == project_id).order_by(Video.created_at.desc())
    return list(db.execute(stmt).scalars())


def get_video(db: Session, video_id: int) -> Video | None:
    """One video by id, or ``None``."""
    return db.get(Video, video_id)


def import_video(db: Session, project: Project, source_path: Path) -> Video:
    """Validate, copy, probe, thumbnail, and persist a video.

    The user-selected file is never modified; everything is generated inside
    the project workspace.
    """
    settings = get_settings()
    if source_path.suffix.lower() not in settings.allowed_video_extensions:
        allowed = ", ".join(settings.allowed_video_extensions)
        raise VideoImportError(f"Unsupported file type. Allowed: {allowed}")
    if not source_path.is_file():
        raise VideoImportError(f"File does not exist: {source_path}")

    try:
        source_dir = ensure_subdir(project.id, "source")
        thumb_dir = ensure_subdir(project.id, "media/thumbnails")
        preview_dir = ensure_subdir(project.id, "media/previews")
    except WorkspaceError as exc:
        raise VideoImportError(str(exc)) from exc

    stored = ffmpeg_service.store_import_copy(source_path, source_dir)
    info = ffmpeg_service.probe_file(stored)

    video = Video(
        project_id=project.id,
        filename=source_path.name,
        relative_path=stored.name,
        status=VideoStatus.READY,
        duration_seconds=info.duration_seconds,
        width=info.width,
        height=info.height,
        fps=info.fps,
        video_codec=info.video_codec,
        audio_codec=info.audio_codec,
        sample_rate=info.sample_rate,
        channels=info.channels,
        file_size_bytes=info.file_size_bytes,
    )
    db.add(video)
    db.flush()  # assigns video.id before asset filenames

    # Generated assets are stored under media/ keyed by video id.
    video.thumbnail_path = f"media/thumbnails/{video.id}.jpg"
    video.preview_path = f"media/previews/{video.id}.mp4"

    # Thumbnail from a few seconds in (mid-point for very short videos).
    at_seconds = min(3.0, info.duration_seconds / 2)
    ffmpeg_service.generate_thumbnail(
        stored, thumb_dir / f"{video.id}.jpg", at_seconds, settings.thumbnail_width
    )
    ffmpeg_service.generate_preview(
        stored, preview_dir / f"{video.id}.mp4", info.duration_seconds, settings.preview_width
    )

    db.commit()
    db.refresh(video)
    _touch_project(db, project)
    return video


def delete_video(db: Session, video_id: int) -> bool:
    """Remove a video row and its generated workspace assets.

    The user's original file outside the workspace is never touched.
    """
    video = get_video(db, video_id)
    if video is None:
        return False

    project = video.project
    _remove_assets(video)
    db.delete(video)
    db.commit()
    _touch_project(db, project)
    return True


def _remove_assets(video: Video) -> None:
    """Best-effort removal of workspace files for a video."""
    try:
        workspace = workspace_path(video.project_id)
    except WorkspaceError:
        return
    for relative in (video.relative_path, video.thumbnail_path, video.preview_path):
        if not relative:
            continue
        path = (workspace / relative).resolve()
        if path.is_file() and _is_inside(path, workspace):
            path.unlink()


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _touch_project(db: Session, project: Project) -> None:
    """Keep the project's updated_at meaningful for 'last modified' UI."""
    project.updated_at = utcnow()
    db.commit()
