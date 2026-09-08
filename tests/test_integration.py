"""Optional live-tool integration tests. Skip if tools are missing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.tools.registry import detect_all

runner = CliRunner()


def _tools():
    return detect_all()


@pytest.mark.integration
def test_blender_crate_build(project: Path, crate_yaml: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["blender"].available:
        pytest.skip("Blender not installed")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(crate_yaml), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    glb = project / ".mason" / "jobs" / "simple_crate" / "output" / "asset.glb"
    preview = (
        project / ".mason" / "jobs" / "simple_crate" / "previews" / "front.png"
    )
    assert glb.is_file() and glb.stat().st_size > 0
    assert preview.is_file()
    data = __import__("json").loads(result.stdout)
    assert data["validation"]["passed"] is True
    job = project / ".mason" / "jobs" / "simple_crate" / "previews"
    assert (job / "silhouette_front.png").is_file()
    assert (job / "clay_three_quarter.png").is_file()
    assert (job / "detail.png").is_file()


@pytest.mark.integration
def test_blender_hydrant_previews(
    project: Path, monkeypatch,
) -> None:
    tools = _tools()
    if not tools["blender"].available:
        pytest.skip("Blender not installed")
    spec = {
        "type": "static_prop",
        "id": "fire_hydrant",
        "name": "Fire Hydrant",
        "dimensions": {"width": 0.37, "depth": 0.32, "height": 0.62},
        "style": "default",
        "geometry": {"recipe": "hydrant"},
        "materials": {"primary": "hydrant_red"},
        "export": {"format": "glb", "save_blend": True},
    }
    path = project / "hydrant.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    previews = project / ".mason" / "jobs" / "fire_hydrant" / "previews"
    for name in (
        "front.png",
        "three_quarter.png",
        "silhouette_front.png",
        "silhouette_three_quarter.png",
        "clay_three_quarter.png",
        "detail.png",
    ):
        assert (previews / name).is_file()


@pytest.mark.integration
def test_imagemagick_resize(project: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["imagemagick"].available:
        pytest.skip("ImageMagick not installed")
    src = project / "swatch.png"
    Image.new("RGB", (128, 64), (200, 80, 40)).save(src)
    spec = {
        "type": "image_process",
        "id": "swatch_32",
        "name": "Swatch",
        "source": {"path": "swatch.png"},
        "operations": [{
            "op": "resize",
            "width": 32,
            "height": 32,
            "fit": "stretch",
        }],
    }
    spec_path = project / "swatch.yaml"
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(spec_path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    out = project / ".mason" / "jobs" / "swatch_32" / "output" / "asset.png"
    assert out.is_file()
    with Image.open(out) as img:
        assert img.size == (32, 32)
    preview = project / ".mason" / "jobs" / "swatch_32" / "previews" / "full.png"
    assert preview.is_file()


@pytest.mark.integration
def test_krita_panel(project: Path, monkeypatch) -> None:
    tools = _tools()
    info = tools["krita"]
    if not info.available or not (info.extras or {}).get("kritarunner"):
        pytest.skip("Krita/kritarunner not installed")
    spec = {
        "type": "layered_raster",
        "id": "panel",
        "name": "Panel",
        "dimensions": {"width": 64, "height": 64},
        "layers": [
            {"name": "background", "fill": "cream"},
            {"name": "accent", "fill": "accent",
             "rect": {"x": 0, "y": 0, "width": 64, "height": 8}},
        ],
    }
    path = project / "panel.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    preview = project / ".mason" / "jobs" / "panel" / "previews" / "full.png"
    assert preview.is_file()


@pytest.mark.integration
def test_krita_build_json_slims_layer_names_by_default(
    project: Path, monkeypatch,
) -> None:
    """A dapple/speckle stamp expands into dozens of grain layers;
    --json should hide that array unless --full is passed."""
    tools = _tools()
    info = tools["krita"]
    if not info.available or not (info.extras or {}).get("kritarunner"):
        pytest.skip("Krita/kritarunner not installed")
    spec = {
        "type": "layered_raster",
        "id": "panel_grain",
        "name": "Panel Grain",
        "dimensions": {"width": 64, "height": 64},
        "layers": [
            {"name": "background", "fill": "cream"},
            {"name": "grain", "role": "overlay", "fill": "accent",
             "stamp": "dapple",
             "rect": {"x": 0, "y": 0, "width": 64, "height": 64}},
        ],
    }
    path = project / "panel_grain.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)

    slim = runner.invoke(app, ["build", str(path), "--json"])
    assert slim.exit_code == 0, slim.stdout + slim.stderr
    slim_data = json.loads(slim.stdout)
    assert "layer_names" not in slim_data["validation"]
    assert slim_data["validation"]["passed"] is True

    full = runner.invoke(
        app, ["rebuild", "panel_grain", "--json", "--full"],
    )
    assert full.exit_code == 0, full.stdout + full.stderr
    full_data = json.loads(full.stdout)
    assert "layer_names" in full_data["validation"]


@pytest.mark.integration
def test_aseprite_sprite_sheet(project: Path, monkeypatch) -> None:
    tools = _tools()
    if not tools["aseprite"].available:
        pytest.skip("Aseprite not installed")
    spec = {
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "canvas": {"width": 8, "height": 8},
        "animations": [
            {
                "name": "idle",
                "loop": True,
                "frames": [
                    {
                        "duration_ms": 200,
                        "layers": [{
                            "name": "body",
                            "pixels": [
                                "IIII....",
                                "I..I....",
                                "IIII....",
                                "........",
                                "........",
                                "........",
                                "........",
                                "........",
                            ],
                            "keys": {"I": "ink"},
                        }],
                    },
                    {
                        "duration_ms": 200,
                        "layers": [{
                            "name": "body",
                            "pixels": [
                                ".IIII...",
                                ".I..I...",
                                ".IIII...",
                                "........",
                                "........",
                                "........",
                                "........",
                                "........",
                            ],
                            "keys": {"I": "ink"},
                        }],
                    },
                ],
            },
        ],
    }
    path = project / "hero.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["build", str(path), "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    out = project / ".mason" / "jobs" / "hero" / "output"
    png = out / "asset.png"
    frames = out / "frames.json"
    preview = project / ".mason" / "jobs" / "hero" / "previews" / "full.png"
    assert png.is_file() and png.stat().st_size > 0
    assert frames.is_file()
    assert preview.is_file()
    with Image.open(png) as img:
        assert img.size == (16, 8)
    data = __import__("json").loads(frames.read_text(encoding="utf-8"))
    assert data["animations"][0]["name"] == "idle"
    assert data["animations"][0]["frames"][1]["x"] == 8
