"""LLM provider registry."""

from __future__ import annotations

from app.config import Settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.fake import FakeLLMProvider
from app.providers.llm.ollama import OllamaProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "fake": FakeLLMProvider,
}


class ProviderUnavailableError(RuntimeError):
    """Raised when the configured provider cannot be used."""


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the configured provider, or raise if it cannot run."""
    provider_cls = _PROVIDERS.get(settings.llm_provider)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise ProviderUnavailableError(
            f"Unknown LLM provider '{settings.llm_provider}'. Available: {available}."
        )
    provider = _build(provider_cls, settings)
    if not provider.is_available():
        raise ProviderUnavailableError(
            f"LLM provider '{settings.llm_provider}' is not available "
            f"(is Ollama running at {settings.ollama_host}?)."
        )
    return provider


def _build(provider_cls: type[LLMProvider], settings: Settings) -> LLMProvider:
    if provider_cls is OllamaProvider:
        return OllamaProvider(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            temperature=settings.llm_temperature,
        )
    return provider_cls()
