"""Clips API: turn candidates into rendered MP4 clips (roadmap Phase 9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.editing import UnknownProfileError, get_profile, trim_clip_range
from app.models.candidate import CandidateStatus, ClipCandidate
from app.models.processing import JobType
from app.schemas import ClipGenerateRequest, ClipRead, ClipUpdate
from app.services import analysis as analysis_service
from app.services import candidates as candidate_service
from app.services import clips as clip_service
from app.services import jobs as job_service
from app.services import projects as project_service
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from app.services.workspace import WorkspaceError, asset_path
from app.workers.queue import get_queue

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["clips"])

SELECTION_SIZES = {"top5": 5, "top10": 10}


@router.post(
    "/videos/{video_id}/generate-clips",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_clips(video_id: int, payload: ClipGenerateRequest, db: DbSession) -> dict:
    """Create clip definitions for the chosen candidates and queue rendering."""
    video = video_service.get_video(db, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    if job_service.active_job_exists(db, video_id, JobType.GENERATE_CLIP):
        raise HTTPException(status.HTTP_409_CONFLICT, "Clip generation is already active")

    candidates = candidate_service.list_video_candidates(db, video_id)
    if not candidates:
        raise HTTPException(status.HTTP_409_CONFLICT, "No candidates; detect highlights first")

    try:
        profile = get_profile(payload.editing_profile)
    except UnknownProfileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    trim_context = _trim_context(db, video)
    existing = clip_service.existing_candidate_ids(db, video_id)
    selected = _select_candidates(candidates, payload, existing)
    if not selected:
        raise HTTPException(status.HTTP_409_CONFLICT, "No new candidates to clip")

    for candidate in selected:
        trimmed = trim_clip_range(
            candidate.start_seconds,
            candidate.end_seconds,
            **trim_context,
        )
        clip_service.create_clip(
            db,
            video_id,
            start_seconds=trimmed.start_seconds,
            end_seconds=trimmed.end_seconds,
            title=_title_for(candidate),
            candidate_id=candidate.id,
            profile=profile,
            trim=trimmed.trim,
        )
    db.commit()

    job = job_service.create_job(db, video_id, JobType.GENERATE_CLIP)
    get_queue().submit(job.id)
    return {"job_id": job.id, "status": job.status.value, "clip_count": len(selected)}


def _trim_context(db: DbSession, video) -> dict:
    """Reusable keyword arguments for trim_clip_range, per video."""
    settings = get_settings()
    segments = transcript_service.get_transcript_for_video(db, video.id)
    transcript_segments = [
        (segment.start_seconds, segment.end_seconds, segment.text)
        for segment in (segments.segments if segments else [])
    ]
    silences = [
        (event.start_seconds, event.end_seconds)
        for event in analysis_service.list_events(db, video.id)
        if event.type == "silence"
    ]
    return {
        "segments": transcript_segments,
        "silences": silences,
        "duration": video.duration_seconds or 0.0,
        "sentence_tolerance": settings.trim_sentence_tolerance_seconds,
        "pre_roll": settings.trim_pre_roll_seconds,
        "post_roll": settings.trim_post_roll_seconds,
    }


@router.get("/videos/{video_id}/clips", response_model=list[ClipRead])
def list_video_clips(video_id: int, db: DbSession) -> list[ClipRead]:
    """Clips for a video, newest first."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return [ClipRead.model_validate(clip) for clip in clip_service.list_video_clips(db, video_id)]


@router.get("/projects/{project_id}/clips", response_model=list[ClipRead])
def list_project_clips(project_id: str, db: DbSession) -> list[ClipRead]:
    """All clips across a project's videos, newest first."""
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return [
        ClipRead.model_validate(clip) for clip in clip_service.list_project_clips(db, project_id)
    ]


@router.get("/clips/{clip_id}", response_model=ClipRead)
def get_clip(clip_id: int, db: DbSession) -> ClipRead:
    """One clip by id."""
    clip = clip_service.get_clip(db, clip_id)
    if clip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")
    return ClipRead.model_validate(clip)


@router.patch("/clips/{clip_id}", response_model=ClipRead)
def update_clip(clip_id: int, payload: ClipUpdate, db: DbSession) -> ClipRead:
    """Update a clip's editable fields."""
    clip = clip_service.update_clip(db, clip_id, payload.title)
    if clip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")
    return ClipRead.model_validate(clip)


@router.delete("/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clip(clip_id: int, db: DbSession) -> None:
    """Delete a clip and its rendered file."""
    if not clip_service.delete_clip(db, clip_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")


@router.get("/clips/{clip_id}/file")
def get_clip_file(clip_id: int, db: DbSession) -> FileResponse:
    """Stream a rendered clip MP4."""
    clip = clip_service.get_clip(db, clip_id)
    if clip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")
    try:
        path = asset_path(clip.video.project_id, clip.file_path)
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip file not rendered")
    return FileResponse(path, media_type="video/mp4")


def _select_candidates(
    candidates: list[ClipCandidate], payload: ClipGenerateRequest, existing: set[int]
) -> list[ClipCandidate]:
    """Candidates to clip, in score order, excluding any already clipped.

    The selection (top N / all / accepted / explicit ids) is applied against
    the full ranked candidate list first, so "Top 5" always means the same
    five candidates regardless of what has already been clipped.
    """
    if payload.candidate_ids is not None:
        wanted = set(payload.candidate_ids)
        chosen = [candidate for candidate in candidates if candidate.id in wanted]
    elif payload.selection == "accepted":
        chosen = [c for c in candidates if c.status == CandidateStatus.ACCEPTED]
    elif payload.selection == "all":
        chosen = list(candidates)
    else:
        chosen = candidates[: SELECTION_SIZES[payload.selection]]
    return [candidate for candidate in chosen if candidate.id not in existing]


def _title_for(candidate: ClipCandidate) -> str:
    reason = (candidate.reason or "").strip()
    if reason:
        return reason[:255]
    category = candidate.category or "Highlight"
    return f"{category} at {candidate.start_seconds:.0f}s"[:255]
