"""Caption generation (roadmap 10.3, implementation-guide §22).

Transcript segments are clipped to a clip's timeline and re-based to zero, then
serialised as SRT (portable) and ASS (styled, used for burned captions). Both
builders are pure and deterministic so their output can be snapshotted and
tested.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.editing.caption_emphasis import emphasize_text
from app.editing.profiles import EditingProfile

# Transcript segments as (start, end, text).
Segments = list[tuple[float, float, str]]

ASS_COLOR_WHITE = "&H00FFFFFF"
ASS_COLOR_BLACK = "&H00000000"
ASS_COLOR_SHADOW = "&H80000000"
# ASS colours are &HAABBGGRR; this gold is RGB(255, 213, 0).
ASS_COLOR_EMPHASIS = "&H0000D5FF"


@dataclass(frozen=True)
class CaptionCue:
    """One subtitle line, timed relative to the start of the clip."""

    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class CaptionStyle:
    """ASS styling for a caption track."""

    name: str
    font: str
    font_size: int
    primary_color: str
    outline_color: str
    back_color: str
    outline: int
    margin_v: int
    play_res_x: int
    play_res_y: int
    emphasis_color: str = ASS_COLOR_EMPHASIS
    emphasis_scale: int = 115


LANDSCAPE_STYLE = CaptionStyle(
    name="landscape",
    font="Arial",
    font_size=48,
    primary_color=ASS_COLOR_WHITE,
    outline_color=ASS_COLOR_BLACK,
    back_color=ASS_COLOR_SHADOW,
    outline=2,
    margin_v=40,
    play_res_x=1920,
    play_res_y=1080,
)

VERTICAL_STYLE = CaptionStyle(
    name="vertical",
    font="Arial",
    font_size=64,
    primary_color=ASS_COLOR_WHITE,
    outline_color=ASS_COLOR_BLACK,
    back_color=ASS_COLOR_SHADOW,
    outline=3,
    margin_v=180,
    play_res_x=1080,
    play_res_y=1920,
)


def style_for_profile(profile: EditingProfile) -> CaptionStyle:
    """Vertical profiles get a larger, higher-set caption style."""
    return VERTICAL_STYLE if profile.aspect_ratio == "9:16" else LANDSCAPE_STYLE


def cues_for_range(
    segments: Segments, *, start: float, end: float, max_seconds: float | None = None
) -> list[CaptionCue]:
    """Clip segments to ``[start, end]`` and re-base their times to zero.

    Segments are trimmed at the clip edges so a caption never outlives its
    clip, and empty segments are dropped. ``max_seconds`` caps a cue's length
    (used when a profile shortens the clip after captions are laid out).
    """
    cues: list[CaptionCue] = []
    for seg_start, seg_end, raw_text in sorted(segments):
        if seg_end <= start or seg_start >= end:
            continue
        cue_start = max(seg_start, start) - start
        cue_end = min(seg_end, end) - start
        if max_seconds is not None:
            cue_end = min(cue_end, cue_start + max_seconds)
        text = " ".join(raw_text.split())
        if not text or cue_end <= cue_start:
            continue
        cues.append(CaptionCue(round(cue_start, 3), round(cue_end, 3), text))
    return cues


def split_cues(cues: list[CaptionCue], *, max_words: int) -> list[CaptionCue]:
    """Break long cues into shorter ones at word boundaries (roadmap 12.3).

    Times are distributed across the chunks proportionally to their character
    length, so the words of a segment stay in sync with the audio. ``max_words``
    ``<= 0`` disables splitting.
    """
    if max_words <= 0:
        return cues
    out: list[CaptionCue] = []
    for cue in cues:
        out.extend(_split_cue(cue, max_words))
    return out


def _split_cue(cue: CaptionCue, max_words: int) -> list[CaptionCue]:
    words = cue.text.split()
    if len(words) <= max_words:
        return [cue]
    duration = cue.end_seconds - cue.start_seconds
    chunks = [words[index : index + max_words] for index in range(0, len(words), max_words)]
    weights = [sum(len(word) for word in chunk) for chunk in chunks]
    total = sum(weights) or 1
    out: list[CaptionCue] = []
    cursor = cue.start_seconds
    for position, chunk in enumerate(chunks):
        end = (
            cue.end_seconds
            if position == len(chunks) - 1
            else cursor + duration * weights[position] / total
        )
        out.append(CaptionCue(round(cursor, 3), round(end, 3), " ".join(chunk)))
        cursor = end
    return out


def build_srt(cues: list[CaptionCue]) -> str:
    """Serialise cues as SubRip (SRT)."""
    blocks = [
        f"{index}\n{_srt_time(cue.start_seconds)} --> {_srt_time(cue.end_seconds)}\n{cue.text}"
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def build_ass(
    cues: list[CaptionCue],
    style: CaptionStyle,
    *,
    emphases: dict[int, list[str]] | None = None,
) -> str:
    """Serialise cues as Advanced SubStation Alpha (ASS).

    ``emphases`` maps a cue's index to the words that should be highlighted;
    those words are wrapped in override tags by
    :func:`app.editing.caption_emphasis.emphasize_text`.
    """
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {style.play_res_x}",
        f"PlayResY: {style.play_res_y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding"
        ),
        (
            f"Style: Default,{style.font},{style.font_size},{style.primary_color},"
            f"{style.primary_color},{style.outline_color},{style.back_color},"
            f"0,0,0,0,100,100,0,0,1,{style.outline},1,2,20,20,{style.margin_v},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for index, cue in enumerate(cues):
        text = _ass_text(cue.text)
        words = (emphases or {}).get(index)
        if words:
            text = emphasize_text(
                text,
                words,
                color=style.emphasis_color,
                scale=style.emphasis_scale,
                reset_color=style.primary_color,
            )
        lines.append(
            "Dialogue: 0,"
            f"{_ass_time(cue.start_seconds)},{_ass_time(cue.end_seconds)},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def _srt_time(seconds: float) -> str:
    total_ms = max(round(seconds * 1000), 0)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    total_cs = max(round(seconds * 100), 0)
    hours, remainder = divmod(total_cs, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centis = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _ass_text(text: str) -> str:
    """ASS is line-based; braces are override tags, so strip them."""
    return text.replace("{", "(").replace("}", ")")
