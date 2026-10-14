"""Tests for the health endpoint and API surface."""

from __future__ import annotations


def test_health_returns_ok(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["database"] == "ok"


def test_health_schema_fields(client) -> None:
    response = client.get("/api/health")
    assert set(response.json().keys()) == {"status", "version", "database"}


def test_openapi_exposes_health_and_projects(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/projects" in paths
