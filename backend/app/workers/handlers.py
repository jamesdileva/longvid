"""Job handler registry: maps JobType to pipeline stage functions."""

from __future__ import annotations

from app.models.processing import JobType
from app.pipeline.analysis import analyze_video
from app.pipeline.audio import extract_audio
from app.pipeline.candidates import generate_candidates, rescore_candidates
from app.pipeline.clips import generate_clips
from app.pipeline.transcription import transcribe_video
from app.workers.queue import JobHandler

HANDLERS: dict[JobType, JobHandler] = {
    JobType.EXTRACT_AUDIO: extract_audio,
    JobType.TRANSCRIBE: transcribe_video,
    JobType.ANALYZE_EVENTS: analyze_video,
    JobType.GENERATE_CANDIDATES: generate_candidates,
    JobType.SCORE_CANDIDATES: rescore_candidates,
    JobType.GENERATE_CLIP: generate_clips,
}
