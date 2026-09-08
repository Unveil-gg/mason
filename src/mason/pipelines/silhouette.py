"""Normalize and compare silhouettes in image space."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from mason.core.jobs import AssetJob
from mason.core.ref_analysis import ImageLandmark, WidthSample

CANVAS = 128
IOU_DROP = 0.05
WIDTH_TS = (0.2, 0.4, 0.6, 0.8)
_VIEW_FILES = {
    "silhouette_side": "silhouette_side.png",
    "side": "silhouette_side.png",
    "silhouette_front": "silhouette_front.png",
    "front": "silhouette_front.png",
    "silhouette_three_quarter": "silhouette_three_quarter.png",
    "three_quarter": "silhouette_three_quarter.png",
}


def extract_silhouette(src: Path) -> tuple[Image.Image, float]:
    """Threshold, trim, return (L image, height/width)."""
    gray = np.array(Image.open(src).convert("L"))
    mask = subject_mask(gray)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        out = Image.new("L", (1, 1), 255)
        return out, 1.0
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    crop = mask[y0:y1 + 1, x0:x1 + 1]
    out = Image.fromarray(255 - crop)
    width, height = out.size
    ratio = (height / width) if width else 1.0
    return out, ratio


def subject_mask(gray: np.ndarray) -> np.ndarray:
    """255 on the subject. Dark-on-light, or edges if low contrast."""
    work = gray
    if float(work.mean()) < 128:
        work = 255 - work
    dark = _threshold_mask(work)
    frac = _mask_frac(dark)
    edge = _edge_mask(gray) if float(gray.std()) < 22 or frac < 0.02 else None
    if edge is not None:
        edge_frac = _mask_frac(edge)
        if 0.02 <= edge_frac <= 0.88 and (frac < 0.02 or edge_frac > frac):
            return edge
    if 0.02 <= frac <= 0.88:
        return dark
    return dark


def silhouette_iou(current: Path, reference: Path) -> float:
    """IoU after shared-canvas normalize. Dark pixels are subject."""
    a = _normalized_mask(current)
    b = _normalized_mask(reference)
    if a is None or b is None:
        return 0.0
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return inter / union if union else 0.0


def compare_masks(current: Path, reference: Path) -> dict:
    """IoU, contour distance, bbox ratio, COM, and width samples."""
    a = _normalized_mask(current)
    b = _normalized_mask(reference)
    if a is None or b is None:
        return {
            "iou": 0.0,
            "contour_distance": None,
            "bbox_ratio": None,
            "com": None,
            "widths": [],
        }
    iou = _iou(a, b)
    return {
        "iou": round(iou, 4),
        "contour_distance": round(_chamfer(a, b), 4),
        "bbox_ratio": round(_bbox_ratio(a), 4),
        "ref_bbox_ratio": round(_bbox_ratio(b), 4),
        "com": _com(a),
        "ref_com": _com(b),
        "widths": _widths(a),
        "ref_widths": _widths(b),
    }


def extrema_landmarks(contour: list[tuple[float, float]]) -> list[ImageLandmark]:
    """Generic bbox extrema from a 0..1 contour (y down)."""
    if not contour:
        return []
    top = min(contour, key=lambda p: p[1])
    bottom = max(contour, key=lambda p: p[1])
    left = min(contour, key=lambda p: p[0])
    right = max(contour, key=lambda p: p[0])
    return [
        ImageLandmark(id="top", uv=_uv(top), role="highest"),
        ImageLandmark(id="bottom", uv=_uv(bottom), role="lowest"),
        ImageLandmark(id="left", uv=_uv(left), role="leftmost"),
        ImageLandmark(id="right", uv=_uv(right), role="rightmost"),
    ]


def mask_extrema(mask: np.ndarray) -> list[ImageLandmark]:
    """Extrema from the full subject mask, not a simplified contour."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return []
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    bw = max(x1 - x0, 1)
    bh = max(y1 - y0, 1)

    def _pt(idx: int) -> tuple[float, float]:
        return (
            round((int(xs[idx]) - x0) / bw, 4),
            round((int(ys[idx]) - y0) / bh, 4),
        )

    marks = [
        ImageLandmark(id="top", uv=_pt(int(np.argmin(ys))), role="highest"),
        ImageLandmark(id="bottom", uv=_pt(int(np.argmax(ys))), role="lowest"),
        ImageLandmark(id="left", uv=_pt(int(np.argmin(xs))), role="leftmost"),
        ImageLandmark(id="right", uv=_pt(int(np.argmax(xs))), role="rightmost"),
    ]
    upper = ys <= y0 + int(0.45 * bh)
    if int(upper.sum()) > 0:
        uxs, uys = xs[upper], ys[upper]

        def _upt(idx: int) -> tuple[float, float]:
            return (
                round((int(uxs[idx]) - x0) / bw, 4),
                round((int(uys[idx]) - y0) / bh, 4),
            )

        marks.append(ImageLandmark(
            id="forward", uv=_upt(int(np.argmin(uxs))),
            role="leftmost in upper half",
        ))
        marks.append(ImageLandmark(
            id="rear_high", uv=_upt(int(np.argmax(uxs))),
            role="rightmost in upper half",
        ))
    return marks


def width_samples(mask: np.ndarray) -> list[WidthSample]:
    """Width at standard heights from a subject mask."""
    return [
        WidthSample(t=row["t"], width=row["width"])
        for row in _widths(mask > 0)
    ]


