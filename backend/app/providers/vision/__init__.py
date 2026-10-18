"""Vision provider registry.

Selected via ``LONGVID_VISION_PROVIDER`` (``opencv`` default, ``synthetic``
for tests). Importing this module never imports OpenCV — availability is probed
lazily so the app runs without the optional dependency.
"""

from __future__ import annotations

from app.config import Settings
from app.providers.vision.base import SubjectSample, SubjectTrack, VisionProvider
from app.providers.vision.opencv import OpenCVVisionProvider
from app.providers.vision.synthetic import SyntheticVisionProvider

__all__ = [
    "SubjectSample",
    "SubjectTrack",
    "VisionProvider",
    "VisionProviderUnavailableError",
    "get_vision_provider",
]

_PROVIDERS: dict[str, type[VisionProvider]] = {
    "opencv": OpenCVVisionProvider,
    "synthetic": SyntheticVisionProvider,
}


class VisionProviderUnavailableError(RuntimeError):
    """Raised when the configured vision provider cannot be used."""


def get_vision_provider(settings: Settings) -> VisionProvider:
    """Instantiate the configured provider, verifying it is usable."""
    provider_cls = _PROVIDERS.get(settings.vision_provider)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise VisionProviderUnavailableError(
            f"Unknown vision provider '{settings.vision_provider}'. Available: {available}."
        )
    provider = _build(provider_cls, settings)
    if not provider.is_available():
        raise VisionProviderUnavailableError(
            f"Vision provider '{settings.vision_provider}' is not available. "
            "Install it (pip install backend[vision]) or set "
            "LONGVID_VISION_PROVIDER=synthetic."
        )
    return provider


def _build(provider_cls: type[VisionProvider], settings: Settings) -> VisionProvider:
    if provider_cls is OpenCVVisionProvider:
        return OpenCVVisionProvider(
            sample_interval_seconds=settings.vision_sample_interval_seconds,
            min_confidence=settings.vision_min_confidence,
        )
    if provider_cls is SyntheticVisionProvider:
        return SyntheticVisionProvider(
            sample_interval_seconds=settings.vision_sample_interval_seconds
        )
    return provider_cls()
