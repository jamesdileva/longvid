"""Candidate generation and scoring stage (roadmap 7.4/7.5).

Deterministic-first: semantic windows are built from the transcript, audio,
and scenes; windows are classified by the configured LLM when available
(falling back to deterministic signals), padded, and scored with the
configured weights.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.analysis import scoring
from app.analysis.windowing import WindowEvent, build_windows
from app.config import Settings, get_settings
from app.models.candidate import ClipCandidate
from app.models.processing import ProcessingJob
from app.providers.llm import (
    LLMProvider,
    LLMValidationError,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.services import analysis as analysis_service
from app.services import candidates as candidate_service
from app.services import jobs as job_service
from app.services import transcripts as transcript_service

logger = logging.getLogger("longvid.candidates")

# Signals considered "interesting enough" to become a candidate without an LLM.
DETERMINISTIC_SIGNAL_EVENTS = {"audio_spike", "speech_density", "scene_change"}


def generate_candidates(db: Session, job: ProcessingJob) -> None:
    """Generate and score candidates for the job's video."""
    settings = get_settings()
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")
    if not video.audio_path:
        raise ValueError("Extract audio before generating candidates")

    duration = video.duration_seconds or 0.0
    if duration <= 0:
        raise ValueError("Video has no known duration")

    job_service.update_progress(db, job, 0.1)
    segments = _transcript_segments(db, video.id)
    events = analysis_service.list_events(db, video.id)
    scenes = analysis_service.list_scenes(db, video.id)

    window_events = [
        WindowEvent(
            type=event.type,
            start_seconds=event.start_seconds,
            end_seconds=event.end_seconds,
            confidence=event.confidence,
        )
        for event in events
    ]
    scene_boundaries = [scene.start_seconds for scene in scenes if scene.start_seconds > 0]
    windows = build_windows(
        segments,
        window_events,
        duration_seconds=duration,
        window_seconds=settings.semantic_window_seconds,
        scene_boundaries=scene_boundaries,
    )
    job_service.update_progress(db, job, 0.35)

    provider = _llm_provider_or_none(settings)
    selected: list[tuple[float, float, dict]] = []
    for window in windows:
        judgment = None
        if provider is not None:
            try:
                judgment = provider.judge_window(window.render_prompt())
            except (LLMValidationError, ProviderUnavailableError) as exc:
                # A single bad window must not sink the run.
                logger.warning("Window at %.1fs skipped: %s", window.start_seconds, exc)

        if judgment is not None:
            if not judgment.is_highlight:
                continue
            start = window.start_seconds + judgment.suggested_start_offset
            end = window.end_seconds + judgment.suggested_end_offset
            semantic = judgment.score
            category = judgment.category
            reason = judgment.reason
            source = provider.name
        elif _has_deterministic_signal(window):
            start, end = window.start_seconds, window.end_seconds
            semantic = 0.4  # neutral: interesting window, no model opinion
            category = "detected"
            reason = "Deterministic signals (audio/spike/events) without LLM judgment."
            source = "deterministic"
        else:
            continue

        padded = _pad(start, end, duration, settings)
        if padded is None:
            continue
        selected.append(
            (
                *padded,
                {
                    "video_id": video.id,
                    "semantic": semantic,
                    "category": category,
                    "reason": reason,
                    "source": source,
                    "audio_events": sum(
                        1
                        for event in window.events
                        if event.type in {"audio_spike", "speech_density"}
                    ),
                    "scene_changes": window.scene_count,
                    "speech_density": _window_density(window),
                    "speech_coverage": _coverage(window, duration),
                },
            )
        )
    job_service.update_progress(db, job, 0.7)

    candidates = _score_candidates(selected, duration, settings)
    candidate_service.replace_candidates(db, video.id, candidates)
    logger.info("Generated %d candidates for video %s", len(candidates), video.id)
    job_service.complete_job(db, job)


def rescore_candidates(db: Session, job: ProcessingJob) -> None:
    """Re-score existing candidates with current settings/weights."""
    settings = get_settings()
    video = job.video
    if video is None:
        raise ValueError(f"Job {job.id} has no video")

    job_service.update_progress(db, job, 0.2)
    candidates = candidate_service.list_video_candidates(db, video.id)
    duration = video.duration_seconds or 0.0
    events = analysis_service.list_events(db, video.id)

    for index, candidate in enumerate(candidates):
        signals = _signals_for(candidate, duration, events, candidates[:index], settings)
        candidate.overall_score = scoring.score_candidate(signals, settings.scoring_weights)
    db.commit()
    job_service.complete_job(db, job)


