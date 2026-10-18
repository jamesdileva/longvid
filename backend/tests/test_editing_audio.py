"""Tests for audio processing at render time (roadmap 10.4)."""

from __future__ import annotations

from app.editing.audio import AudioProcessing, audio_processing
from app.editing.profiles import get_profile
from app.services import ffmpeg_service
from tests.conftest import requires_ffmpeg
from tests.test_clips_api import prepare_with_candidates, run_job_settle

SETTINGS = {
    "loudness_target_lufs": -16.0,
    "true_peak_db": -1.5,
    "loudness_range": 11.0,
    "gate_threshold_db": -45.0,
}


class TestAudioProcessing:
    def test_disabled_for_profiles_without_normalization(self) -> None:
        assert audio_processing(get_profile("clean"), **SETTINGS) is None

    def test_chain_gates_silence_then_normalizes_loudness(self) -> None:
        resolved = audio_processing(get_profile("youtube"), **SETTINGS)

        assert isinstance(resolved, AudioProcessing)
        chain = resolved.filter_chain()
        assert chain == (
            "agate=threshold=-45dB:ratio=2,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
        )

    def test_plan_snapshot_records_parameters_and_chain(self) -> None:
        snapshot = audio_processing(get_profile("shorts"), **SETTINGS).to_dict()

        assert snapshot["loudness_target_lufs"] == -16.0
        assert snapshot["gate_threshold_db"] == -45.0
        assert snapshot["filter"].startswith("agate=")


@requires_ffmpeg
class TestCutClipAudio:
    def test_audio_filter_reencodes_audio_and_copies_video(self, tmp_path, synthetic_video) -> None:
        output = tmp_path / "audio.mp4"

        ffmpeg_service.cut_clip(synthetic_video, output, 0.0, 2.0, audio_filter="aresample=8000")

        assert output.is_file()
        info = ffmpeg_service.probe_file(output)
        assert info.sample_rate == 8000
        assert info.video_codec is not None

    def test_audio_filter_combines_with_burned_subtitles(self, tmp_path, synthetic_video) -> None:
        subtitle = tmp_path / "clip.srt"
        subtitle.write_text("1\n00:00:00,000 --> 00:00:02,000\nhello\n", encoding="utf-8")
        output = tmp_path / "both.mp4"

        ffmpeg_service.cut_clip(
            synthetic_video,
            output,
            0.0,
            2.0,
            video_filters=[ffmpeg_service.subtitles_filter(subtitle)],
            audio_filter="aresample=8000",
        )

        assert output.is_file()
        info = ffmpeg_service.probe_file(output)
        assert info.sample_rate == 8000


@requires_ffmpeg
class TestAudioThroughApi:
    def test_youtube_clip_records_and_applies_normalization(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "youtube"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["status"] == "ready"
        assert clip["editing_plan"]["audio_normalization"] is True
        assert "loudnorm=I=-16" in clip["editing_plan"]["audio"]["filter"]
        assert client.get(clip["file_url"]).status_code == 200

    def test_clean_clip_has_no_audio_processing(self, client, narrate_video) -> None:
        _, video = prepare_with_candidates(client, narrate_video)

        created = client.post(
            f"/api/videos/{video['id']}/generate-clips",
            json={"editing_profile": "clean"},
        )
        assert created.status_code == 202, created.text
        run_job_settle(client, created.json()["job_id"])

        clip = client.get(f"/api/videos/{video['id']}/clips").json()[0]
        assert clip["editing_plan"]["audio_normalization"] is False
        assert "audio" not in clip["editing_plan"]
