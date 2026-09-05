"""Executable discovery and version parsing (no real tools)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mason.tools.detect import parse_version_token
from mason.tools.blender.detection import find_blender
from mason.tools.imagemagick.detection import find_magick


def test_parse_version_token() -> None:
    assert parse_version_token("Blender 4.5.2") == "4.5.2"
    assert parse_version_token("Version: ImageMagick 7.1.1") == "7.1.1"
    assert parse_version_token("no version here") is None


def test_find_blender_override(tmp_path: Path) -> None:
    exe = tmp_path / "blender.exe"
    exe.write_text("", encoding="utf-8")
    found = find_blender(exe)
    assert found == exe.resolve()


def test_find_blender_path() -> None:
    fake = Path("/tmp/fake-blender")
    with patch("mason.tools.blender.detection.which", return_value=fake):
        assert find_blender() == fake


def test_find_magick_override(tmp_path: Path) -> None:
    exe = tmp_path / "magick.exe"
    exe.write_text("", encoding="utf-8")
    assert find_magick(exe) == exe.resolve()


def test_skips_windows_system32_convert() -> None:
    from mason.tools.imagemagick.detection import _is_windows_convert

    fake = Path(r"C:\Windows\System32\convert.EXE")
    assert _is_windows_convert(fake)
