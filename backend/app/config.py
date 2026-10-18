"""Application settings.

All values are overridable via environment variables prefixed with ``LONGVID_``
(e.g. ``LONGVID_PORT=9000``). The local API is bound to ``127.0.0.1`` by design.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(env_prefix="LONGVID_", env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8790
    data_dir: Path = DEFAULT_DATA_DIR
    database_name: str = "longvid.db"
    log_level: str = "info"

    # Media tooling. Override via LONGVID_FFPROBE_PATH / LONGVID_FFMPEG_PATH
    # if ffmpeg is not on PATH.
    ffprobe_path: str = "ffprobe"
    ffmpeg_path: str = "ffmpeg"
    allowed_video_extensions: tuple[str, ...] = (".mp4", ".mov", ".mkv", ".webm", ".avi")
    thumbnail_width: int = 320
    preview_width: int = 480
    preview_seconds: float = 4.0

    # Transcription-oriented audio extraction (implementation-guide §11).
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    # Background job processing.
    job_workers: int = 2

    # Transcription (architecture §8): provider name + model settings.
    transcription_provider: str = "whisper"
    whisper_model: str = "tiny"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = None  # None = auto-detect
    synthetic_segment_seconds: float = 5.0

    # Analysis thresholds (roadmap 6.2/6.4) — all deterministic defaults.
    scene_threshold: float = 0.3
    silence_threshold_db: float = -45.0
    min_silence_seconds: float = 1.5
    peak_threshold_db: float = -8.0
    analysis_window_seconds: float = 10.0
    speech_density_threshold: float = 0.6

    # Semantic analysis (roadmap 7): local LLM provider.
    llm_provider: str = "ollama"  # ollama | fake (deterministic, tests)
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 120.0
    llm_temperature: float = 0.2
    # Set false to generate candidates from deterministic signals only.
    llm_enabled: bool = True

    # Semantic windowing and candidate padding (implementation-guide §15/§17).
    semantic_window_seconds: float = 30.0
    candidate_pre_roll_seconds: float = 5.0
    candidate_post_roll_seconds: float = 8.0
    candidate_min_seconds: float = 15.0
    candidate_max_seconds: float = 90.0

    # Automatic trimming at clip creation (roadmap 10.2): snap clip boundaries
    # to natural sentence edges and remove dead air around the speech.
    trim_sentence_tolerance_seconds: float = 3.0
    trim_pre_roll_seconds: float = 0.5
    trim_post_roll_seconds: float = 1.0

    # Captions (roadmap 10.3): generate SRT/ASS and burn them for profiles
    # that request captions. Disable to render clips caption-free.
    captions_enabled: bool = True

    # Audio processing (roadmap 10.4): profiles with audio_normalization get a
    # gate + EBU R128 loudness normalization chain at render time.
    audio_loudness_target_lufs: float = -16.0
    audio_true_peak_db: float = -1.5
    audio_loudness_range: float = 11.0
    audio_gate_threshold_db: float = -45.0

    # Candidate scoring weights (implementation-guide §16).
    scoring_weights: dict[str, float] = {
        "semantic": 0.30,
        "audio": 0.15,
        "visual": 0.15,
        "context": 0.15,
        "standalone": 0.15,
        "novelty": 0.10,
    }

    @property
    def database_url(self) -> str:
        """SQLite URL derived from the data directory."""
        return f"sqlite:///{self.data_dir / self.database_name}"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
