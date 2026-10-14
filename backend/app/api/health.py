"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.database import db_health_check
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report service and database availability."""
    database = db_health_check()
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=__version__,
        database=database,
    )
