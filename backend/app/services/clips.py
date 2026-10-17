"""Clip persistence, selection, and file lifecycle."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editing import DEFAULT_PROFILE_KEY, EditingProfile, build_editing_plan, get_profile
from app.models.clip import Clip, ClipStatus
from app.models.video import Video
from app.services.workspace import WorkspaceError, asset_path, ensure_subdir

RENDERABLE_STATUSES = (ClipStatus.PENDING, ClipStatus.FAILED)


def create_clip(
    db: Session,
    video_id: int,
    *,
    start_seconds: float,
    end_seconds: float,
    title: str | None,
    candidate_id: int | None = None,
    profile: EditingProfile | None = None,
    trim: dict | None = None,
) -> Clip:
    """Snapshot a timeline definition as a pending clip.

    The range is trimmed to natural boundaries by the caller, clamped to the
    profile's maximum duration here, and recorded with the resolved editing
    plan so the render is reproducible (guide §21/§24).
    """
    profile = profile or get_profile(DEFAULT_PROFILE_KEY)
    video = db.get(Video, video_id)
    source = f"source/{video.relative_path}" if video is not None else ""
    plan = build_editing_plan(
        profile, source=source, start_seconds=start_seconds, end_seconds=end_seconds
    )
    if trim is not None:
        plan["trim"] = trim
    start = plan["start"]
    end = plan["end"]
    clip = Clip(
        video_id=video_id,
        candidate_id=candidate_id,
        title=title,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=max(end - start, 0.0),
        editing_profile=profile.key,
        editing_plan=plan,
        status=ClipStatus.PENDING,
    )
    db.add(clip)
    return clip


def list_video_clips(db: Session, video_id: int) -> list[Clip]:
    """Clips of a video, newest first."""
    stmt = (
        select(Clip)
        .where(Clip.video_id == video_id)
        .order_by(Clip.created_at.desc(), Clip.id.desc())
    )
    return list(db.execute(stmt).scalars())


def list_project_clips(db: Session, project_id: str) -> list[Clip]:
    """All clips across a project's videos, newest first."""
    stmt = (
        select(Clip)
        .join(Video, Video.id == Clip.video_id)
        .where(Video.project_id == project_id)
        .order_by(Clip.created_at.desc(), Clip.id.desc())
    )
    return list(db.execute(stmt).scalars())


def get_clip(db: Session, clip_id: int) -> Clip | None:
    """One clip by id, or ``None``."""
    return db.get(Clip, clip_id)


def existing_candidate_ids(db: Session, video_id: int) -> set[int]:
    """Candidate ids already turned into a clip for a video."""
    stmt = select(Clip.candidate_id).where(
        Clip.video_id == video_id, Clip.candidate_id.is_not(None)
    )
    return {row for row in db.execute(stmt).scalars() if row is not None}


def clips_to_render(db: Session, video_id: int) -> list[Clip]:
    """Clips awaiting (or needing a retry of) rendering."""
    stmt = (
        select(Clip)
        .where(Clip.video_id == video_id, Clip.status.in_(RENDERABLE_STATUSES))
        .order_by(Clip.id)
    )
    return list(db.execute(stmt).scalars())


def update_clip(db: Session, clip_id: int, title: str | None) -> Clip | None:
    """Update editable clip fields."""
    clip = get_clip(db, clip_id)
    if clip is None:
        return None
    if title is not None:
        clip.title = title.strip() or None
    db.commit()
    db.refresh(clip)
    return clip


def delete_clip(db: Session, clip_id: int) -> bool:
    """Delete a clip row and unlink its rendered file."""
    clip = get_clip(db, clip_id)
    if clip is None:
        return False
    _unlink_file(clip)
    db.delete(clip)
    db.commit()
    return True


def clip_output_path(project_id: str, clip_id: int) -> Path:
    """Absolute path of a clip's rendered MP4."""
    return ensure_subdir(project_id, "clips/generated") / f"{clip_id}.mp4"


def delete_files_for_video(db: Session, video_id: int) -> None:
    """Best-effort removal of a video's rendered clip files (before row deletion)."""
    for clip in list_video_clips(db, video_id):
        _unlink_file(clip)


def relative_clip_path(clip_id: int) -> str:
    """Workspace-relative path stored on the clip row."""
    return f"clips/generated/{clip_id}.mp4"


def _unlink_file(clip: Clip) -> None:
    if not clip.file_path:
        return
    try:
        path = asset_path(clip.video.project_id, clip.file_path)
    except WorkspaceError:
        return
    if path is not None and path.is_file():
        path.unlink()
