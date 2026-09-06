"""Build the critic compare plate and regression flag."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from mason.core.jobs import AssetJob, require_job
from mason.core.workspace import find_project_root
from mason.pipelines.ingest import silhouette_iou


def write_compare_plate(job: AssetJob) -> Path | None:
    """Write previews/compare.png. Returns the path, or None."""
    job.previews.mkdir(parents=True, exist_ok=True)
    current_sil = _current_silhouette(job)
    current_beauty = _current_beauty(job)
    if current_sil is None and current_beauty is None:
        return None
    size = _tile_size(current_sil or current_beauty)
    prev_dir = _previous_preview_dir(job)
    prev_name = (
        "silhouette_front.png"
        if (job.previews / "silhouette_front.png").is_file()
        else "full.png"
    )
    prev = None
    if prev_dir is not None and (prev_dir / prev_name).is_file():
        prev = prev_dir / prev_name
    ref = job.previews / "reference_silhouette.png"
    tiles = [
        _load_tile(current_sil, size),
        _load_tile(current_beauty, size),
        _load_tile(prev, size, empty="no previous"),
        _load_tile(
            ref if ref.is_file() else None,
            size,
            empty="no reference",
        ),
    ]
    sheet = Image.new("RGB", (size[0] * 2, size[1] * 2), (0, 0, 0))
    for index, tile in enumerate(tiles):
        col, row = index % 2, index // 2
        sheet.paste(tile, (col * size[0], row * size[1]))
    dest = job.previews / "compare.png"
    sheet.save(dest)
    return dest


def compare_payload(job: AssetJob) -> dict:
    """Write the plate and return inspect-style compare JSON."""
    path = write_compare_plate(job)
    meta = job.load_meta()
    current = meta.iteration if meta else 0
    prev_dir = _previous_preview_dir(job)
    prev_n = None
    if prev_dir is not None and prev_dir.parent.name.isdigit():
        prev_n = int(prev_dir.parent.name)
    payload = {
        "compare": job.rel(path) if path else None,
        "iteration": current,
        "previous_iteration": prev_n,
        "silhouette_regressed": silhouette_regressed(job),
    }
    iou = reference_iou(job)
    if iou is not None:
        payload["silhouette_iou"] = iou
    return payload


def silhouette_regressed(job: AssetJob) -> bool:
    """True if the last two evaluations exist and silhouette dropped."""
    found = job.list_evaluations()
    if len(found) < 2:
        return False
    older = job.load_evaluation(found[-2][0])
    newer = job.load_evaluation(found[-1][0])
    if older is None or newer is None:
        return False
    return newer.scores.silhouette < older.scores.silhouette


def run_compare(asset_id: str) -> dict:
    """CLI entry: write compare.png for an existing job."""
    root = find_project_root()
    job = require_job(root, asset_id)
    return compare_payload(job)


def _current_silhouette(job: AssetJob) -> Path | None:
    for name in ("silhouette_front.png", "full.png"):
        path = job.previews / name
        if path.is_file():
            return path
    return None


def _current_beauty(job: AssetJob) -> Path | None:
    for name in ("three_quarter.png", "full.png"):
        path = job.previews / name
        if path.is_file():
            return path
    return None


def _previous_preview_dir(job: AssetJob) -> Path | None:
    current = _current_silhouette(job)
    current_bytes = current.read_bytes() if current and current.is_file() else None
    for number in reversed(job.list_iterations()):
        folder = job.iterations / f"{number:03d}" / "previews"
        name = "silhouette_front.png"
        if current is not None:
            name = current.name
        candidate = folder / name
        if not candidate.is_file():
            continue
        if current_bytes is not None and candidate.read_bytes() == current_bytes:
            continue
        return folder
    return None


def _tile_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def _load_tile(
    path: Path | None,
    size: tuple[int, int],
    empty: str = "missing",
) -> Image.Image:
    if path is not None and path.is_file():
        img = Image.open(path).convert("RGB")
        if img.size != size:
            img = img.resize(size)
        return img
    tile = Image.new("RGB", size, (36, 36, 36))
    draw = ImageDraw.Draw(tile)
    draw.text((12, max(size[1] // 2 - 6, 8)), empty, fill=(200, 200, 200))
    return tile


def reference_iou(job: AssetJob) -> float | None:
    current = _current_silhouette(job)
    ref = job.previews / "reference_silhouette.png"
    if current is None or not ref.is_file():
        return None
    return silhouette_iou(current, ref)
