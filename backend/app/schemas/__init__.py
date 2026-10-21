"""API schemas (contract source for the frontend)."""

from app.schemas.analysis import EventRead, SceneRead
from app.schemas.candidates import CandidateRead, CandidateStatusUpdate
from app.schemas.clips import ClipGenerateRequest, ClipRead, ClipUpdate
from app.schemas.content_profiles import ContentProfileRead
from app.schemas.editing import EditingProfileRead
from app.schemas.exports import ExportCreate, ExportPresetRead, ExportRead
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobProcessRequest, JobRead
from app.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.transcripts import TranscriptRead, TranscriptSegmentRead
from app.schemas.videos import (
    VideoContentProfileUpdate,
    VideoImportRequest,
    VideoRead,
)

__all__ = [
    "CandidateRead",
    "CandidateStatusUpdate",
    "ClipGenerateRequest",
    "ClipRead",
    "ClipUpdate",
    "ContentProfileRead",
    "EditingProfileRead",
    "EventRead",
    "ExportCreate",
    "ExportPresetRead",
    "ExportRead",
    "HealthResponse",
    "JobProcessRequest",
    "JobRead",
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
    "SceneRead",
    "TranscriptRead",
    "TranscriptSegmentRead",
    "VideoContentProfileUpdate",
    "VideoImportRequest",
    "VideoRead",
]
