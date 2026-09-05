"""Find Krita and kritarunner."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mason.tools.detect import first_existing, parse_version_token, run_version, which


def common_krita_paths() -> list[Path]:
    paths: list[Path] = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            for name in (
                Path(base) / "Krita (x64)" / "bin" / "krita.exe",
                Path(base) / "Krita" / "bin" / "krita.exe",
            ):
                paths.append(name)
    elif sys.platform == "darwin":
        paths.append(
            Path("/Applications/krita.app/Contents/MacOS/krita"),
        )
    else:
        paths.extend([
            Path("/usr/bin/krita"),
            Path("/usr/local/bin/krita"),
            Path("/snap/bin/krita"),
        ])
    return paths


def find_krita(override: Path | None = None) -> Path | None:
    if override and override.is_file():
        return override.resolve()
    on_path = which("krita") or which("krita.exe")
    if on_path:
        return on_path
    return first_existing(common_krita_paths())


def find_kritarunner(krita: Path | None) -> Path | None:
    """Sibling kritarunner next to krita, then PATH."""
    if krita is not None:
        sibling = krita.with_name(
            "kritarunner.exe" if krita.suffix == ".exe" else "kritarunner",
        )
        if sibling.is_file():
            return sibling.resolve()
    return which("kritarunner") or which("kritarunner.exe")


def krita_version(executable: Path) -> str | None:
    code, text = run_version(executable, ["--version"])
    if code != 0 and not text:
        return None
    return parse_version_token(text)
