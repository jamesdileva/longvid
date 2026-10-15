"""Transcripts API: fetch stored transcripts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TranscriptRead
from app.services import transcripts as transcript_service
from app.services import videos as video_service

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(tags=["transcripts"])


@router.get("/videos/{video_id}/transcript", response_model=TranscriptRead)
def get_transcript(video_id: int, db: DbSession) -> TranscriptRead:
    """The transcript for a video, segments ordered by position."""
    if video_service.get_video(db, video_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    transcript = transcript_service.get_transcript_for_video(db, video_id)
    if transcript is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No transcript yet")
    return transcript_service.to_read_model(transcript)
