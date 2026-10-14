"""Project entity — an isolated video-editing workspace."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import enum_values
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.video import Video


class ProjectStatus(str, enum.Enum):
    """Lifecycle state of a project."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    """A workspace that owns videos, jobs, analysis, clips, and exports."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, values_callable=enum_values),
        default=ProjectStatus.ACTIVE,
        nullable=False,
    )
    workspace_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    videos: Mapped[list["Video"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
