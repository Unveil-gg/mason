"""Enclosed-hole and island counts on silhouette previews."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from mason.pipelines.continuity import enclosed_holes, preview_continuity
from mason.tools.blender.validation import validate_static_prop
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob


def _save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).save(path)


def test_enclosed_hole_detected(tmp_path: Path) -> None:
    mask = np.zeros((40, 40), dtype=bool)
    mask[8:32, 8:32] = True
    mask[16:24, 16:24] = False
    src = tmp_path / "sil.png"
    _save_mask(src, mask)
    metrics = preview_continuity(src)
    assert metrics["holes"] == 1
    assert metrics["islands"] == 1
    assert metrics["hole_pixels"] == 64


def test_donut_is_enclosed() -> None:
    mask = np.zeros((20, 20), dtype=bool)
    mask[4:16, 4:16] = True
    mask[8:12, 8:12] = False
    holes = enclosed_holes(mask)
    assert int(holes.sum()) == 16


def test_body_validation_fails_on_hole(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "joined",
        "name": "Joined",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "a",
                "size": [0.2, 0.2, 0.2],
                "location": [0, 0, 0.1],
            }],
            "bodies": [{
                "name": "body",
                "members": ["a"],
                "method": "remesh",
            }],
        },
    })
    job = AssetJob(project, "joined")
    job.prepare()
    mask = np.zeros((40, 40), dtype=bool)
    mask[8:32, 8:32] = True
    mask[16:24, 16:24] = False
    _save_mask(job.previews / "silhouette_side.png", mask)
    report = validate_static_prop(job, spec, exit_code=1)
    names = {row.name: row.passed for row in report.checks}
    assert names["solid_silhouette_side"] is False
