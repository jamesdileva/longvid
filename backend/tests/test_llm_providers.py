"""Tests for LLM providers (Ollama) and the fake used by tests."""

from __future__ import annotations

import json
import urllib.error

import pytest

from app.config import Settings
from app.providers.llm import (
    FakeLLMProvider,
    LLMValidationError,
    OllamaProvider,
    ProviderUnavailableError,
    get_llm_provider,
)
from app.providers.llm.ollama import _parse_judgment


class TestOllamaProviderAvailability:
    def test_unavailable_when_server_is_down(self) -> None:
        # Point at a port nothing listens on.
        provider = OllamaProvider(host="http://127.0.0.1:59999", timeout_seconds=1)

        assert provider.is_available() is False

    def test_factory_raises_for_unreachable_ollama(self) -> None:
        settings = Settings(llm_provider="ollama", ollama_host="http://127.0.0.1:59999")

        with pytest.raises(ProviderUnavailableError):
            get_llm_provider(settings)

    def test_factory_rejects_unknown_provider(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            get_llm_provider(Settings(llm_provider="telepathy"))


class TestParseJudgment:
    def test_parses_valid_json(self) -> None:
        judgment = _parse_judgment(
            json.dumps(
                {
                    "is_highlight": True,
                    "score": 0.91,
                    "category": "reaction",
                    "reason": "Strong reaction",
                    "suggested_start_offset": -4.2,
                    "suggested_end_offset": 7.5,
                }
            )
        )

        assert judgment.is_highlight is True
        assert judgment.score == 0.91
        assert judgment.category == "reaction"
        assert judgment.suggested_start_offset == pytest.approx(-4.2)
        assert judgment.suggested_end_offset == pytest.approx(7.5)

    def test_clamps_scores_above_one(self) -> None:
        judgment = _parse_judgment(
            '{"is_highlight": true, "score": 9.5, "category": "x", "reason": "y"}'
        )

        assert judgment.score == 1.0

    def test_rejects_invalid_json(self) -> None:
        with pytest.raises(LLMValidationError):
            _parse_judgment("not json at all")

    def test_rejects_missing_fields(self) -> None:
        with pytest.raises(LLMValidationError):
            _parse_judgment('{"is_highlight": true}')

    def test_rejects_non_object_json(self) -> None:
        with pytest.raises(LLMValidationError):
            _parse_judgment("[1, 2, 3]")

    def test_defaults_bad_offsets_to_zero(self) -> None:
        judgment = _parse_judgment(
            '{"is_highlight": false, "score": 0.1, "category": "x", "reason": "y", '
            '"suggested_start_offset": "soon"}'
        )

        assert judgment.suggested_start_offset == 0.0


class TestOllamaRequest:
    def test_judge_window_parses_model_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = OllamaProvider(host="http://ollama.test", model="llama3.2", timeout_seconds=5)
        payload = {
            "response": json.dumps(
                {
                    "is_highlight": True,
                    "score": 0.8,
                    "category": "joke",
                    "reason": "punchline",
                }
            )
        }

        class FakeResponse:
            status = 200

            def read(self) -> bytes:
                return json.dumps(payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        judgment = provider.judge_window("WINDOW")

        assert judgment.category == "joke"
        assert captured["url"] == "http://ollama.test/api/generate"
        assert captured["body"]["format"] == "json"
        assert captured["body"]["model"] == "llama3.2"

    def test_judge_window_raises_on_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = OllamaProvider(host="http://ollama.test", timeout_seconds=5)

        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        with pytest.raises(LLMValidationError):
            provider.judge_window("WINDOW")


class TestFakeProvider:
    def test_marks_highlight_windows(self) -> None:
        judgment = FakeLLMProvider().judge_window("... [HIGHLIGHT] ...")

        assert judgment.is_highlight is True
        assert judgment.score == 0.9
        assert judgment.category == "reaction"

    def test_rejects_plain_windows(self) -> None:
        judgment = FakeLLMProvider().judge_window("ordinary narration")

        assert judgment.is_highlight is False

    def test_factory_returns_fake(self) -> None:
        provider = get_llm_provider(Settings(llm_provider="fake"))

        assert isinstance(provider, FakeLLMProvider)
        assert provider.is_available()
