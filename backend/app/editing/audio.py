"""Audio processing (roadmap 10.4).

Clips whose editing profile enables ``audio_normalization`` get a deterministic
FFmpeg filter chain at render time:

* a gentle **gate** (``agate``) keeps true silence and the noise floor quiet so
  normalization does not pump up dead air — the "silence handling" step;
* **EBU R128 loudness normalization** (``loudnorm``) delivers consistent,
  broadcast-safe levels — the "normalization" / "basic loudness control".

The chain is a pure function of the profile and settings so it can be recorded
in the editing plan and replayed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.editing.profiles import EditingProfile

# loudnorm resamples internally to 192 kHz; bring the output back to the
# standard delivery rate so clips stay compact and broadly compatible.
_OUTPUT_SAMPLE_RATE = 48_000


@dataclass(frozen=True)
class AudioProcessing:
    """Resolved audio-processing parameters."""

    loudness_target_lufs: float
    true_peak_db: float
    loudness_range: float
    gate_threshold_db: float

    def filter_chain(self) -> str:
        """The FFmpeg ``-af`` chain (gate, loudness normalization, resample)."""
        return (
            f"agate=threshold={self.gate_threshold_db:g}dB:ratio=2,"
            f"loudnorm=I={self.loudness_target_lufs:g}:"
            f"TP={self.true_peak_db:g}:LRA={self.loudness_range:g},"
            f"aresample={_OUTPUT_SAMPLE_RATE}"
        )

    def to_dict(self) -> dict:
        """Plan snapshot including the concrete filter chain."""
        return {**asdict(self), "filter": self.filter_chain()}


def audio_processing(
    profile: EditingProfile,
    *,
    loudness_target_lufs: float,
    true_peak_db: float,
    loudness_range: float,
    gate_threshold_db: float,
) -> AudioProcessing | None:
    """Resolved audio processing for a profile, or ``None`` when disabled."""
    if not profile.audio_normalization:
        return None
    return AudioProcessing(
        loudness_target_lufs=loudness_target_lufs,
        true_peak_db=true_peak_db,
        loudness_range=loudness_range,
        gate_threshold_db=gate_threshold_db,
    )
