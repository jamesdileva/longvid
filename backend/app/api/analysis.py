"""Analysis API: scenes and events for a video."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EventRead, SceneRead
from app.services import analysis as analysis_service
from app.services import videos as video_service

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["analysis"])


@router.get("/videos/{video_id}/scenes", response_model=list[SceneRead])
def list_scenes(video_id: int, db: DbSession) -> list[SceneRead]:
    """Detected scenes for a video, in order."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return [SceneRead.model_validate(row) for row in analysis_service.list_scenes(db, video_id)]


@router.get("/videos/{video_id}/events", response_model=list[EventRead])
def list_events(video_id: int, db: DbSession) -> list[EventRead]:
    """Analysis events for a video, chronological."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return [
        EventRead.model_validate(_event_fields(row))
        for row in analysis_service.list_events(db, video_id)
    ]


def _event_fields(row) -> dict:
    """Flatten an event row, decoding its JSON payload."""
    payload = None
    if row.payload:
        try:
            payload = json.loads(row.payload)
        except json.JSONDecodeError:
            payload = None
    return {
        "id": row.id,
        "video_id": row.video_id,
        "type": row.type,
        "start_seconds": row.start_seconds,
        "end_seconds": row.end_seconds,
        "confidence": row.confidence,
        "source": row.source,
        "payload": payload,
        "created_at": row.created_at,
    }
