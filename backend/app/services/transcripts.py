"""Transcript persistence: store and replace segment sets."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transcript import Transcript, TranscriptSegment
from app.models.video import Video
from app.providers.transcription.base import SegmentResult
from app.schemas.transcripts import TranscriptRead


def get_transcript_for_video(db: Session, video_id: int) -> Transcript | None:
    """The transcript for a video, or ``None``."""
    stmt = select(Transcript).where(Transcript.video_id == video_id)
    return db.execute(stmt).scalars().first()


def replace_transcript(
    db: Session,
    video: Video,
    segments: Sequence[SegmentResult],
    *,
    language: str | None = None,
) -> Transcript:
    """Replace a video's transcript with a fresh set of segments.

    Re-running transcription is safe: the old segments are deleted and the new
    ones take their place.
    """
    existing = get_transcript_for_video(db, video.id)
    if existing is not None:
        db.delete(existing)
        db.flush()

    transcript = Transcript(
        video_id=video.id,
        language=language,
        duration_seconds=video.duration_seconds,
    )
    db.add(transcript)
    db.flush()

    for position, segment in enumerate(segments):
        db.add(
            TranscriptSegment(
                transcript_id=transcript.id,
                position=position,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                text=segment.text,
                confidence=segment.confidence,
            )
        )
    db.commit()
    db.refresh(transcript)
    return transcript


def to_read_model(transcript: Transcript) -> TranscriptRead:
    """Convert a transcript entity into its API representation."""
    return TranscriptRead(
        id=transcript.id,
        video_id=transcript.video_id,
        language=transcript.language,
        duration_seconds=transcript.duration_seconds,
        created_at=transcript.created_at,
        segments=[
            {
                "id": segment.id,
                "position": segment.position,
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "text": segment.text,
                "confidence": segment.confidence,
            }
            for segment in transcript.segments
        ],
    )
