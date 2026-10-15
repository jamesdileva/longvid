"""Scene helpers: turn detected boundaries into persisted scene spans."""

from __future__ import annotations

from app.services.ffmpeg_service import SceneBoundary


def build_scenes(
    boundaries: list[SceneBoundary], *, duration_seconds: float
) -> list[tuple[float, float, float | None]]:
    """Convert boundary times into (start, end, score) scene spans.

    The first scene starts at 0 and the last ends at ``duration_seconds``;
    boundaries inside the video split it into continuous shots.
    """
    if duration_seconds <= 0:
        return []
    cuts = sorted(
        {
            round(boundary.time_seconds, 3)
            for boundary in boundaries
            if 0 < boundary.time_seconds < duration_seconds
        }
    )
    if not cuts:
        return [(0.0, duration_seconds, None)]

    score_by_time = {round(boundary.time_seconds, 3): boundary.score for boundary in boundaries}
    scenes: list[tuple[float, float, float | None]] = []
    start = 0.0
    for cut in cuts:
        scenes.append((start, cut, score_by_time.get(cut)))
        start = cut
    scenes.append((start, duration_seconds, None))
    return scenes
