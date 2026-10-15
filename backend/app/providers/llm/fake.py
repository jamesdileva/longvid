"""Deterministic fake LLM provider for tests and offline development.

Judges windows by a fixed rule so candidate generation is testable without a
model server: transcripts containing the marker ``[HIGHLIGHT]`` are judged as
highlights, everything else is not.
"""

from __future__ import annotations

from app.providers.llm.base import HighlightJudgment, LLMProvider

HIGHLIGHT_MARKER = "[HIGHLIGHT]"


class FakeLLMProvider(LLMProvider):
    """Deterministic stand-in for a local LLM server."""

    @property
    def name(self) -> str:
        return "fake"

    def is_available(self) -> bool:
        return True

    def judge_window(self, prompt: str) -> HighlightJudgment:
        if HIGHLIGHT_MARKER in prompt:
            return HighlightJudgment(
                is_highlight=True,
                score=0.9,
                category="reaction",
                reason="Strong reaction followed by a successful outcome.",
                suggested_start_offset=-2.0,
                suggested_end_offset=3.0,
            )
        return HighlightJudgment(
            is_highlight=False,
            score=0.2,
            category="filler",
            reason="No strong signal in this window.",
        )
