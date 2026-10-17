"""Tests for the projects CRUD API and workspace provisioning."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import workspace as workspace_service

EXPECTED_SUBDIRS = {
    "source",
    "media",
    "media/thumbnails",
    "media/previews",
    "media/audio",
    "media/candidate-thumbs",
    "analysis",
    "clips",
    "clips/generated",
    "clips/captions",
    "clips/previews",
    "exports",
    "exports/shorts",
    "exports/youtube",
}


def create_project(client, name: str = "Gaming Session", description: str | None = None):
    payload: dict = {"name": name}
    if description is not None:
        payload["description"] = description
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateProject:
    def test_creates_project_with_workspace(self, client, data_dir: Path) -> None:
        project = create_project(client, "Gaming Session", "Ranked grind")

        assert project["name"] == "Gaming Session"
        assert project["description"] == "Ranked grind"
        assert project["status"] == "active"
        assert project["video_count"] == 0
        assert project["clip_count"] == 0
        assert project["workspace_path"].startswith("projects/")
        assert project["id"] in project["workspace_path"]

        workspace = data_dir / "projects" / project["id"]
        assert workspace.is_dir()

    def test_scaffolds_workspace_tree(self, client, data_dir: Path) -> None:
        project = create_project(client)
        workspace = data_dir / "projects" / project["id"]
        actual = {
            str(path.relative_to(workspace)).replace("\\", "/")
            for path in workspace.rglob("*")
            if path.is_dir()
        }
        assert actual == EXPECTED_SUBDIRS

    def test_blank_name_is_rejected(self, client) -> None:
        response = client.post("/api/projects", json={"name": "   "})
        assert response.status_code == 400
        assert "blank" in response.json()["detail"]

    def test_empty_name_fails_validation(self, client) -> None:
        response = client.post("/api/projects", json={"name": ""})
        assert response.status_code == 422

    def test_hostile_name_cannot_escape_workspace(self, client, data_dir: Path) -> None:
        project = create_project(client, "../../evil")
        workspace = data_dir / "projects" / project["id"]
        assert workspace.is_dir()
        # Nothing was created outside the projects root.
        assert list((data_dir / "projects").iterdir()) == [workspace]


class TestListProjects:
    def test_returns_projects_newest_first(self, client) -> None:
        create_project(client, "First")
        create_project(client, "Second")

        response = client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert [p["name"] for p in projects] == ["Second", "First"]


class TestGetProject:
    def test_unknown_project_returns_404(self, client) -> None:
        response = client.get("/api/projects/deadbeef" * 4)
        assert response.status_code == 404

    def test_fetches_created_project(self, client) -> None:
        created = create_project(client, "Podcast Pilot")
        response = client.get(f"/api/projects/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Podcast Pilot"


class TestUpdateProject:
    def test_updates_name_description_and_status(self, client) -> None:
        created = create_project(client, "Old name", "Old description")
        response = client.patch(
            f"/api/projects/{created['id']}",
            json={"name": "New name", "description": "New description", "status": "archived"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New name"
        assert body["description"] == "New description"
        assert body["status"] == "archived"

    def test_blank_name_is_rejected(self, client) -> None:
        created = create_project(client)
        response = client.patch(f"/api/projects/{created['id']}", json={"name": " "})
        assert response.status_code == 400

    def test_unknown_project_returns_404(self, client) -> None:
        response = client.patch("/api/projects/" + "ab" * 16, json={"name": "x"})
        assert response.status_code == 404


class TestDeleteProject:
    def test_removes_row_and_workspace(self, client, data_dir: Path) -> None:
        created = create_project(client)
        response = client.delete(f"/api/projects/{created['id']}")
        assert response.status_code == 204

        assert client.get(f"/api/projects/{created['id']}").status_code == 404
        assert not (data_dir / "projects" / created["id"]).exists()

    def test_unknown_project_returns_404(self, client) -> None:
        response = client.delete("/api/projects/" + "cd" * 16)
        assert response.status_code == 404


class TestWorkspaceService:
    def test_rejects_non_hex_ids(self) -> None:
        with pytest.raises(workspace_service.WorkspaceError):
            workspace_service.workspace_path("../../etc")

    def test_rejects_path_traversal_ids(self) -> None:
        with pytest.raises(workspace_service.WorkspaceError):
            workspace_service.workspace_path("a" * 31 + "/")

    def test_delete_workspace_is_idempotent(self) -> None:
        fake_id = "f" * 32
        workspace_service.create_workspace(fake_id)
        assert workspace_service.workspace_path(fake_id).is_dir()
        workspace_service.delete_workspace(fake_id)
        workspace_service.delete_workspace(fake_id)  # must not raise
        assert not workspace_service.workspace_path(fake_id).exists()

    def test_ensure_subdir_rejects_unknown(self) -> None:
        fake_id = "e" * 32
        with pytest.raises(workspace_service.WorkspaceError):
            workspace_service.ensure_subdir(fake_id, "../outside")
