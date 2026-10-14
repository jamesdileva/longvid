"""Test fixtures and path bootstrapping for the backend suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings


@pytest.fixture()
def settings():
    """Application settings instance."""
    return get_settings()
