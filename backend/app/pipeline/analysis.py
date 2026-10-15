"""The deterministic analysis stage (roadmap 6.4: no LLM required).

Combines scene detection, audio feature extraction, and transcript coverage
into persisted scenes and events.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import audio as audio_analysis
from app.analysis.scenes import build_scenes
from app.config import Settings, get_settings
from app.models.processing import ProcessingJob
from app.models.transcript import Transcript, TranscriptSegment
from app.services import analysis as analysis_service
from app.services import ffmpeg_service
from app.services import jobs as job_service
from app.services.workspace import WorkspaceError, asset_path

EVENT_SOURCE = "deterministic"
EVENT_SCENE_CHANGE = "scene_change"
EVENT_SILENCE = "silence"
EVENT_AUDIO_SPIKE = "audio_spike"
EVENT_SPEECH_DENSITY = "speech_density"


def analyze_video(db: Session, job: ProcessingJob) -> None:
    """Detect scenes, analyze audio, and derive deterministic events."""
    settings = get_settings()
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")
    if not video.audio_path:
        raise ValueError("Extract audio before analysis")

    try:
        audio = asset_path(video.project_id, video.audio_path)
        source = asset_path(video.project_id, f"source/{video.relative_path}")
    except WorkspaceError as exc:
        raise ValueError(f"Workspace assets not accessible: {exc}") from exc
    if audio is None or not audio.is_file():
        raise ValueError("Extracted audio file is missing; run audio extraction again")
    if source is None or not source.is_file():
        raise ValueError("Source video is missing from the workspace")

    duration = video.duration_seconds or 0.0

    # 1. Scenes (6.1) — persisted even though candidates come later.
    job_service.update_progress(db, job, 0.1)
    boundaries = ffmpeg_service.detect_scenes(source, settings.scene_threshold)
    scenes = build_scenes(boundaries, duration_seconds=duration)
    analysis_service.replace_scenes(db, video.id, scenes)
    job_service.update_progress(db, job, 0.4)

    # 2. Audio analysis (6.2) -> events (6.4).
    levels = ffmpeg_service.audio_levels(audio)
    events: list[analysis_service.EventInput] = []

    for boundary in boundaries:
        if 0 < boundary.time_seconds < duration:
            events.append(
                analysis_service.EventInput(
                    type=EVENT_SCENE_CHANGE,
                    start_seconds=boundary.time_seconds,
                    end_seconds=boundary.time_seconds,
                    confidence=min(max(boundary.score, 0.0), 1.0),
                    source="scene_detection",
                    payload={"score": boundary.score},
                )
            )

    for silence in audio_analysis.detect_silence(
        levels,
        threshold_db=settings.silence_threshold_db,
        min_seconds=settings.min_silence_seconds,
    ):
        events.append(
            analysis_service.EventInput(
                type=EVENT_SILENCE,
                start_seconds=silence.start_seconds,
                end_seconds=silence.end_seconds,
                confidence=0.99,
                source="audio_analysis",
                payload={"mean_rms_db": silence.mean_rms_db},
            )
        )

    for peak in audio_analysis.detect_peaks(levels, threshold_db=settings.peak_threshold_db):
        events.append(
            analysis_service.EventInput(
                type=EVENT_AUDIO_SPIKE,
                start_seconds=peak.time_seconds,
                end_seconds=peak.time_seconds,
                confidence=0.9,
                source="audio_analysis",
                payload={"rms_db": peak.rms_db},
            )
        )
    job_service.update_progress(db, job, 0.7)

    # 3. Speech density (6.2) — only when a transcript exists.
    events.extend(_speech_density_events(db, video.id, duration, settings))

    job_service.raise_if_cancelled(db, job)
    analysis_service.replace_events(db, video.id, events)
    job_service.complete_job(db, job)


def _speech_density_events(
    db: Session, video_id: int, duration: float, settings: Settings
) -> list[analysis_service.EventInput]:
    """Emit speech_density events for windows with dense speech coverage."""
    if duration <= 0:
        return []
    spans = db.execute(segment_spans_sql(video_id)).all()
    if not spans:
        return []
    windows = audio_analysis.speech_density_windows(
        [(float(start), float(end)) for start, end in spans],
        total_duration=duration,
        window_seconds=settings.analysis_window_seconds,
    )
    return [
        analysis_service.EventInput(
            type=EVENT_SPEECH_DENSITY,
            start_seconds=window.start_seconds,
            end_seconds=window.end_seconds,
            confidence=min(window.density, 1.0),
            source="transcript_analysis",
            payload={"density": window.density, "window_seconds": settings.analysis_window_seconds},
        )
        for window in windows
        if window.density >= settings.speech_density_threshold
    ]


def segment_spans_sql(video_id: int):
    """SQL for a video's transcript segment spans."""
    return (
        select(TranscriptSegment.start_seconds, TranscriptSegment.end_seconds)
        .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
        .where(Transcript.video_id == video_id)
    )
