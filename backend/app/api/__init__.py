"""API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.projects import router as projects_router
from app.api.videos import router as videos_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(videos_router)
api_router.include_router(jobs_router)
