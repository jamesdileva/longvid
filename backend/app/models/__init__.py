"""ORM models.

Import every module here so ``Base.metadata`` is fully populated before
``create_all()`` runs.
"""

from app.models.candidate import CandidateStatus, ClipCandidate
from app.models.clip import Clip, ClipStatus
from app.models.event import Event
from app.models.processing import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus
from app.models.scene import Scene
from app.models.transcript import Transcript, TranscriptSegment
from app.models.video import Video, VideoStatus

__all__ = [
    "CandidateStatus",
    "Clip",
    "ClipCandidate",
    "ClipStatus",
    "Event",
    "JobStatus",
    "JobType",
    "ProcessingJob",
    "Project",
    "ProjectStatus",
    "Scene",
    "Transcript",
    "TranscriptSegment",
    "Video",
    "VideoStatus",
]