# ---------------------------------------------------------------------------
# helpers


def _llm_provider_or_none(settings: Settings) -> LLMProvider | None:
    if not settings.llm_enabled:
        return None
    try:
        return get_llm_provider(settings)
    except ProviderUnavailableError as exc:
        logger.warning("LLM unavailable, using deterministic signals only: %s", exc)
        return None


def _transcript_segments(db: Session, video_id: int) -> list[tuple[float, float, str]]:
    transcript = transcript_service.get_transcript_for_video(db, video_id)
    if transcript is None:
        return []
    return [
        (segment.start_seconds, segment.end_seconds, segment.text)
        for segment in transcript.segments
    ]


def _has_deterministic_signal(window) -> bool:
    return any(event.type in DETERMINISTIC_SIGNAL_EVENTS for event in window.events)


def _pad(start: float, end: float, duration: float, settings) -> tuple[float, float] | None:
    """Apply pre/post-roll padding and clamp to the video bounds."""
    padded_start = start - settings.candidate_pre_roll_seconds
    padded_end = end + settings.candidate_post_roll_seconds
    if padded_end <= padded_start:
        return None
    return (max(padded_start, 0.0), min(padded_end, duration))


def _window_density(window) -> float:
    for event in window.events:
        if event.type == "speech_density" and event.confidence is not None:
            return event.confidence
    return 0.0


def _coverage(window, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return min((window.end_seconds - window.start_seconds) / duration, 1.0)


def _score_candidates(selected, duration, settings) -> list[ClipCandidate]:
    """Score each candidate; novelty downweights overlap with earlier picks."""
    candidates: list[ClipCandidate] = []
    for start, end, info in selected:
        signals = scoring.CandidateSignals(
            semantic=info["semantic"],
            audio=scoring.audio_signal(
                audio_event_count=info["audio_events"],
                speech_density=info["speech_density"],
            ),
            visual=scoring.visual_signal(
                scene_change_count=info["scene_changes"],
                duration_seconds=end - start,
            ),
            context=scoring.context_signal(speech_coverage=info["speech_coverage"]),
            standalone=scoring.standalone_signal(
                speech_coverage=info["speech_coverage"],
                starts_on_silence=False,
                ends_on_silence=False,
                duration_seconds=end - start,
                min_seconds=settings.candidate_min_seconds,
                max_seconds=settings.candidate_max_seconds,
            ),
            novelty=_novelty(start, end, [c for c in candidates]),
        )
        overall = scoring.score_candidate(signals, settings.scoring_weights)
        candidates.append(
            ClipCandidate(
                video_id=info["video_id"],
                start_seconds=start,
                end_seconds=end,
                semantic_score=signals.semantic,
                audio_score=signals.audio,
                visual_score=signals.visual,
                context_score=signals.context,
                standalone_score=signals.standalone,
                novelty_score=signals.novelty,
                overall_score=overall,
                category=info["category"],
                reason=info["reason"],
                source=info["source"],
            )
        )
    candidates.sort(key=lambda candidate: -candidate.overall_score)
    return candidates


def _signals_for(candidate, duration, events, earlier, settings) -> scoring.CandidateSignals:
    """Recompute signals for an existing candidate (re-score path)."""
    overlapping = [
        event
        for event in events
        if event.start_seconds < candidate.end_seconds
        and event.end_seconds >= candidate.start_seconds
    ]
    audio_events = sum(
        1 for event in overlapping if event.type in {"audio_spike", "speech_density"}
    )
    scene_changes = sum(1 for event in overlapping if event.type == "scene_change")
    density = next(
        (
            event.confidence
            for event in overlapping
            if event.type == "speech_density" and event.confidence is not None
        ),
        0.0,
    )
    duration_seconds = candidate.end_seconds - candidate.start_seconds
    return scoring.CandidateSignals(
        semantic=candidate.semantic_score,
        audio=scoring.audio_signal(audio_event_count=audio_events, speech_density=density or 0.0),
        visual=scoring.visual_signal(
            scene_change_count=scene_changes, duration_seconds=duration_seconds
        ),
        context=candidate.context_score,
        standalone=candidate.standalone_score,
        novelty=_novelty(candidate.start_seconds, candidate.end_seconds, earlier),
    )


def _novelty(start: float, end: float, earlier) -> float:
    """1.0 minus the largest overlap with an already-selected candidate."""
    worst = 0.0
    for candidate in earlier:
        overlap = min(end, candidate.end_seconds) - max(start, candidate.start_seconds)
        if overlap > 0:
            worst = max(worst, overlap / max(end - start, 0.001))
    return scoring.novelty_signal(worst)
