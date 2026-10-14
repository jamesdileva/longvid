"""Tests for the videos API: import, list, assets, delete."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import requires_ffmpeg


def create_project(client, name: str = "Gaming Session") -> dict:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def import_video(client, project_id: str, path: Path | str):
    return client.post(f"/api/projects/{project_id}/videos", json={"path": str(path)})


@requires_ffmpeg
class TestImportVideo:
    def test_imports_probes_and_generates_assets(
        self, client, data_dir: Path, synthetic_video: Path
    ) -> None:
        project = create_project(client)

        response = import_video(client, project["id"], synthetic_video)

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["filename"] == "synthetic_clip.mp4"
        assert body["status"] == "ready"
        assert body["width"] == 320
        assert body["height"] == 240
        assert body["duration_seconds"] == pytest.approx(2.0, abs=0.3)
        assert body["video_codec"] == "h264"
        assert body["audio_codec"] == "aac"
        assert body["file_size_bytes"] > 0
        assert body["thumbnail_url"] == f"/api/videos/{body['id']}/thumbnail"
        assert body["preview_url"] == f"/api/videos/{body['id']}/preview"

        # Files landed inside the workspace, next to the DB rows.
        workspace = data_dir / project["workspace_path"]
        assert any((workspace / "source").glob("*.mp4"))
        assert (workspace / "media/thumbnails" / f"{body['id']}.jpg").is_file()
        assert (workspace / "media/previews" / f"{body['id']}.mp4").is_file()

    def test_original_file_is_untouched(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        before = synthetic_video.read_bytes()

        import_video(client, project["id"], synthetic_video)

        assert synthetic_video.read_bytes() == before

    def test_lists_videos(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        import_video(client, project["id"], synthetic_video)
        import_video(client, project["id"], synthetic_video)

        response = client.get(f"/api/projects/{project['id']}/videos")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_serves_thumbnail_and_preview(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video).json()

        thumb = client.get(f"/api/videos/{video['id']}/thumbnail")
        assert thumb.status_code == 200
        assert thumb.headers["content-type"] == "image/jpeg"
        assert thumb.content[:2] == b"\xff\xd8"

        preview = client.get(f"/api/videos/{video['id']}/preview")
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "video/mp4"
        assert len(preview.content) > 0

    def test_project_counts_video(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        import_video(client, project["id"], synthetic_video)

        response = client.get(f"/api/projects/{project['id']}")

        assert response.json()["video_count"] == 1

    def test_rejects_unsupported_extension(self, client, tmp_path: Path) -> None:
        project = create_project(client)
        bogus = tmp_path / "notes.txt"
        bogus.write_text("not a video", encoding="utf-8")

        response = import_video(client, project["id"], bogus)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_rejects_missing_file(self, client) -> None:
        project = create_project(client)

        response = import_video(client, project["id"], "C:/nonexistent/video.mp4")

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_unknown_project_returns_404(self, client, synthetic_video: Path) -> None:
        response = import_video(client, "0" * 32, synthetic_video)

        assert response.status_code == 404

    def test_importing_workspace_files_never_outside(
        self, client, data_dir: Path, synthetic_video: Path
    ) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video).json()

        # The only .mp4 under the data dir lives inside the project workspace.
        all_mp4 = [p for p in data_dir.rglob("*.mp4")]
        assert all(data_dir / project["workspace_path"] in mp4.parents for mp4 in all_mp4)
        assert video["id"] > 0


@requires_ffmpeg
class TestDeleteVideo:
    def test_removes_row_and_assets(self, client, synthetic_video: Path) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], synthetic_video).json()

        response = client.delete(f"/api/videos/{video['id']}")
        assert response.status_code == 204

        assert client.get(f"/api/videos/{video['id']}").status_code == 404
        assert client.get(f"/api/videos/{video['id']}/thumbnail").status_code == 404
        listed = client.get(f"/api/projects/{project['id']}/videos").json()
        assert listed == []

    def test_unknown_video_returns_404(self, client) -> None:
        assert client.delete("/api/videos/999999").status_code == 404
