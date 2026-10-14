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

    @property
    def database_url(self) -> str:
        """SQLite URL derived from the data directory."""
        return f"sqlite:///{self.data_dir / self.database_name}"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
