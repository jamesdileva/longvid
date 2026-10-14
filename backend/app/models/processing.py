"""Processing job entity — tracks long-running pipeline operations."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import enum_values
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.video import Video


class JobType(str, enum.Enum):
    """Pipeline stages that can run as background jobs."""

    INGEST = "ingest"
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    DETECT_SCENES = "detect_scenes"
    ANALYZE_EVENTS = "analyze_events"
    GENERATE_CANDIDATES = "generate_candidates"
    SCORE_CANDIDATES = "score_candidates"
    GENERATE_CLIP = "generate_clip"
    EXPORT = "export"


class JobStatus(str, enum.Enum):
    """Lifecycle states of a job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob(Base):
    """A unit of background work tied to a single video.

    Jobs must never block HTTP requests; progress is polled or streamed to the UI.
    """

    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[JobType] = mapped_column(
        Enum(JobType, values_callable=enum_values), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=enum_values),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    video: Mapped["Video"] = relationship(back_populates="jobs")
