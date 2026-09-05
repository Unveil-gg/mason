"""Find Aseprite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mason.tools.detect import first_existing, parse_version_token, run_version, which


def common_aseprite_paths() -> list[Path]:
    paths: list[Path] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            paths.extend([
                Path(base) / "Aseprite" / "Aseprite.exe",
                Path(base) / "Steam" / "steamapps" / "common" / "Aseprite" / "Aseprite.exe",
            ])
    elif sys.platform == "darwin":
        paths.append(
            Path("/Applications/Aseprite.app/Contents/MacOS/aseprite"),
        )
    else:
        paths.extend([
            Path("/usr/bin/aseprite"),
            Path("/usr/local/bin/aseprite"),
        ])
    return paths


def find_aseprite(override: Path | None = None) -> Path | None:
    if override and override.is_file():
        return override.resolve()
    on_path = which("aseprite") or which("aseprite.exe")
    if on_path:
        return on_path
    return first_existing(common_aseprite_paths())


def aseprite_version(executable: Path) -> str | None:
    code, text = run_version(executable, ["--version"])
    if code != 0 and not text:
        return None
    return parse_version_token(text)
