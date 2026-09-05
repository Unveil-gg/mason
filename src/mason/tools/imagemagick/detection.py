"""Find ImageMagick magick or convert."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mason.tools.detect import first_existing, parse_version_token, run_version, which


def common_magick_paths() -> list[Path]:
    paths: list[Path] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            root = Path(base)
            for pattern in root.glob("ImageMagick*"):
                paths.append(pattern / "magick.exe")
    elif sys.platform == "darwin":
        paths.extend([
            Path("/opt/homebrew/bin/magick"),
            Path("/usr/local/bin/magick"),
        ])
    else:
        paths.extend([
            Path("/usr/bin/magick"),
            Path("/usr/local/bin/magick"),
        ])
    return paths


def _is_windows_convert(path: Path) -> bool:
    """True for the Windows FAT convert.exe, not ImageMagick."""
    parts = {p.lower() for p in path.parts}
    return "system32" in parts or "syswow64" in parts


def find_magick(override: Path | None = None) -> Path | None:
    if override and override.is_file():
        return override.resolve()
    on_path = which("magick") or which("magick.exe")
    if on_path:
        return on_path
    found = first_existing(common_magick_paths())
    if found:
        return found
    convert = which("convert") or which("convert.exe")
    if convert and not _is_windows_convert(convert):
        return convert
    return None


def magick_version(executable: Path) -> str | None:
    args = ["--version"]
    if executable.name.lower().startswith("convert"):
        args = ["-version"]
    code, text = run_version(executable, args)
    if "imagemagick" not in text.lower():
        return None
    if code != 0 and not text:
        return None
    return parse_version_token(text)
