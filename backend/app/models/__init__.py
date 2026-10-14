"""ORM models.

Import every module here so ``Base.metadata`` is fully populated before
``create_all()`` runs.
"""

from app.models.processing import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus
from app.models.video import Video, VideoStatus

__all__ = [
    "JobStatus",
    "JobType",
    "ProcessingJob",
    "Project",
    "ProjectStatus",
    "Video",
    "VideoStatus",
]
