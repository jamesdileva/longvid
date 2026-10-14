"""Tests for filename/path safety helpers."""

from __future__ import annotations

from pathlib import Path

from app.utils.files import is_within, safe_filename, unique_filename


class TestSafeFilename:
    def test_strips_directory_components(self) -> None:
        assert safe_filename("../../etc/passwd") == "passwd"
        assert safe_filename("C:\\videos\\clip.mp4") == "clip.mp4"

    def test_replaces_unsafe_characters(self) -> None:
        assert safe_filename("my video!.mp4") == "my_video_.mp4"
        assert safe_filename("a/b&c.mkv") == "b_c.mkv"

    def test_falls_back_when_nothing_usable(self) -> None:
        assert safe_filename("///") == "file"
        assert safe_filename("..", fallback="video") == "video"

    def test_truncates_long_names_keeping_extension(self) -> None:
        name = safe_filename("x" * 300 + ".mp4")
        assert len(name) <= 120
        assert name.endswith(".mp4")

    def test_allows_safe_characters_through(self) -> None:
        assert safe_filename("My-Clip_01.final.mp4") == "My-Clip_01.final.mp4"


class TestUniqueFilename:
    def test_prefixes_random_token(self) -> None:
        first = unique_filename("clip.mp4")
        second = unique_filename("clip.mp4")

        assert first != second
        assert first.endswith("_clip.mp4")
        assert len(first.split("_")[0]) == 12

    def test_sanitizes_hostile_names(self) -> None:
        assert unique_filename("../evil.mp4").endswith("_evil.mp4")
        assert "/" not in unique_filename("../evil.mp4")


class TestIsWithin:
    def test_child_inside_parent(self, tmp_path: Path) -> None:
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        assert is_within(child, tmp_path)

    def test_outside_parent(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "elsewhere"
        assert not is_within(outside, tmp_path)

    def test_nonexistent_child_still_resolves(self, tmp_path: Path) -> None:
        assert is_within(tmp_path / "ghost" / "file.mp4", tmp_path)
