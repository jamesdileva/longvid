"""LLM provider interface (implementation-guide §17/§30).

LongVid never hard-codes a model: it asks for capabilities (structured
highlight judgments) and the configured provider answers. Raw LLM output is
never trusted — every response is parsed and validated before use.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class HighlightJudgment:
    """A validated structured judgment about one analysis window."""

    is_highlight: bool
    score: float
    category: str
    reason: str
    suggested_start_offset: float = 0.0
    suggested_end_offset: float = 0.0


class LLMValidationError(ValueError):
    """Raised when model output cannot be parsed into a judgment."""


class LLMProvider(abc.ABC):
    """Local LLM access behind a replaceable interface."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier used in logs and settings."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether the provider can serve requests right now."""

    @abc.abstractmethod
    def judge_window(self, prompt: str) -> HighlightJudgment:
        """Classify one semantic window, returning a validated judgment."""
