"""Test fixtures and path bootstrapping for the backend suite.

Every test runs against an isolated data directory (tmp_path) with a fresh
SQLite database, and fully deterministic time — no wall-clock dependencies.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.database import init_db, reset_caches
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch) -> Iterator[None]:
    """Point the app at a throwaway data dir and clear cached settings/engine."""
    monkeypatch.setenv("LONGVID_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    reset_caches()
    init_db()
    yield
    get_settings.cache_clear()
    reset_caches()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient with lifespan (database initialized) as a context manager."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def data_dir() -> Path:
    """The isolated data directory for the current test."""
    return get_settings().data_dir
