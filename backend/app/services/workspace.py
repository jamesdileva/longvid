"""Project workspace management — the filesystem side of the project model.

Layout per docs/architecture.md section 21::

    data/projects/<project_id>/
        source/            # imported originals (copies; user files untouched)
        media/thumbnails/
        media/previews/
        analysis/
        clips/generated/
        clips/previews/
        exports/shorts/
        exports/youtube/

Every path is validated against the projects root so a bad id can never
escape ``data/projects``.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.config import get_settings

PROJECTS_DIRNAME = "projects"

WORKSPACE_SUBDIRS: tuple[str, ...] = (
    "source",
    "media/thumbnails",
    "media/previews",
    "media/audio",
    "media/candidate-thumbs",
    "analysis",
    "clips/generated",
    "clips/previews",
    "exports/shorts",
    "exports/youtube",
)

_PROJECT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class WorkspaceError(RuntimeError):
    """Raised when a workspace path is invalid or could not be managed."""


def projects_root() -> Path:
    """Absolute path of ``<data_dir>/projects`` (created on demand)."""
    root = Path(get_settings().data_dir) / PROJECTS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def workspace_path(project_id: str) -> Path:
    """Resolve a project id to its absolute workspace directory."""
    if not _PROJECT_ID_PATTERN.match(project_id):
        raise WorkspaceError(f"Invalid project id: {project_id!r}")
    root = projects_root().resolve()
    candidate = (root / project_id).resolve()
    if not _is_within(candidate, root):
        raise WorkspaceError(f"Workspace path escapes projects root: {project_id!r}")
    return candidate


def create_workspace(project_id: str) -> Path:
    """Create the full workspace tree for a project."""
    workspace = workspace_path(project_id)
    for subdir in WORKSPACE_SUBDIRS:
        (workspace / subdir).mkdir(parents=True, exist_ok=True)
    return workspace


def delete_workspace(project_id: str) -> None:
    """Remove a project's workspace directory if it exists."""
    workspace = workspace_path(project_id)
    if workspace.is_dir():
        shutil.rmtree(workspace, ignore_errors=True)


def ensure_subdir(project_id: str, subdir: str) -> Path:
    """Create (if needed) and return one subdirectory of a workspace."""
    if subdir not in WORKSPACE_SUBDIRS:
        raise WorkspaceError(f"Unknown workspace subdirectory: {subdir!r}")
    path = workspace_path(project_id) / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_path(project_id: str, relative: str | None) -> Path | None:
    """Resolve a stored asset path (relative to the workspace root) safely."""
    if not relative:
        return None
    workspace = workspace_path(project_id)
    candidate = (workspace / relative).resolve()
    if not _is_within(candidate, workspace.resolve()):
        raise WorkspaceError(f"Asset path escapes workspace: {relative!r}")
    return candidate


def relative_workspace_path(project_id: str) -> str:
    """Workspace path as stored in the database (relative to the data dir)."""
    return f"{PROJECTS_DIRNAME}/{project_id}"


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True
