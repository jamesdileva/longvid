"""Export entity — a reproducible render of a clip to a delivery preset.

Exports store everything needed to reproduce (or debug) the result:
implementation-guide §24 — source/editing plan snapshot, preset, resolved export
settings, application version and timestamp.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import enum_values
from app.models.clip import Clip
from app.utils.time import utcnow


class ExportStatus(str, enum.Enum):
    """Render lifecycle of an export file."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Export(Base):
    """A clip exported to a specific delivery preset."""

    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    preset: Mapped[str] = mapped_column(String(32), nullable=False)
    container: Mapped[str] = mapped_column(String(16), nullable=False)
    video_codec: Mapped[str] = mapped_column(String(16), nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(16), nullable=False)
    # Resolved encoder settings + reproducibility metadata (guide §24).
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    editing_profile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus, values_callable=enum_values),
        default=ExportStatus.PENDING,
        nullable=False,
        index=True,
    )
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    clip: Mapped[Clip] = relationship()