def write_job_metrics(job: AssetJob) -> dict:
    """Compare live previews to ingested reference silhouettes."""
    payload = measure_job(job)
    dest = job.dir / "silhouette_metrics.json"
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def measure_job(job: AssetJob, preview_dir: Path | None = None) -> dict:
    """Per-view metrics for one preview folder."""
    previews = preview_dir or job.previews
    refs = _reference_map(job)
    views: dict[str, dict] = {}
    for view, preview_name in _VIEW_FILES.items():
        preview = previews / preview_name
        ref = refs.get(view)
        if ref is None and view in ("silhouette_side", "side"):
            ref = refs.get("default")
        if not preview.is_file() or ref is None or not ref.is_file():
            continue
        views[view] = compare_masks(preview, ref)
    ious = [row["iou"] for row in views.values() if row.get("iou") is not None]
    return {
        "views": views,
        "iou": min(ious) if ious else None,
    }


def load_metrics(job: AssetJob, iteration: int) -> dict | None:
    """Read stored metrics for a snapshot, or measure its previews."""
    path = job.iterations / f"{iteration:03d}" / "silhouette_metrics.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    snap = job.iterations / f"{iteration:03d}" / "previews"
    if snap.is_dir():
        return measure_job(job, snap)
    return None


def iou_regressed(
    candidate: dict | None,
    best: dict | None,
    critical: list[str],
    *,
    drop: float = IOU_DROP,
) -> list[str]:
    """Critical views whose IoU fell by `drop` or more."""
    if not candidate or not best:
        return []
    dropped: list[str] = []
    for view in critical:
        c_iou = _view_iou(candidate, view)
        b_iou = _view_iou(best, view)
        if c_iou is None or b_iou is None:
            continue
        if c_iou <= b_iou - drop:
            dropped.append(view)
    return dropped


def _view_iou(payload: dict, view: str) -> float | None:
    views = payload.get("views") or {}
    row = views.get(view)
    if row and row.get("iou") is not None:
        return float(row["iou"])
    if payload.get("iou") is not None and view in ("silhouette_side", "side"):
        return float(payload["iou"])
    return None


def _reference_map(job: AssetJob) -> dict[str, Path]:
    found: dict[str, Path] = {}
    default = job.previews / "reference_silhouette.png"
    if default.is_file():
        found["default"] = default
    for view in ("side", "front", "three_quarter"):
        path = job.previews / f"reference_silhouette_{view}.png"
        if path.is_file():
            found[view] = path
            found[f"silhouette_{view}"] = path
            if view == "three_quarter":
                found["silhouette_three_quarter"] = path
    return found


def _threshold_mask(work: np.ndarray) -> np.ndarray:
    return np.where(work < 200, 255, 0).astype(np.uint8)


def _edge_mask(gray: np.ndarray) -> np.ndarray | None:
    try:
        import cv2
    except ImportError:
        return None
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 12, 48)
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.morphologyEx(closed, cv2.MORPH_CLOSE, kernel, iterations=3)
    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return None
    fill = np.zeros_like(gray)
    largest = max(contours, key=cv2.contourArea)
    cv2.drawContours(fill, [largest], -1, 255, thickness=-1)
    return fill


def _mask_frac(mask: np.ndarray) -> float:
    return float((mask > 0).mean()) if mask.size else 0.0


def _normalized_mask(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    with Image.open(path) as img:
        gray = np.array(img.convert("L"))
    subject = gray < 128
    if not subject.any():
        return np.zeros((CANVAS, CANVAS), dtype=bool)
    ys, xs = np.nonzero(subject)
    crop = subject[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    pil = Image.fromarray(crop.astype(np.uint8) * 255)
    fitted = ImageOps.contain(pil, (CANVAS, CANVAS), Image.Resampling.NEAREST)
    canvas = Image.new("L", (CANVAS, CANVAS), 0)
    ox = (CANVAS - fitted.width) // 2
    oy = (CANVAS - fitted.height) // 2
    canvas.paste(fitted, (ox, oy))
    return np.array(canvas) > 0


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return inter / union if union else 0.0


def _chamfer(a: np.ndarray, b: np.ndarray) -> float:
    """Mean nearest-edge distance on the canvas, 0..1."""
    pa = np.argwhere(a)
    pb = np.argwhere(b)
    if len(pa) == 0 or len(pb) == 0:
        return 1.0
    if len(pa) > 256:
        pa = pa[:: max(1, len(pa) // 256)]
    if len(pb) > 256:
        pb = pb[:: max(1, len(pb) // 256)]
    d_ab = _mean_min_dist(pa, pb)
    d_ba = _mean_min_dist(pb, pa)
    return float((d_ab + d_ba) * 0.5 / CANVAS)


def _mean_min_dist(src: np.ndarray, dest: np.ndarray) -> float:
    delta = src[:, None, :] - dest[None, :, :]
    dist = np.sqrt((delta ** 2).sum(axis=2))
    return float(dist.min(axis=1).mean())


def _bbox_ratio(mask: np.ndarray) -> float:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return 1.0
    w = int(xs.max() - xs.min()) + 1
    h = int(ys.max() - ys.min()) + 1
    return h / w if w else 1.0


def _com(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return (0.5, 0.5)
    return (round(float(xs.mean()) / CANVAS, 4), round(float(ys.mean()) / CANVAS, 4))


def _widths(mask: np.ndarray) -> list[dict]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return [{"t": t, "width": 0.0} for t in WIDTH_TS]
    y0, y1 = int(ys.min()), int(ys.max())
    span = max(y1 - y0, 1)
    bbox_w = max(int(xs.max() - xs.min()) + 1, 1)
    rows = []
    for t in WIDTH_TS:
        y = int(round(y1 - t * span))
        y = min(max(y, 0), mask.shape[0] - 1)
        width = int(mask[y].sum())
        rows.append({"t": t, "width": round(width / bbox_w, 4)})
    return rows


def _uv(point: tuple[float, float]) -> tuple[float, float]:
    return (round(float(point[0]), 4), round(float(point[1]), 4))
