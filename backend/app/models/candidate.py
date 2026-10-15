"""ClipCandidate entity — a proposed clip before any media is rendered.

Candidates are independent of editing profiles (implementation-guide §18):
the same candidate can spawn a Shorts, TikTok, or clean export later.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import enum_values
from app.utils.time import utcnow


class CandidateStatus(str, enum.Enum):
    """Human feedback state (implementation-guide §20)."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ClipCandidate(Base):
    """A scored time range proposed as a clip."""

    __tablename__ = "clip_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, values_callable=enum_values),
        default=CandidateStatus.PENDING,
        nullable=False,
        index=True,
    )
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audio_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    visual_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    standalone_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)
    # Comma-separated ids of the events this candidate covers.
    event_ids: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
