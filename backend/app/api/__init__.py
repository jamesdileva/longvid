"""API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.analysis import router as analysis_router
from app.api.candidates import router as candidates_router
from app.api.clips import router as clips_router
from app.api.editing import router as editing_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.projects import router as projects_router
from app.api.transcripts import router as transcripts_router
from app.api.videos import router as videos_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(videos_router)
api_router.include_router(jobs_router)
api_router.include_router(transcripts_router)
api_router.include_router(analysis_router)
api_router.include_router(candidates_router)
api_router.include_router(clips_router)
api_router.include_router(editing_router)
api_router.include_router(exports_router)
