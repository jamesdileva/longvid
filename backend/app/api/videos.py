"""Videos API: import, list, inspect, and serve media assets."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JobProcessRequest, JobRead, VideoImportRequest, VideoRead
from app.services import jobs as job_service
from app.services import projects as project_service
from app.services import videos as video_service
from app.services.videos import VideoImportError
from app.services.workspace import WorkspaceError, asset_path
from app.workers.queue import get_queue

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["videos"])


@router.post(
    "/projects/{project_id}/videos",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
)
def import_video(project_id: str, payload: VideoImportRequest, db: DbSession) -> VideoRead:
    """Copy a local video into the project, probe it, and generate previews.

    Import is synchronous (seconds for typical files); background jobs for
    expensive stages arrive in Sprint 4.3.
    """
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    try:
        video = video_service.import_video(db, project, Path(payload.path))
    except VideoImportError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:  # ffmpeg probe/render failures
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return VideoRead.model_validate(video)


@router.get("/projects/{project_id}/videos", response_model=list[VideoRead])
def list_videos(project_id: str, db: DbSession) -> list[VideoRead]:
    """List all videos imported into a project."""
    return [VideoRead.model_validate(v) for v in video_service.list_videos(db, project_id)]


@router.get("/videos/{video_id}", response_model=VideoRead)
def get_video(video_id: int, db: DbSession) -> VideoRead:
    """Fetch one video with its full metadata."""
    video = video_service.get_video(db, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return VideoRead.model_validate(video)


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: DbSession) -> None:
    """Remove a video and its generated workspace assets."""
    if not video_service.delete_video(db, video_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")


@router.post(
    "/videos/{video_id}/process", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED
)
def process_video(video_id: int, payload: JobProcessRequest, db: DbSession) -> JobRead:
    """Queue a background job for a video and return immediately.

    Long work never blocks the HTTP request (architecture §19); the client
    polls ``GET /api/jobs/{id}`` for progress.
    """
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    if job_service.active_job_exists(db, video_id, payload.type):
        raise HTTPException(status.HTTP_409_CONFLICT, "A job of this type is already active")

    job = job_service.create_job(db, video_id, payload.type)
    get_queue().submit(job.id)
    return JobRead.model_validate(job)


@router.get("/videos/{video_id}/thumbnail")
def get_thumbnail(video_id: int, db: DbSession) -> FileResponse:
    """Serve the generated thumbnail JPEG."""
    return _asset_response(db, video_id, "thumbnail_path", "image/jpeg")


@router.get("/videos/{video_id}/preview")
def get_preview(video_id: int, db: DbSession) -> FileResponse:
    """Serve the generated preview MP4."""
    return _asset_response(db, video_id, "preview_path", "video/mp4")


def _asset_response(db: Session, video_id: int, field: str, media_type: str) -> FileResponse:
    video = video_service.get_video(db, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    try:
        path = asset_path(video.project_id, getattr(video, field))
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not generated")
    return FileResponse(path, media_type=media_type)
