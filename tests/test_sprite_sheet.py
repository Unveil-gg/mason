"""sprite_sheet layout and frames.json contract."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.generators.aseprite.script_builder import sheet_layout
from mason.pipelines.sprite_sheet import write_frames_json


def _spec():
    return parse_asset_spec({
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "canvas": {"width": 16, "height": 16},
        "animations": [
            {
                "name": "idle",
                "loop": True,
                "frames": [
                    {"duration_ms": 400, "layers": [{"name": "a", "fill": "ink"}]},
                    {"duration_ms": 400, "layers": [{"name": "a", "fill": "ink"}]},
                ],
            },
            {
                "name": "walk",
                "loop": True,
                "frames": [
                    {"duration_ms": 100, "layers": [{"name": "a", "fill": "ink"}]},
                    {"duration_ms": 100, "layers": [{"name": "a", "fill": "ink"}]},
                    {"duration_ms": 100, "layers": [{"name": "a", "fill": "ink"}]},
                    {"duration_ms": 100, "layers": [{"name": "a", "fill": "ink"}]},
                ],
            },
        ],
    })


def test_sheet_layout_is_row_per_animation() -> None:
    layout = sheet_layout(_spec())
    assert layout["columns"] == 4
    assert layout["rows"] == 2
    assert layout["sheet"] == {"width": 64, "height": 32}
    idle = layout["animations"][0]
    assert idle["name"] == "idle"
    assert idle["frames"][1] == {
        "index": 1, "x": 16, "y": 0, "w": 16, "h": 16, "duration_ms": 400,
    }
    walk = layout["animations"][1]
    assert walk["frames"][3]["x"] == 48
    assert walk["frames"][3]["y"] == 16


def test_write_frames_json(project: Path) -> None:
    spec = _spec()
    job = AssetJob(project, spec.id)
    job.prepare()
    path = write_frames_json(job, spec)
    assert path.name == "frames.json"
    data = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert [a["name"] for a in data["animations"]] == ["idle", "walk"]
    assert data["frame_size"] == {"width": 16, "height": 16}
