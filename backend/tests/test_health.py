"""Tests for the health endpoint and API surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app())


def test_health_returns_ok() -> None:
    response = make_client().get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["database"] == "ok"


def test_health_schema_fields() -> None:
    response = make_client().get("/api/health")
    assert set(response.json().keys()) == {"status", "version", "database"}


def test_openapi_exposes_health() -> None:
    response = make_client().get("/openapi.json")
    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
