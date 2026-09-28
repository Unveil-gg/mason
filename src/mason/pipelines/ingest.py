"""Measure a reference image with OpenCV and hand the result to Mason.

`mason ingest` does not compile an image into a mesh. It writes a
structured `ImageAnalysis` document (silhouette ratio, k-means
palette, a few color regions, a simplified contour, edge character),
merges the measured facts into `art_analysis` on an existing spec, or
-- when the named asset has no spec yet -- writes a minimal buildable
scaffold. Parts and layers are always authored by the agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from mason.core.art import (
    ArtAnalysis,
    ArtDirection,
    ImageAnalysis,
    ImageBBox,
    ImageRegion,
    PaletteDistribution,
    PaletteHexes,
    PaletteKeys,
    ProportionNotes,
    ReferenceImage,
    ShapeLanguageNotes,
    SourceSize,
)
from mason.core.ref_analysis import ReferenceAnalysis, ReferenceView
from mason.core.assets import (
    AssetSpec,
    Dimensions3D,
    GeometrySpec,
    LayerRect,
    LayeredRasterSpec,
    PixelDimensions,
    PropPart,
    RasterLayer,
    StaticPropSpec,
    dump_asset_spec,
    load_asset_spec,
)
from mason.core.config import load_project_config
from mason.core.jobs import AssetJob
from mason.core.paths import resolve_project_path
from mason.core.runs import record_ingest_run
from mason.core.styles import StyleProfile, resolve_style
from mason.core.workspace import find_project_root
from mason.errors import MasonError
from mason.pipelines.fetch import fetch_reference
from mason.pipelines.silhouette import (
    extract_silhouette,
    mask_extrema,
    silhouette_iou,
    subject_mask,
    width_samples,
)

_MAX_REGIONS = 6
_REGION_K = 6
_MIN_REGION_FRACTION = 0.01
_REGION_MAX_DIM = 400
_EDGE_HARD_THRESHOLD = 0.06
_SCAFFOLD_MAX_CANVAS = 2048
_SCAFFOLD_TYPES = ("static_prop", "layered_raster")




def ensure_reference_silhouette(
    job: AssetJob,
    spec: AssetSpec,
) -> float | None:
    """Extract a silhouette reference on build when one is listed."""
    sources = _silhouette_sources(job, spec)
    if not sources:
        return None
    ratio = None
    dest_dir = job.previews
    dest_dir.mkdir(parents=True, exist_ok=True)
    for view, src in sources.items():
        if not src.is_file():
            continue
        image, measured = extract_silhouette(src)
        name = (
            "reference_silhouette.png"
            if view == "default"
            else f"reference_silhouette_{view}.png"
        )
        image.save(dest_dir / name)
        if view == "default" or ratio is None:
            ratio = measured
            if view != "default":
                image.save(dest_dir / "reference_silhouette.png")
    if ratio is None:
        return None
    _apply_ratio(spec, ratio)
    return ratio


def analyze_image(
    path: Path,
    style: StyleProfile | None = None,
) -> ImageAnalysis:
    """Measure silhouette, palette, regions, contour, and edges with
    OpenCV. Deterministic; no ML segmentation."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise MasonError(
            f"Could not read image: {path}",
            code="ingest_unreadable",
            context={"path": str(path)},
        )
    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask, (bx, by, bw, bh) = _subject_mask(gray)
    ratio = (bh / bw) if bw else 1.0
    palette = _subject_palette(bgr, mask)
    return ImageAnalysis(
        source=str(path),
        source_size=SourceSize(width=width, height=height),
        bbox=ImageBBox(x=bx, y=by, width=bw, height=bh),
        height_width_ratio=round(ratio, 4),
        palette=palette,
        palette_keys=_map_palette_keys(palette, style),
        regions=_color_regions(bgr),
        contour=_contour_points(mask, (bx, by, bw, bh)),
        edges=_edge_character(gray),
    )


