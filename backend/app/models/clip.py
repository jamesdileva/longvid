"""Clip entity — a persistent timeline definition and its rendered file.

A clip is a timeline range (source video + start/end + editing profile) that is
independent of the rendered MP4 (implementation-guide §18), so the same clip
can later be re-rendered under a different editing profile.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import enum_values
from app.models.video import Video
from app.utils.time import utcnow


class ClipStatus(str, enum.Enum):
    """Render lifecycle of a clip's MP4 file."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class Clip(Base):
    """A clip definition plus the state of its rendered file."""

    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Soft reference only: candidates are replaced on regeneration, so a
    # foreign key would go stale. The timeline fields are snapshotted.
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    editing_profile: Mapped[str] = mapped_column(String(32), default="clean", nullable=False)
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, values_callable=enum_values),
        default=ClipStatus.PENDING,
        nullable=False,
        index=True,
    )
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    video: Mapped[Video] = relationship(back_populates="clips")
