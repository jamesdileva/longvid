"""API schemas (contract source for the frontend)."""

from app.schemas.analysis import EventRead, SceneRead
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobProcessRequest, JobRead
from app.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.transcripts import TranscriptRead, TranscriptSegmentRead
from app.schemas.videos import VideoImportRequest, VideoRead

__all__ = [
    "EventRead",
    "HealthResponse",
    "JobProcessRequest",
    "JobRead",
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
    "SceneRead",
    "TranscriptRead",
    "TranscriptSegmentRead",
    "VideoImportRequest",
    "VideoRead",
]
