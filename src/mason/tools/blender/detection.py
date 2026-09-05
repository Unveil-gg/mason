"""Find a Blender executable on this machine."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mason.tools.detect import first_existing, parse_version_token, run_version, which


def common_blender_paths() -> list[Path]:
    """Likely install locations for the current OS."""
    paths: list[Path] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            root = Path(base) / "Blender Foundation"
            if root.is_dir():
                for child in sorted(root.iterdir(), reverse=True):
                    exe = child / "blender.exe"
                    paths.append(exe)
        paths.append(Path(r"C:\Program Files\Blender Foundation"))
    elif sys.platform == "darwin":
        paths.append(
            Path("/Applications/Blender.app/Contents/MacOS/Blender"),
        )
    else:
        paths.extend([
            Path("/usr/bin/blender"),
            Path("/usr/local/bin/blender"),
            Path("/snap/bin/blender"),
            Path.home() / ".local/bin/blender",
        ])
        flatpak = Path.home() / ".local/share/flatpak/exports/bin/blender"
        paths.append(flatpak)
    return paths


def find_blender(override: Path | None = None) -> Path | None:
    """Search override, PATH, then common locations."""
    if override and override.is_file():
        return override.resolve()
    on_path = which("blender") or which("blender.exe")
    if on_path:
        return on_path
    return first_existing(common_blender_paths())


def blender_version(executable: Path) -> str | None:
    """Run blender --version and parse the version string."""
    code, text = run_version(executable, ["--version"])
    if code != 0 and not text:
        return None
    return parse_version_token(text)
