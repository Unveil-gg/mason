"""Extract a silhouette and height/width ratio from concept art."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, ImageStat

from mason.core.art import ArtAnalysis, ProportionNotes
from mason.core.assets import AssetSpec, dump_asset_spec, load_asset_spec
from mason.core.jobs import AssetJob, require_job
from mason.core.paths import resolve_project_path
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def extract_silhouette(src: Path) -> tuple[Image.Image, float]:
    """Threshold, trim, and return (L image, height/width)."""
    gray = Image.open(src).convert("L")
    mean = ImageStat.Stat(gray).mean[0]
    if mean < 128:
        gray = ImageOps.invert(gray)
    mask = gray.point(lambda p: 255 if p < 200 else 0)
    bbox = mask.getbbox()
    if bbox:
        mask = mask.crop(bbox)
    out = ImageOps.invert(mask)
    width, height = out.size
    ratio = (height / width) if width else 1.0
    return out, ratio


def silhouette_iou(current: Path, reference: Path) -> float:
    """Coarse IoU of two silhouette PNGs. Dark pixels are subject."""
    with Image.open(current) as ia, Image.open(reference) as ib:
        a = ia.convert("L").point(lambda p: 255 if p < 128 else 0)
        b = ib.convert("L").resize(a.size, Image.Resampling.NEAREST)
        b = b.point(lambda p: 255 if p < 128 else 0)
        pa = a.tobytes()
        pb = b.tobytes()
    inter = sum(x and y for x, y in zip(pa, pb))
    union = sum(x or y for x, y in zip(pa, pb))
    return inter / union if union else 0.0


def ensure_reference_silhouette(
    job: AssetJob,
    spec: AssetSpec,
) -> float | None:
    """Extract a silhouette reference on build when one is listed."""
    src = _silhouette_source(job, spec)
    if src is None or not src.is_file():
        return None
    image, ratio = extract_silhouette(src)
    dest = job.previews / "reference_silhouette.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest)
    _apply_ratio(spec, ratio)
    return ratio


def run_ingest(image: Path, asset_id: str | None) -> dict:
    """CLI entry: write a silhouette PNG and optional analysis ratio."""
    if not image.is_file():
        raise MasonError(
            f"Image not found: {image}",
            code="ingest_missing",
            context={"path": str(image)},
        )
    sil, ratio = extract_silhouette(image)
    dest = image.with_name(f"{image.stem}_silhouette.png")
    payload: dict = {
        "height_width_ratio": ratio,
        "asset_id": asset_id,
    }
    if asset_id:
        root = find_project_root()
        job = require_job(root, asset_id)
        job.prepare()
        dest = job.previews / "reference_silhouette.png"
        spec = _apply_ratio(job.load_spec(), ratio)
        job.write_spec(spec)
        job.write_art_sidecars(spec)
        meta = job.load_meta()
        if meta and meta.source_spec:
            original = root / meta.source_spec
            if original.is_file():
                dump_asset_spec(
                    _apply_ratio(load_asset_spec(original), ratio),
                    original,
                )
        payload["asset_id"] = asset_id
    dest.parent.mkdir(parents=True, exist_ok=True)
    sil.save(dest)
    payload["path"] = str(dest)
    return payload


def _silhouette_source(job: AssetJob, spec: AssetSpec) -> Path | None:
    direction = spec.art_direction
    if direction is None:
        return None
    for ref in direction.references:
        if ref.purpose == "silhouette":
            return resolve_project_path(job.project_root, ref.path)
    return None


def _apply_ratio(spec: AssetSpec, ratio: float) -> AssetSpec:
    analysis = spec.art_analysis or ArtAnalysis()
    props = analysis.proportions or ProportionNotes()
    spec.art_analysis = analysis.model_copy(
        update={"proportions": props.model_copy(
            update={"height_width_ratio": ratio},
        )},
    )
    return spec
