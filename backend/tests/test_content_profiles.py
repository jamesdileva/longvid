"""Tests for content profiles: catalog, assignment, and detection (Phase 13)."""

from __future__ import annotations

import pytest

from app.analysis.content_profiles import (
    CONTENT_PROFILES,
    DEFAULT_CONTENT_PROFILE_KEY,
    UnknownContentProfileError,
    get_content_profile,
    list_content_profiles,
)
from app.database import get_sessionmaker
from app.providers.transcription.base import SegmentResult
from app.services import transcripts as transcript_service
from app.services import videos as video_service
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import create_project, import_video, run_job

GAMING_TRANSCRIPT = [
    SegmentResult(0.0, 6.0, "that was an insane headshot, what a clutch"),
    SegmentResult(6.0, 12.0, "gg, we won the boss fight"),
]


class TestContentProfileCatalog:
    def test_exposes_the_roadmap_profiles(self) -> None:
        assert [profile.key for profile in list_content_profiles()] == [
            "general",
            "gaming",
            "podcast",
            "commentary",
        ]

    def test_general_is_the_default(self) -> None:
        assert DEFAULT_CONTENT_PROFILE_KEY == "general"
        assert CONTENT_PROFILES["general"].keywords == ()

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(UnknownContentProfileError):
            get_content_profile("speedrunning")

    def test_keyword_hits_are_whole_word_and_distinct(self) -> None:
        gaming = get_content_profile("gaming")

        assert gaming.keyword_hits("an insane INSANE clutch, gg") == 3
        assert gaming.keyword_hits("a skillful display") == 0

    def test_general_profile_never_matches_keywords(self) -> None:
        assert get_content_profile("general").keyword_hits("kill win clutch boss") == 0

    def test_profiles_carry_prompt_guidance(self) -> None:
        assert "boss" in get_content_profile("gaming").guidance.lower()
        assert "stories" in get_content_profile("podcast").guidance.lower()
        assert "controversial" in get_content_profile("commentary").guidance.lower()


class TestContentProfileApi:
    def test_lists_profiles(self, client) -> None:
        response = client.get("/api/content-profiles")

        assert response.status_code == 200
        keys = [profile["key"] for profile in response.json()]
        assert keys == ["general", "gaming", "podcast", "commentary"]
        assert "keywords" in response.json()[1]

    def test_assigns_a_profile_to_a_video(self, client, narrate_video) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)
        assert video["content_profile"] == "general"

        response = client.put(
            f"/api/videos/{video['id']}/content-profile",
            json={"content_profile": "podcast"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["content_profile"] == "podcast"

    def test_rejects_an_unknown_profile(self, client, narrate_video) -> None:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)

        response = client.put(
            f"/api/videos/{video['id']}/content-profile",
            json={"content_profile": "speedrunning"},
        )

        assert response.status_code == 400

    def test_missing_video_is_404(self, client) -> None:
        response = client.put(
            "/api/videos/9999/content-profile", json={"content_profile": "gaming"}
        )

        assert response.status_code == 404


@requires_ffmpeg
class TestContentProfileDetection:
    def _prepare(self, client, narrate_video, profile: str) -> dict:
        project = create_project(client)
        video = import_video(client, project["id"], narrate_video)
        run_job(client, video["id"], "extract_audio")
        run_job(client, video["id"], "transcribe")
        session = get_sessionmaker()()
        try:
            row = video_service.get_video(session, video["id"])
            assert row is not None
            transcript_service.replace_transcript(session, row, GAMING_TRANSCRIPT)
        finally:
            session.close()
        run_job(client, video["id"], "analyze_events")
        assignment = client.put(
            f"/api/videos/{video['id']}/content-profile",
            json={"content_profile": profile},
        )
        assert assignment.status_code == 200, assignment.text
        run_job(client, video["id"], "generate_candidates")
        return video

    def test_gaming_profile_surfaces_gaming_moments(self, client, narrate_video) -> None:
        video = self._prepare(client, narrate_video, "gaming")

        candidates = client.get(f"/api/videos/{video['id']}/candidates").json()

        assert candidates
        assert any(candidate["category"] == "gaming" for candidate in candidates)

    def test_general_profile_does_not_label_gaming_moments(self, client, narrate_video) -> None:
        video = self._prepare(client, narrate_video, "general")

        candidates = client.get(f"/api/videos/{video['id']}/candidates").json()

        assert all(candidate["category"] != "gaming" for candidate in candidates)
