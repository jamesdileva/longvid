"""API schemas (contract source for the frontend)."""

from app.schemas.analysis import EventRead, SceneRead
from app.schemas.candidates import CandidateRead, CandidateStatusUpdate
from app.schemas.clips import ClipGenerateRequest, ClipRead, ClipUpdate
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobProcessRequest, JobRead
from app.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.transcripts import TranscriptRead, TranscriptSegmentRead
from app.schemas.videos import VideoImportRequest, VideoRead

__all__ = [
    "CandidateRead",
    "CandidateStatusUpdate",
    "ClipGenerateRequest",
    "ClipRead",
    "ClipUpdate",
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
