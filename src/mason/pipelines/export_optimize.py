"""Optional shrink of copied export files. Never edits the job."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from mason.errors import MasonError

ENGINES = ("generic", "godot", "unreal")
ENGINE_SUBDIRS = {
    "generic": {"glb": "models", "png": "textures", "frames": "textures"},
    "godot": {"glb": "models", "png": "textures", "frames": "textures"},
    "unreal": {"glb": "Meshes", "png": "Textures", "frames": "Textures"},
}


def require_engine(engine: str) -> str:
    """Return engine if it is a known preset."""
    if engine not in ENGINES:
        raise MasonError(
            f"Unknown export engine '{engine}'.",
            code="invalid_export_engine",
            hint="Use generic, godot, or unreal.",
        )
    return engine


def grouped_subdir(engine: str, key: str) -> str:
    """Folder name under --to for a grouped layout."""
    return ENGINE_SUBDIRS[engine].get(key, "")


def optimize_file(path: Path) -> str | None:
    """Rewrite path in place if we can shrink it.

    Returns a short method name, or None when the file is left as
    copied. Fake or unreadable bytes are skipped.
    """
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _optimize_png(path)
    if suffix == ".glb":
        return _optimize_glb(path)
    return None


def _optimize_png(path: Path) -> str | None:
    """Adaptive 256-color palette plus PNG optimize flag."""
    try:
        image = Image.open(path)
        image.load()
    except OSError:
        return None
    if image.mode not in ("P", "1"):
        image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    image.save(path, format="PNG", optimize=True)
    return "quantize"


def _optimize_glb(path: Path) -> str | None:
    """Run gltfpack when it is on PATH. Leave the copy on failure."""
    tool = shutil.which("gltfpack")
    if not tool:
        return None
    with tempfile.TemporaryDirectory() as raw:
        dest = Path(raw) / "packed.glb"
        try:
            proc = subprocess.run(
                [tool, "-i", str(path), "-o", str(dest), "-cc"],
                capture_output=True,
                check=False,
            )
        except OSError:
            return None
        if proc.returncode != 0 or not dest.is_file():
            return None
        path.write_bytes(dest.read_bytes())
        return "gltfpack"
