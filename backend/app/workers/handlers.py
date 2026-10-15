"""Job handler registry: maps JobType to pipeline stage functions."""

from __future__ import annotations

from app.models.processing import JobType
from app.pipeline.audio import extract_audio
from app.pipeline.transcription import transcribe_video
from app.workers.queue import JobHandler

HANDLERS: dict[JobType, JobHandler] = {
    JobType.EXTRACT_AUDIO: extract_audio,
    JobType.TRANSCRIBE: transcribe_video,
}