def _subject_mask(
    gray: np.ndarray,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Threshold + invert-if-needed, matching `extract_silhouette`.
    Returns (mask, bbox); mask is 255 on the subject."""
    mask = subject_mask(gray)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        h, w = gray.shape
        return mask, (0, 0, w, h)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return mask, (x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def _contour_points(
    mask: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> list[tuple[float, float]]:
    """Largest external contour, simplified and normalized to the
    bbox (0..1). A silhouette shape hint, not a traced mesh."""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return []
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) <= 0:
        return []
    perimeter = cv2.arcLength(largest, True)
    epsilon = max(perimeter * 0.01, 1.0)
    simplified = cv2.approxPolyDP(largest, epsilon, True)
    points = simplified.reshape(-1, 2)
    if len(points) > 16:
        step = max(1, len(points) // 16)
        points = points[::step][:16]
    x, y, w, h = bbox
    w, h = max(w, 1), max(h, 1)
    return [
        (round((float(px) - x) / w, 4), round((float(py) - y) / h, 4))
        for px, py in points
    ]


def _to_hex(bgr_pixel) -> str:
    b, g, r = (int(round(v)) for v in bgr_pixel[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


def _kmeans(pixels: np.ndarray, k: int) -> list[tuple[np.ndarray, int]]:
    """K-means over Nx3 float32 pixels. Returns (center_bgr, count)
    sorted by count descending."""
    if len(pixels) == 0:
        return []
    unique = np.unique(pixels, axis=0)
    k = max(1, min(k, len(unique)))
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5,
    )
    _, labels, centers = cv2.kmeans(
        pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS,
    )
    counts = np.bincount(labels.flatten(), minlength=k)
    order = np.argsort(-counts)
    return [(centers[i], int(counts[i])) for i in order]


def _subject_palette(bgr: np.ndarray, mask: np.ndarray) -> PaletteHexes:
    """Dominant/secondary/accent hex from k-means on subject pixels."""
    pixels = bgr[mask > 0].astype(np.float32)
    clusters = _kmeans(pixels, 3)
    hexes = [_to_hex(center) for center, _ in clusters]
    hexes += [""] * (3 - len(hexes))
    return PaletteHexes(dominant=hexes[0], secondary=hexes[1], accent=hexes[2])


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")[:6]
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _nearest_key(hex_value: str, palette: dict[str, str]) -> str | None:
    """Nearest style palette key to a measured hex, by RGB distance.
    Never invents a hex outside the given style."""
    if not hex_value or not palette:
        return None
    try:
        target = _hex_to_rgb(hex_value)
    except ValueError:
        return None
    best_key, best_dist = None, None
    for key, value in palette.items():
        try:
            rgb = _hex_to_rgb(value)
        except ValueError:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(target, rgb))
        if best_dist is None or dist < best_dist:
            best_key, best_dist = key, dist
    return best_key


def _map_palette_keys(
    palette: PaletteHexes, style: StyleProfile | None,
) -> PaletteKeys:
    if style is None or not style.palette:
        return PaletteKeys()
    return PaletteKeys(
        dominant=_nearest_key(palette.dominant, style.palette),
        secondary=_nearest_key(palette.secondary, style.palette),
        accent=_nearest_key(palette.accent, style.palette),
    )


def _color_regions(bgr: np.ndarray) -> list[ImageRegion]:
    """A few large same-color blobs, largest first. Drops tiny noise
    below `_MIN_REGION_FRACTION` of the (downscaled) image."""
    height, width = bgr.shape[:2]
    scale = 1.0
    work = bgr
    if max(height, width) > _REGION_MAX_DIM:
        scale = _REGION_MAX_DIM / max(height, width)
        work = cv2.resize(
            bgr, (max(int(width * scale), 1), max(int(height * scale), 1)),
            interpolation=cv2.INTER_AREA,
        )
    wh, ww = work.shape[:2]
    pixels = work.reshape(-1, 3).astype(np.float32)
    unique = np.unique(pixels, axis=0)
    if len(unique) == 0:
        return []
    k = max(1, min(_REGION_K, len(unique)))
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5,
    )
    _, labels, centers = cv2.kmeans(
        pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS,
    )
    label_map = labels.reshape(wh, ww).astype(np.uint8)
    min_area = max(9.0, _MIN_REGION_FRACTION * wh * ww)
    found: list[tuple[float, ImageRegion]] = []
    for idx in range(k):
        blob = np.where(label_map == idx, 255, 0).astype(np.uint8)
        count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
            blob, connectivity=8,
        )
        for comp in range(1, count):
            area = float(stats[comp, cv2.CC_STAT_AREA])
            if area < min_area:
                continue
            x = stats[comp, cv2.CC_STAT_LEFT]
            y = stats[comp, cv2.CC_STAT_TOP]
            w = stats[comp, cv2.CC_STAT_WIDTH]
            h = stats[comp, cv2.CC_STAT_HEIGHT]
            found.append((
                area,
                ImageRegion(
                    x=int(round(x / scale)),
                    y=int(round(y / scale)),
                    width=max(int(round(w / scale)), 1),
                    height=max(int(round(h / scale)), 1),
                    hex=_to_hex(centers[idx]),
                ),
            ))
    found.sort(key=lambda item: -item[0])
    return [region for _, region in found[:_MAX_REGIONS]]


def _edge_character(gray: np.ndarray) -> str:
    """`hard` (crisp man-made edges) vs `soft` (organic/painterly)."""
    edges = cv2.Canny(gray, 50, 150)
    density = float(np.count_nonzero(edges)) / edges.size
    return "hard" if density >= _EDGE_HARD_THRESHOLD else "soft"


def _draw_regions(
    image: Path, regions: list[ImageRegion], dest: Path,
) -> None:
    """Diagnostic overlay: region boxes on a copy of the source."""
    with Image.open(image) as src:
        canvas = src.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    for region in regions:
        box = (
            region.x, region.y,
            region.x + region.width, region.y + region.height,
        )
        draw.rectangle(box, outline=region.hex or "#FF00FF", width=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)


def run_ingest(
    image: Path | None,
    asset_id: str | None,
    *,
    style_name: str | None = None,
    spec_type: str | None = None,
    out: Path | None = None,
    fetch_url: str | None = None,
    view: str | None = None,
    component: str | None = None,
    purpose: str | None = None,
) -> dict:
    """CLI entry: measure a reference image and hand it to Mason.

    With `--asset` naming a job that already has a spec, only
    `art_analysis` is merged (parts/layers are never touched). With
    `--asset` naming a new id, a minimal buildable scaffold is
    written instead (`--type` picks static_prop or layered_raster).
    `--fetch` downloads into `.mason/jobs/<id>/refs/` first.
    """
    started = datetime.now(timezone.utc)
    fetched_from = None
    if fetch_url and image is not None:
        raise MasonError(
            "Pass a local image or --fetch, not both.",
            code="ingest_ambiguous",
        )
    if fetch_url:
        if not asset_id:
            raise MasonError(
                "ingest --fetch needs --asset.",
                code="ingest_fetch_needs_asset",
                hint="mason ingest --fetch URL --asset <id>",
            )
        root = find_project_root()
        refs = AssetJob(root, asset_id).dir / "refs"
        image = fetch_reference(fetch_url, refs)
        fetched_from = fetch_url
    if image is None:
        raise MasonError(
            "ingest needs an image path or --fetch.",
            code="ingest_missing",
            hint="mason ingest <image> | mason ingest --fetch URL --asset <id>",
        )
    if not image.is_file():
        raise MasonError(
            f"Image not found: {image}",
            code="ingest_missing",
            context={"path": str(image)},
        )
    sil, ratio = extract_silhouette(image)
    root: Path | None = None
    style: StyleProfile | None = None
    if asset_id:
        root = find_project_root()
        project = load_project_config(root)
        style = resolve_style(root, style_name or "", project.default_style)
    elif style_name:
        root = find_project_root()
        project = load_project_config(root)
        style = resolve_style(root, style_name, project.default_style)
    analysis = analyze_image(image, style)

    payload: dict = {
        "height_width_ratio": ratio,
        "asset_id": asset_id,
        "analysis": analysis.model_dump(mode="json"),
    }

    dest = image.with_name(f"{image.stem}_silhouette.png")
    regions_dest = image.with_name(f"{image.stem}_regions.png")
    if asset_id:
        assert root is not None
        job = AssetJob(root, asset_id)
        if job.exists():
            spec = _merge_ingest(
                job.load_spec(), ratio, analysis, view, image,
                component, purpose,
            )
            job.write_spec(spec)
            job.write_art_sidecars(spec)
            meta = job.load_meta()
            if meta and meta.source_spec:
                original = root / meta.source_spec
                if original.is_file():
                    updated = _merge_ingest(
                        load_asset_spec(original), ratio, analysis,
                        view, image, component, purpose,
                    )
                    dump_asset_spec(updated, original)
        else:
            _spec, scaffold_path = _write_scaffold(
                root, asset_id, spec_type or "static_prop",
                image, analysis, ratio, style, out,
            )
            job.prepare()
            job.write_spec(_spec)
            job.write_meta(_rel(root, scaffold_path))
            job.write_art_sidecars(_spec)
            payload["scaffold"] = _rel(root, scaffold_path)
        dest = _silhouette_dest(job, view, component, purpose)
        regions_dest = job.previews / "reference_regions.png"
        payload["asset_id"] = asset_id
        payload["view"] = view
        payload["component"] = component
        payload["purpose"] = purpose
        if purpose == "correction" and asset_id:
            cached = _cache_correction(job, image, view, component)
            payload["correction"] = _rel(root, cached) if root else str(cached)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sil.save(dest)
    if (
        asset_id
        and purpose != "correction"
        and _write_whole_object_silhouette(job, component)
    ):
        primary = job.previews / "reference_silhouette.png"
        if dest.resolve() != primary.resolve():
            sil.save(primary)
        if view:
            named = job.previews / f"reference_silhouette_{view}.png"
            if dest.resolve() != named.resolve():
                sil.save(named)
    payload["path"] = str(dest)
    if fetched_from:
        payload["source_url"] = fetched_from
        payload["fetched"] = str(image)
    if analysis.regions:
        _draw_regions(image, analysis.regions, regions_dest)
        payload["regions_preview"] = str(regions_dest)
    if asset_id:
        job = AssetJob(root or find_project_root(), asset_id)
        record_ingest_run(
            job,
            source=fetched_from or str(image),
            started_at=started,
        )
    return payload


def _rel(root: Path, path: Path) -> str:
    """Project-relative POSIX path if possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _silhouette_source(job: AssetJob, spec: AssetSpec) -> Path | None:
    sources = _silhouette_sources(job, spec)
    if "default" in sources:
        return sources["default"]
    if sources:
        return next(iter(sources.values()))
    return None


def _silhouette_sources(job: AssetJob, spec: AssetSpec) -> dict[str, Path]:
    """Map view name (or default) to a silhouette reference path."""
    direction = spec.art_direction
    if direction is None:
        return {}
    found: dict[str, Path] = {}
    for ref in direction.references:
        if ref.purpose != "silhouette" or ref.component:
            continue
        path = resolve_project_path(job.project_root, ref.path)
        key = ref.view or "default"
        found[key] = path
    return found


def _merge_ingest(
    spec: AssetSpec,
    ratio: float,
    analysis: ImageAnalysis,
    view: str | None,
    image: Path,
    component: str | None,
    purpose: str | None = None,
) -> AssetSpec:
    """Merge CV facts. Component isolates skip parent art_analysis."""
    if purpose != "correction":
        if not component or _is_component_job(spec, component):
            spec = _apply_analysis(spec, ratio, analysis)
    spec = _apply_reference_view(
        spec, analysis, ratio, view, image, component,
        purpose=purpose,
    )
    if purpose == "correction":
        spec = _bind_correction_reference(spec, image, view, component)
    else:
        spec = _bind_component_reference(spec, image, view, component)
    return spec


def _is_component_job(spec: AssetSpec, component: str) -> bool:
    """True when this job is the named component, not the parent."""
    if spec.id == component:
        return True
    return spec.id.endswith("__" + component)


def _silhouette_dest(
    job, view: str | None, component: str | None,
    purpose: str | None = None,
) -> Path:
    """Preview path for an ingested silhouette."""
    if purpose == "correction":
        suffix = "_".join(
            part for part in (component, view or "default") if part
        )
        return job.previews / f"correction_silhouette_{suffix}.png"
    if component:
        suffix = view or "default"
        return job.previews / (
            f"reference_silhouette_{component}_{suffix}.png"
        )
    if view:
        return job.previews / f"reference_silhouette_{view}.png"
    return job.previews / "reference_silhouette.png"


def _cache_correction(
    job: AssetJob,
    image: Path,
    view: str | None,
    component: str | None,
) -> Path:
    """Copy a paintover into the job refs cache."""
    refs = job.dir / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    suffix = "_".join(
        part for part in (component, view or "default") if part
    )
    dest = refs / f"correction_{suffix}.png"
    dest.write_bytes(image.read_bytes())
    return dest


def _bind_correction_reference(
    spec: AssetSpec,
    image: Path,
    view: str | None,
    component: str | None,
) -> AssetSpec:
    """Record a purpose=correction paintover on art_direction."""
    direction = spec.art_direction or ArtDirection()
    refs = list(direction.references)
    path = str(image)
    already = any(
        row.path == path and row.purpose == "correction"
        and row.component == component and row.view == view
        for row in refs
    )
    if not already:
        refs.append(ReferenceImage(
            path=path,
            purpose="correction",
            view=view,
            component=component,
        ))
        spec.art_direction = direction.model_copy(
            update={"references": refs},
        )
    return spec


def _write_whole_object_silhouette(job, component: str | None) -> bool:
    """Also write unscoped silhouettes on component jobs."""
    if not component:
        return True
    try:
        spec = job.load_spec()
    except Exception:
        return False
    return _is_component_job(spec, component)


def _bind_component_reference(
    spec: AssetSpec,
    image: Path,
    view: str | None,
    component: str | None,
) -> AssetSpec:
    """Record a purpose=component reference on art_direction."""
    if not component:
        return spec
    direction = spec.art_direction or ArtDirection()
    refs = list(direction.references)
    path = str(image)
    already = any(
        row.path == path
        and row.purpose == "component"
        and row.component == component
        for row in refs
    )
    if not already:
        refs.append(ReferenceImage(
            path=path,
            purpose="component",
            view=view,
            component=component,
        ))
        spec.art_direction = direction.model_copy(
            update={"references": refs},
        )
    return spec


def _apply_reference_view(
    spec: AssetSpec,
    analysis: ImageAnalysis,
    ratio: float,
    view: str | None,
    image: Path,
    component: str | None = None,
    purpose: str | None = None,
) -> AssetSpec:
    """Merge one measured view into reference_analysis. No parts."""
    if not view and not component and purpose != "correction":
        return spec
    view_name = view or "default"
    profile = [
        (round(u, 4), round(1.0 - v, 4)) for u, v in analysis.contour
    ]
    mask = subject_mask(
        np.array(Image.open(image).convert("L")),
    )
    entry = ReferenceView(
        view=view_name,
        path=str(image),
        purpose=(
            purpose or ("component" if component else "silhouette")
        ),
        component=component,
        height_width_ratio=round(ratio, 4),
        contour=list(analysis.contour),
        profile=profile,
        com=_mask_com(mask),
        widths=width_samples(mask),
        landmarks=mask_extrema(mask),
    )
    current = spec.reference_analysis or ReferenceAnalysis()
    views = [
        row for row in current.views
        if not (row.view == view_name and row.component == component)
    ]
    views.append(entry)
    spec.reference_analysis = current.model_copy(update={"views": views})
    return spec


def _mask_com(mask: np.ndarray) -> tuple[float, float] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    h, w = mask.shape[:2]
    return (round(float(xs.mean()) / w, 4), round(float(ys.mean()) / h, 4))


def _apply_ratio(spec: AssetSpec, ratio: float) -> AssetSpec:
    """Build-time-only ratio patch (no CV pass). Used by
    `ensure_reference_silhouette` so plain builds stay fast."""
    analysis = spec.art_analysis or ArtAnalysis()
    props = analysis.proportions or ProportionNotes()
    spec.art_analysis = analysis.model_copy(
        update={"proportions": props.model_copy(
            update={"height_width_ratio": ratio},
        )},
    )
    return spec


def _apply_analysis(
    spec: AssetSpec, ratio: float, analysis: ImageAnalysis,
) -> AssetSpec:
    """Merge measured CV facts into `art_analysis`. Never touches
    `parts` / `layers`."""
    current = spec.art_analysis or ArtAnalysis()
    props = current.proportions.model_copy(
        update={"height_width_ratio": ratio},
    )
    palette = current.palette_distribution.model_copy(update={
        "dominant": analysis.palette.dominant
        or current.palette_distribution.dominant,
        "secondary": analysis.palette.secondary
        or current.palette_distribution.secondary,
        "accent": analysis.palette.accent
        or current.palette_distribution.accent,
    })
    shape = current.shape_language.model_copy(
        update={"edges": analysis.edges},
    )
    spec.art_analysis = current.model_copy(update={
        "proportions": props,
        "palette_distribution": palette,
        "shape_language": shape,
        "source_size": analysis.source_size,
        "regions": list(analysis.regions),
    })
    return spec


def _analysis_to_art(analysis: ImageAnalysis, ratio: float) -> ArtAnalysis:
    return ArtAnalysis(
        shape_language=ShapeLanguageNotes(edges=analysis.edges),
        proportions=ProportionNotes(height_width_ratio=ratio),
        palette_distribution=PaletteDistribution(
            dominant=analysis.palette.dominant,
            secondary=analysis.palette.secondary,
            accent=analysis.palette.accent,
        ),
        source_size=analysis.source_size,
        regions=list(analysis.regions),
    )


def _write_scaffold(
    root: Path,
    asset_id: str,
    spec_type: str,
    image: Path,
    analysis: ImageAnalysis,
    ratio: float,
    style: StyleProfile | None,
    out: Path | None,
) -> tuple[AssetSpec, Path]:
    """Write a minimal, buildable spec from measured analysis. The
    agent still authors real `parts` / `layers`."""
    if spec_type not in _SCAFFOLD_TYPES:
        raise MasonError(
            f"Unsupported scaffold type '{spec_type}'.",
            code="ingest_bad_type",
            hint="Use static_prop or layered_raster.",
        )
    image_ref = _rel(root, image)
    style_name = style.name if style else None
    if spec_type == "static_prop":
        spec: AssetSpec = _scaffold_static_prop(
            asset_id, image_ref, analysis, ratio, style_name,
        )
    else:
        spec = _scaffold_layered_raster(
            asset_id, image_ref, analysis, ratio, style_name,
        )
    path = out if out else Path("assets") / f"{asset_id}.yaml"
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_asset_spec(spec, path)
    return spec, path


def _scaffold_static_prop(
    asset_id: str,
    image_ref: str,
    analysis: ImageAnalysis,
    ratio: float,
    style_name: str | None,
) -> StaticPropSpec:
    height = round(ratio, 3) if ratio > 0 else 1.0
    height = max(height, 0.05)
    return StaticPropSpec(
        type="static_prop",
        id=asset_id,
        name=asset_id.replace("_", " ").title(),
        dimensions=Dimensions3D(width=1.0, depth=1.0, height=height),
        style=style_name or "default",
        geometry=GeometrySpec(parts=[
            PropPart(
                name="mass",
                shape="box",
                size=(1.0, 1.0, height),
                location=(0.0, 0.0, height / 2.0),
            ),
        ]),
        art_direction=ArtDirection(
            subject=asset_id.replace("_", " "),
            references=[
                ReferenceImage(path=image_ref, purpose="silhouette"),
                ReferenceImage(path=image_ref, purpose="color"),
            ],
        ),
        art_analysis=_analysis_to_art(analysis, ratio),
    )


def _scaffold_layered_raster(
    asset_id: str,
    image_ref: str,
    analysis: ImageAnalysis,
    ratio: float,
    style_name: str | None,
) -> LayeredRasterSpec:
    src_w = analysis.source_size.width
    src_h = analysis.source_size.height
    scale = 1.0
    width, height = src_w, src_h
    if max(src_w, src_h) > _SCAFFOLD_MAX_CANVAS:
        scale = _SCAFFOLD_MAX_CANVAS / max(src_w, src_h)
        width = max(int(src_w * scale), 1)
        height = max(int(src_h * scale), 1)
    bbox = analysis.bbox
    rect = LayerRect(
        x=max(int(bbox.x * scale), 0),
        y=max(int(bbox.y * scale), 0),
        width=min(max(int(bbox.width * scale), 1), width),
        height=min(max(int(bbox.height * scale), 1), height),
    )
    bg_key = analysis.palette_keys.dominant or "primary"
    return LayeredRasterSpec(
        type="layered_raster",
        id=asset_id,
        name=asset_id.replace("_", " ").title(),
        dimensions=PixelDimensions(width=width, height=height),
        style=style_name or "default",
        layers=[
            RasterLayer(name="background", role="background", fill=bg_key),
            RasterLayer(
                name="reference",
                role="image",
                image=image_ref,
                rect=rect,
            ),
        ],
        art_direction=ArtDirection(
            subject=asset_id.replace("_", " "),
            references=[
                ReferenceImage(path=image_ref, purpose="silhouette"),
                ReferenceImage(path=image_ref, purpose="color"),
            ],
        ),
        art_analysis=_analysis_to_art(analysis, ratio),
    )
