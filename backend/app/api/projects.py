"""Projects API: CRUD over project workspaces."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import projects as project_service
from app.services.workspace import WorkspaceError

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession) -> list[ProjectRead]:
    """List all projects, newest first."""
    return [project_service.to_read_model(db, p) for p in project_service.list_projects(db)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession) -> ProjectRead:
    """Create a project and scaffold its isolated workspace."""
    try:
        project = project_service.create_project(db, payload)
    except (WorkspaceError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return project_service.to_read_model(db, project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: DbSession) -> ProjectRead:
    """Fetch a single project by id."""
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project_service.to_read_model(db, project)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: DbSession) -> ProjectRead:
    """Partially update a project (name, description, status)."""
    try:
        project = project_service.update_project(db, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project_service.to_read_model(db, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: DbSession) -> None:
    """Delete a project, its database rows, and its workspace."""
    if not project_service.delete_project(db, project_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
