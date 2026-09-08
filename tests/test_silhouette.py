"""Objective silhouette metrics and reference views."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.ref_analysis import ReferenceAnalysis
from mason.pipelines.checkpoint import restart_parts
from mason.pipelines.silhouette import (
    compare_masks,
    extract_silhouette,
    iou_regressed,
    silhouette_iou,
    subject_mask,
)
import numpy as np


def _rect(path: Path, box: tuple[int, int, int, int], size=(40, 80)) -> None:
    img = Image.new("L", size, 255)
    x0, y0, x1, y1 = box
    for x in range(x0, x1):
        for y in range(y0, y1):
            img.putpixel((x, y), 0)
    img.save(path)


def test_normalized_iou_self(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    _rect(src, (10, 10, 30, 70))
    sil, ratio = extract_silhouette(src)
    dest = tmp_path / "sil.png"
    sil.save(dest)
    assert ratio == 3.0
    assert silhouette_iou(dest, dest) == 1.0


def test_compare_masks_detects_shift(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _rect(a, (10, 10, 30, 70))
    _rect(b, (10, 10, 30, 40), size=(40, 80))
    metrics = compare_masks(a, b)
    assert metrics["iou"] < 0.8
    assert metrics["contour_distance"] > 0
    assert metrics["widths"]


def test_mask_extrema_use_full_mask(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    _rect(src, (10, 10, 30, 70))
    mask = subject_mask(np.array(Image.open(src).convert("L")))
    from mason.pipelines.silhouette import mask_extrema
    points = {row.id: row.uv for row in mask_extrema(mask)}
    assert points["left"][0] <= 0.05
    assert points["right"][0] >= 0.95


def test_light_on_light_uses_edges(tmp_path: Path) -> None:
    src = tmp_path / "soft.png"
    img = Image.new("L", (80, 80), 250)
    for x in range(20, 60):
        for y in range(15, 65):
            img.putpixel((x, y), 210)
    img.save(src)
    mask = subject_mask(np.array(img))
    assert 0.05 < float((mask > 0).mean()) < 0.8


def test_iou_regressed_threshold() -> None:
    best = {"views": {"silhouette_side": {"iou": 0.71}}}
    worse = {"views": {"silhouette_side": {"iou": 0.64}}}
    assert iou_regressed(worse, best, ["silhouette_side"]) == [
        "silhouette_side",
    ]


def test_reference_analysis_roundtrip() -> None:
    doc = ReferenceAnalysis.model_validate({
        "views": [{
            "view": "side",
            "path": "ref.png",
            "height_width_ratio": 2.0,
            "profile": [[0.1, 0.0], [0.2, 1.0]],
            "landmarks": [{"id": "nose", "uv": [0.1, 0.4]}],
        }],
        "defining_silhouette": "side S-curve",
    })
    assert doc.views[0].landmarks[0].id == "nose"


def test_restart_keeps_best_parts(project: Path) -> None:
    best = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"parts": [
            {
                "name": "base", "shape": "cylinder",
                "size": [0.4, 0.4, 0.2], "location": [0, 0, 0.1],
            },
            {
                "name": "head", "shape": "sphere",
                "size": [0.3, 0.3, 0.3], "location": [0, 0, 0.5],
            },
        ]},
    })
    live = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"parts": [
            {
                "name": "base", "shape": "box",
                "size": [0.4, 0.4, 0.2], "location": [0, 0, 0.1],
            },
            {
                "name": "head", "shape": "box",
                "size": [0.3, 0.3, 0.3], "location": [0, 0, 0.5],
            },
            {
                "name": "eye", "shape": "sphere",
                "size": [0.05, 0.05, 0.05], "location": [0, 0, 0.6],
            },
        ]},
    })
    job = AssetJob(project, "box")
    job.prepare()
    job.write_spec(live)
    job.write_meta(None, iteration=2, current_best=1, set_best=True)
    dest = job.iterations / "001"
    dest.mkdir(parents=True)
    from mason.core.assets import dump_asset_spec
    dump_asset_spec(best, dest / "asset.yaml")
    payload = restart_parts(job, keep=["base"], rebuild=["head"])
    spec = job.load_spec()
    names = [p.name for p in spec.geometry.parts]
    assert names[0] == "base"
    assert spec.geometry.parts[0].shape == "cylinder"
    assert "head" not in names
    assert "eye" in names
    assert payload["from_iteration"] == 1
