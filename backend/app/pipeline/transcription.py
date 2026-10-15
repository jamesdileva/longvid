"""The transcription pipeline stage (implementation-guide §12).

Consumes the mono 16 kHz WAV produced by EXTRACT_AUDIO and persists ordered,
timestamped segments — the raw material for highlight detection later.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.processing import ProcessingJob
from app.providers.transcription import ProviderUnavailableError, get_transcription_provider
from app.services import jobs as job_service
from app.services import transcripts as transcript_service
from app.services.workspace import WorkspaceError, asset_path


def transcribe_video(db: Session, job: ProcessingJob) -> None:
    """Transcribe a video's extracted audio and store the segments."""
    settings = get_settings()
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")
    if not video.audio_path:
        raise ValueError("Extract audio before transcribing")

    try:
        audio = asset_path(video.project_id, video.audio_path)
    except WorkspaceError as exc:
        raise ValueError(f"Audio asset not accessible: {exc}") from exc
    if audio is None or not audio.is_file():
        raise ValueError("Extracted audio file is missing; run audio extraction again")

    try:
        provider = get_transcription_provider(settings)
    except ProviderUnavailableError as exc:
        raise ValueError(str(exc)) from exc

    job_service.update_progress(db, job, 0.3)
    segments = provider.transcribe(audio, language=settings.whisper_language)
    job_service.update_progress(db, job, 0.8)

    job_service.raise_if_cancelled(db, job)
    transcript_service.replace_transcript(db, video, segments, language=settings.whisper_language)
    job_service.complete_job(db, job)
