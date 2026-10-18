"""Tests for aspect-ratio conversion and center crop (roadmap 11.1/11.2)."""

from __future__ import annotations

from dataclasses import replace

from app.editing.framing import ASPECT_TARGETS, Framing, framing_plan
from app.editing.profiles import get_profile
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle


def _crop_ratio(framing: Framing) -> float:
    return framing.crop_width / framing.crop_height


def _square(aspect_ratio: str) -> object:
    """A profile forced to ``aspect_ratio`` with zoom off."""
    return replace(get_profile("clean"), aspect_ratio=aspect_ratio, zoom=False)


class TestFramingPlan:
    def test_clean_keeps_the_source_untouched(self) -> None:
        assert framing_plan(get_profile("clean"), source_width=1920, source_height=1080) is None

    def test_matching_aspect_without_zoom_is_a_no_op(self) -> None:
        assert framing_plan(get_profile("youtube"), source_width=1920, source_height=1080) is None

    def test_unknown_source_resolution_is_a_no_op(self) -> None:
        assert framing_plan(get_profile("shorts"), source_width=None, source_height=None) is None

    def test_landscape_to_vertical_center_crops_then_scales(self) -> None:
        framing = framing_plan(get_profile("shorts"), source_width=1920, source_height=1080)

        assert framing is not None
        assert (framing.target_width, framing.target_height) == ASPECT_TARGETS["9:16"]
        assert framing.zoom == 1.15
        assert abs(_crop_ratio(framing) - 9 / 16) < 0.01
        assert framing.crop_width % 2 == 0 and framing.crop_height % 2 == 0
        assert framing.crop_x + framing.crop_width <= 1920
        assert framing.crop_y + framing.crop_height <= 1080

    def test_four_three_source_is_letterbox_cropped_to_widescreen(self) -> None:
        framing = framing_plan(get_profile("youtube"), source_width=640, source_height=480)

        assert framing is not None
        assert (framing.target_width, framing.target_height) == (1920, 1080)
        assert abs(_crop_ratio(framing) - 16 / 9) < 0.01
        assert framing.crop_width == 640

    def test_one_by_one_target(self) -> None:
        framing = framing_plan(_square("1:1"), source_width=1920, source_height=1080)

        assert framing is not None
        assert (framing.target_width, framing.target_height) == (1080, 1080)
        assert framing.crop_width == 1080
        assert framing.crop_x == 420

    def test_filter_chain_crops_scales_and_sets_square_pixels(self) -> None:
        framing = framing_plan(get_profile("shorts"), source_width=1920, source_height=1080)

        chain = framing.filter_chain()
        assert chain.startswith(f"crop={framing.crop_width}:{framing.crop_height}:")
        assert chain.endswith("scale=1080:1920,setsar=1")
        assert framing.to_dict()["filter"] == chain


@requires_ffmpeg
class TestFramingThroughApi:
    def test_shorts_clip_is_rendered_vertical(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        assert clip["editing_plan"]["framing"]["filter"].endswith("scale=1080:1920,setsar=1")

    def test_clean_clip_keeps_the_source_resolution(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "clean"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        assert "framing" not in clip["editing_plan"]
