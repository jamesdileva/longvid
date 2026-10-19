"""Export persistence and file lifecycle (roadmap Phase 18; guide §24)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editing import ExportPreset
from app.models.clip import Clip
from app.models.export import Export, ExportStatus
from app.services.workspace import WorkspaceError, asset_path, ensure_subdir

RENDERABLE_STATUSES = (ExportStatus.PENDING, ExportStatus.FAILED)


def create_export(db: Session, clip: Clip, *, preset: ExportPreset, app_version: str) -> Export:
    """Snapshot an export request against a clip (reproducibility per §24).

    The preset settings, the clip's editing plan and the application version
    are all frozen onto the row so the file can be reproduced or audited later.
    """
    export = Export(
        clip_id=clip.id,
        project_id=clip.video.project_id,
        preset=preset.key,
        container=preset.container,
        video_codec=preset.video_codec,
        audio_codec=preset.audio_codec,
        settings={
            "crf": preset.crf,
            "encoder_preset": preset.encoder_preset,
            "max_width": preset.max_width,
            "audio_bitrate": preset.audio_bitrate,
        },
        editing_profile=clip.editing_profile,
        plan_snapshot=clip.editing_plan,
        app_version=app_version,
        status=ExportStatus.PENDING,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def get_export(db: Session, export_id: int) -> Export | None:
    """One export by id, or ``None``."""
    return db.get(Export, export_id)


def list_clip_exports(db: Session, clip_id: int) -> list[Export]:
    """Exports for a clip, newest first."""
    stmt = select(Export).where(Export.clip_id == clip_id).order_by(Export.id.desc())
    return list(db.execute(stmt).scalars())


def list_project_exports(db: Session, project_id: str) -> list[Export]:
    """All exports across a project, newest first."""
    stmt = select(Export).where(Export.project_id == project_id).order_by(Export.id.desc())
    return list(db.execute(stmt).scalars())


def exports_to_render(db: Session, video_id: int) -> list[Export]:
    """Pending/failed exports for a video's clips, oldest first."""
    stmt = (
        select(Export)
        .join(Clip, Export.clip_id == Clip.id)
        .where(Clip.video_id == video_id, Export.status.in_(RENDERABLE_STATUSES))
        .order_by(Export.id)
    )
    return list(db.execute(stmt).scalars())


def export_output_path(project_id: str, export_id: int) -> Path:
    """Absolute path of a rendered export file."""
    return ensure_subdir(project_id, "exports") / f"{export_id}.mp4"


def relative_export_path(export_id: int) -> str:
    """Workspace-relative export path stored on the row."""
    return f"exports/{export_id}.mp4"


def delete_exports_for_clip(db: Session, clip_id: int) -> None:
    """Unlink a clip's export files and delete their rows."""
    for export in list_clip_exports(db, clip_id):
        _unlink(export)
        db.delete(export)
    db.commit()


def delete_exports_for_video(db: Session, video_id: int) -> None:
    """Unlink and delete every export belonging to a video's clips."""
    stmt = select(Export).join(Clip, Export.clip_id == Clip.id).where(Clip.video_id == video_id)
    for export in list(db.execute(stmt).scalars()):
        _unlink(export)
        db.delete(export)
    db.commit()


def _unlink(export: Export) -> None:
    if not export.file_path:
        return
    try:
        path = asset_path(export.project_id, export.file_path)
    except WorkspaceError:
        return
    if path is not None and path.is_file():
        path.unlink()
