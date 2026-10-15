"""Ollama LLM provider — local inference over the Ollama HTTP API.

Uses only the standard library (no new runtime dependencies) and always
requests JSON output, which is validated before it reaches the pipeline
(security rule: raw LLM output is never trusted).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.client import HTTPException

from app.providers.llm.base import (
    HighlightJudgment,
    LLMProvider,
    LLMValidationError,
)

_JSON_SCHEMA_HINT = (
    '{"is_highlight": true|false, "score": 0.0-1.0, "category": "short label", '
    '"reason": "short explanation", "suggested_start_offset": seconds, '
    '"suggested_end_offset": seconds}'
)


class OllamaProvider(LLMProvider):
    """Talks to a local Ollama server's ``/api/generate`` endpoint."""

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3.2",
        timeout_seconds: float = 120.0,
        temperature: float = 0.2,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._temperature = temperature

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._host}/api/tags", timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError, HTTPException, ValueError):
            return False

    def judge_window(self, prompt: str) -> HighlightJudgment:
        body = {
            "model": self._model,
            "prompt": f"{prompt}\n\nRespond ONLY with JSON matching: {_JSON_SCHEMA_HINT}",
            "stream": False,
            "format": "json",
            "options": {"temperature": self._temperature},
        }
        request = urllib.request.Request(
            f"{self._host}/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:  # generation can legitimately take a while
            raise LLMValidationError(f"Ollama request timed out after {self._timeout}s") from exc
        except (urllib.error.URLError, OSError, HTTPException, ValueError) as exc:
            raise LLMValidationError(f"Ollama request failed: {exc}") from exc

        model_text = payload.get("response", "")
        return _parse_judgment(model_text)


def _parse_judgment(model_text: str) -> HighlightJudgment:
    """Parse and validate the model's JSON into a judgment (never trust raw text)."""
    try:
        data = json.loads(model_text)
    except json.JSONDecodeError as exc:
        raise LLMValidationError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMValidationError("Model JSON must be an object")

    missing = {"is_highlight", "score", "category", "reason"} - set(data)
    if missing:
        raise LLMValidationError(f"Model JSON missing fields: {sorted(missing)}")

    try:
        score = float(data["score"])
    except (TypeError, ValueError) as exc:
        raise LLMValidationError("score must be a number") from exc

    return HighlightJudgment(
        is_highlight=bool(data["is_highlight"]),
        score=min(max(score, 0.0), 1.0),
        category=str(data["category"])[:64],
        reason=str(data["reason"])[:500],
        suggested_start_offset=_as_float(data.get("suggested_start_offset"), 0.0),
        suggested_end_offset=_as_float(data.get("suggested_end_offset"), 0.0),
    )


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
