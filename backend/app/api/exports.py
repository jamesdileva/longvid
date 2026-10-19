"""Exports API: render clips through delivery presets (roadmap Phase 18)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import __version__
from app.database import get_db
from app.editing import UnknownExportPresetError, get_export_preset, list_export_presets
from app.models.clip import ClipStatus
from app.models.processing import JobType
from app.schemas import ExportCreate, ExportPresetRead, ExportRead
from app.services import clips as clip_service
from app.services import exports as export_service
from app.services import jobs as job_service
from app.services import projects as project_service
from app.services.workspace import WorkspaceError, asset_path
from app.workers.queue import get_queue

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["exports"])


@router.get("/export-presets", response_model=list[ExportPresetRead])
def list_presets() -> list[ExportPresetRead]:
    """The available export presets."""
    return [ExportPresetRead.model_validate(preset) for preset in list_export_presets()]


@router.post(
    "/clips/{clip_id}/export",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_export(clip_id: int, payload: ExportCreate, db: DbSession) -> dict:
    """Queue an export of a ready clip through a delivery preset."""
    clip = clip_service.get_clip(db, clip_id)
    if clip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")
    if clip.status != ClipStatus.READY:
        raise HTTPException(status.HTTP_409_CONFLICT, "Clip has not been rendered yet")
    if job_service.active_job_exists(db, clip.video_id, JobType.EXPORT):
        raise HTTPException(status.HTTP_409_CONFLICT, "An export is already active")
    try:
        preset = get_export_preset(payload.preset)
    except UnknownExportPresetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    export = export_service.create_export(db, clip, preset=preset, app_version=__version__)
    job = job_service.create_job(db, clip.video_id, JobType.EXPORT)
    get_queue().submit(job.id)
    return {"job_id": job.id, "export_id": export.id, "status": export.status.value}


@router.get("/exports/{export_id}", response_model=ExportRead)
def get_export(export_id: int, db: DbSession) -> ExportRead:
    """One export by id."""
    export = export_service.get_export(db, export_id)
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export not found")
    return ExportRead.model_validate(export)


@router.get("/projects/{project_id}/exports", response_model=list[ExportRead])
def list_project_exports(project_id: str, db: DbSession) -> list[ExportRead]:
    """All exports across a project's clips, newest first."""
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    exports = export_service.list_project_exports(db, project_id)
    return [ExportRead.model_validate(export) for export in exports]


@router.get("/exports/{export_id}/file")
def get_export_file(export_id: int, db: DbSession) -> FileResponse:
    """Download a rendered export file."""
    export = export_service.get_export(db, export_id)
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export not found")
    try:
        path = asset_path(export.project_id, export.file_path)
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export file not rendered")
    return FileResponse(path, media_type="video/mp4", filename=f"export-{export_id}.mp4")
