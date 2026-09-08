"""Build the critic compare plate and regression flag."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from mason.core.jobs import AssetJob, require_job
from mason.core.workspace import find_project_root
from mason.pipelines.ingest import silhouette_iou


def write_compare_plate(job: AssetJob) -> Path | None:
    """Write previews/compare.png. Returns the path, or None.

    Layout is [current silhouette, current beauty; previous
    iteration's beauty (frozen, for regression diffing), reference
    or detail crop]. Each tile is captioned so "previous iteration"
    is never mistaken for the live model.
    """
    job.previews.mkdir(parents=True, exist_ok=True)
    current_sil = _current_silhouette(job)
    current_beauty = _current_beauty(job)
    if current_sil is None and current_beauty is None:
        return None
    size = _tile_size(current_sil or current_beauty)
    prev_dir = _previous_preview_dir(job)
    prev_beauty = _first_existing(prev_dir, (
        "three_quarter.png", "full.png", "silhouette_front.png",
    ))
    prev_n = None
    if prev_dir is not None and prev_dir.parent.name.isdigit():
        prev_n = int(prev_dir.parent.name)
    prev_label = f"previous (iter {prev_n:03d})" if prev_n else "previous"
    ref = job.previews / "reference_silhouette.png"
    detail = _first_existing(job.previews, (
        "detail.png", "full.png",
    ))
    corner = ref if ref.is_file() else detail
    corner_label = "reference" if ref.is_file() else "detail"
    tiles = [
        _load_tile(current_sil, size, label="current silhouette"),
        _load_tile(current_beauty, size, label="current"),
        _load_tile(
            prev_beauty, size, empty="no previous", label=prev_label,
        ),
        _load_tile(corner, size, empty="no detail", label=corner_label),
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
    older_s = older.scores.silhouette
    newer_s = newer.scores.silhouette
    if older_s is None or newer_s is None:
        return False
    return newer_s < older_s


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


def _first_existing(
    folder: Path | None,
    names: tuple[str, ...],
) -> Path | None:
    if folder is None:
        return None
    for name in names:
        path = folder / name
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
        name = "three_quarter.png"
        if current is not None and (folder / current.name).is_file():
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
    label: str = "",
) -> Image.Image:
    if path is not None and path.is_file():
        img = Image.open(path).convert("RGB")
        if img.size != size:
            img = img.resize(size)
    else:
        img = Image.new("RGB", size, (36, 36, 36))
        draw = ImageDraw.Draw(img)
        draw.text((12, max(size[1] // 2 - 6, 8)), empty, fill=(200, 200, 200))
    if label:
        _caption(img, label)
    return img


def _caption(tile: Image.Image, label: str) -> None:
    """Stamp a small top-left caption bar so tiles are self-labeling
    (e.g. "previous" is never mistaken for "current")."""
    bar_h = min(14, max(tile.height // 4, 8))
    draw = ImageDraw.Draw(tile)
    draw.rectangle((0, 0, tile.width, bar_h), fill=(0, 0, 0))
    draw.text((3, 1), label, fill=(255, 255, 255))


def reference_iou(job: AssetJob) -> float | None:
    current = _current_silhouette(job)
    ref = job.previews / "reference_silhouette.png"
    if current is None or not ref.is_file():
        return None
    return silhouette_iou(current, ref)
