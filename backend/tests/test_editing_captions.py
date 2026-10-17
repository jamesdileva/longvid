"""Tests for caption generation and burned captions (roadmap 10.3)."""

from __future__ import annotations

from app.editing.captions import (
    LANDSCAPE_STYLE,
    VERTICAL_STYLE,
    CaptionCue,
    build_ass,
    build_srt,
    cues_for_range,
    style_for_profile,
)
from app.editing.profiles import get_profile
from app.services import ffmpeg_service
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle

SEGMENTS = [
    (0.0, 5.0, "first line"),
    (5.0, 10.0, "second line"),
    (10.0, 20.0, "third line"),
]


class TestCuesForRange:
    def test_rebases_times_to_the_clip_start(self) -> None:
        cues = cues_for_range(SEGMENTS, start=5.0, end=20.0)

        assert cues[0] == CaptionCue(0.0, 5.0, "second line")
        assert cues[1] == CaptionCue(5.0, 15.0, "third line")

    def test_trims_cues_that_overhang_the_clip_edges(self) -> None:
        cues = cues_for_range(SEGMENTS, start=3.0, end=12.0)

        assert cues[0] == CaptionCue(0.0, 2.0, "first line")
        assert cues[-1] == CaptionCue(7.0, 9.0, "third line")

    def test_drops_segments_outside_the_range(self) -> None:
        cues = cues_for_range(SEGMENTS, start=18.0, end=25.0)

        assert [cue.text for cue in cues] == ["third line"]

    def test_drops_empty_segments(self) -> None:
        cues = cues_for_range([(0.0, 5.0, "   "), (5.0, 9.0, "kept")], start=0.0, end=9.0)

        assert [cue.text for cue in cues] == ["kept"]

    def test_collapses_internal_whitespace(self) -> None:
        cues = cues_for_range([(0.0, 5.0, "  hello\n   world  ")], start=0.0, end=5.0)

        assert cues[0].text == "hello world"

    def test_caps_cue_length_when_asked(self) -> None:
        cues = cues_for_range(SEGMENTS, start=0.0, end=20.0, max_seconds=2.0)

        assert all(cue.end_seconds - cue.start_seconds <= 2.0 for cue in cues)


class TestBuildSrt:
    def test_serialises_numbered_blocks(self) -> None:
        srt = build_srt([CaptionCue(0.0, 2.5, "hello"), CaptionCue(2.5, 4.0, "world")])

        assert srt == (
            "1\n00:00:00,000 --> 00:00:02,500\nhello\n\n2\n00:00:02,500 --> 00:00:04,000\nworld\n"
        )

    def test_empty_cues_produce_empty_text(self) -> None:
        assert build_srt([]) == ""


class TestBuildAss:
    def test_includes_header_style_and_events(self) -> None:
        ass = build_ass([CaptionCue(0.0, 2.5, "hello")], style=LANDSCAPE_STYLE)

        assert "[Script Info]" in ass
        assert f"PlayResX: {LANDSCAPE_STYLE.play_res_x}" in ass
        assert "Style: Default,Arial,48," in ass
        assert "Dialogue: 0,0:00:00.00,0:00:02.50,Default,,0,0,0,,hello" in ass

    def test_strips_ass_override_braces(self) -> None:
        ass = build_ass([CaptionCue(0.0, 1.0, "a {b} c")], style=LANDSCAPE_STYLE)

        assert "a (b) c" in ass

    def test_vertical_style_is_larger_and_taller(self) -> None:
        assert style_for_profile(get_profile("shorts")) is VERTICAL_STYLE
        assert style_for_profile(get_profile("clean")) is LANDSCAPE_STYLE
        assert VERTICAL_STYLE.font_size > LANDSCAPE_STYLE.font_size


@requires_ffmpeg
class TestBurnSubtitles:
    def test_cut_clip_burns_a_subtitle_track(self, tmp_path, synthetic_video) -> None:
        subtitle = tmp_path / "clip.ass"
        subtitle.write_text(
            build_ass([CaptionCue(0.0, 2.0, "burned caption")], style=LANDSCAPE_STYLE),
            encoding="utf-8",
        )
        output = tmp_path / "out.mp4"

        ffmpeg_service.cut_clip(synthetic_video, output, 0.0, 2.0, subtitles_path=subtitle)

        assert output.is_file()
        info = ffmpeg_service.probe_file(output)
        assert info.video_codec is not None
        assert output.stat().st_size > 0


@requires_ffmpeg
class TestCaptionsThroughApi:
    def test_shorts_clip_exposes_srt_and_ass(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "shorts"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["editing_plan"]["captions"] is True
        assert clip["caption_srt_url"] == f"/api/clips/{clip['id']}/captions/srt"
        assert clip["caption_ass_url"] == f"/api/clips/{clip['id']}/captions/ass"

        srt = client.get(clip["caption_srt_url"])
        assert srt.status_code == 200
        assert srt.headers["content-type"].startswith("application/x-subrip")
        assert "-->" in srt.text

        ass = client.get(clip["caption_ass_url"])
        assert ass.status_code == 200
        assert "[V4+ Styles]" in ass.text

    def test_clean_clip_has_no_captions(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(f"/api/videos/{video['id']}/generate-clips", json={})
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["editing_plan"]["captions"] is False
        assert clip["caption_srt_url"] is None
        assert client.get(f"/api/clips/{clip['id']}/captions/srt").status_code == 404
        assert client.get(f"/api/clips/{clip['id']}/captions/wav").status_code == 404
