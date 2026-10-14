"""API response schemas (contract source for the frontend)."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Backend availability probe."""

    status: str
    version: str
    database: str
