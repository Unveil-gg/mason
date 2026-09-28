"""Decomposition schema, persist, and component ingest."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.decompose import Decomposition
from mason.core.jobs import AssetJob
from mason.pipelines.assemble import compile_assembly

runner = CliRunner()


def _graph() -> dict:
    return {
        "mode": "assets",
        "components": [
            {
                "id": "deck",
                "technique": "box",
                "asset": "axle_cart__deck",
                "dimensions": {
                    "width": 0.6, "depth": 0.36, "height": 0.04,
                },
            },
            {
                "id": "wheel",
                "technique": "lathe",
                "asset": "axle_cart__wheel",
                "instance_of": "wheel",
                "dimensions": {
                    "width": 0.16, "depth": 0.16, "height": 0.04,
                },
            },
        ],
        "joints": [
            {"child": "deck"},
            {
                "child": "wheel",
                "parent": "deck",
                "parent_socket": "wheel_l",
                "location": [-0.22, 0.0, 0.0],
                "copies": [
                    {
                        "parent_socket": "wheel_r",
                        "location": [0.22, 0.0, 0.0],
                        "mirror": "x",
                    },
                ],
            },
        ],
    }


def test_decomposition_rejects_unknown_instance() -> None:
    try:
        Decomposition.model_validate({
            "mode": "parts",
            "components": [{"id": "wheel", "instance_of": "missing"}],
        })
    except Exception as exc:
        assert "instance_of" in str(exc)
        return
    raise AssertionError("expected invalid instance_of")


def test_assets_mode_requires_asset() -> None:
    try:
        Decomposition.model_validate({
            "mode": "assets",
            "components": [{"id": "deck"}],
        })
    except Exception as exc:
        assert "asset" in str(exc)
        return
    raise AssertionError("expected missing asset")


def test_example_axle_cart_parses() -> None:
    from mason.core.assets import load_asset_spec
    root = Path(__file__).resolve().parents[1]
    spec = load_asset_spec(
        root / "tests" / "fixtures" / "axle_cart.yaml",
    )
    assert spec.decomposition.mode == "assets"
    assert spec.geometry.parts[0].shape == "instance"
    assert spec.depends_on == ["axle_cart__deck", "axle_cart__wheel"]


def test_compile_reuses_wheel_asset() -> None:
    graph = Decomposition.model_validate(_graph())
    parts = compile_assembly(graph)
    names = [part.name for part in parts]
    assert names == ["deck", "wheel_l", "wheel_r"]
    wheels = [p for p in parts if p.name.startswith("wheel")]
    assert all(p.source.asset == "axle_cart__wheel" for p in wheels)
    assert wheels[1].mirror == "x"
    assert wheels[0].parent == "deck"


def _seed_parent(project: Path) -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "axle_cart",
        "name": "Axle Cart",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_meta("examples/assets/axle_cart.yaml")
    return job


def test_decompose_cli_persists(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    job = _seed_parent(project)
    graph_path = tmp_path / "graph.yaml"
    graph_path.write_text(
        yaml.safe_dump(_graph()), encoding="utf-8",
    )
    monkeypatch.chdir(project)
    result = runner.invoke(
        app,
        ["decompose", "axle_cart", str(graph_path), "--json"],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["mode"] == "assets"
    assert job.decomposition_yaml.is_file()
    loaded = job.load_spec()
    assert loaded.decomposition is not None
    assert loaded.depends_on == [
        "axle_cart__deck", "axle_cart__wheel",
    ]


def test_ingest_component_scopes_parent(
    project: Path, monkeypatch, tmp_path: Path,
) -> None:
    from PIL import Image

    job = _seed_parent(project)
    whole = tmp_path / "whole.png"
    img = Image.new("L", (40, 80), 255)
    for x in range(10, 30):
        for y in range(10, 70):
            img.putpixel((x, y), 0)
    img.save(whole)
    isolate = tmp_path / "wheel.png"
    img.save(isolate)
    monkeypatch.chdir(project)
    runner.invoke(
        app,
        ["ingest", str(whole), "--asset", "axle_cart",
         "--view", "side", "--json"],
    )
    result = runner.invoke(
        app,
        [
            "ingest", str(isolate), "--asset", "axle_cart",
            "--component", "wheel", "--view", "three_quarter",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    loaded = job.load_spec()
    views = loaded.reference_analysis.views
    whole_views = [row for row in views if row.component is None]
    isol = [row for row in views if row.component == "wheel"]
    assert len(whole_views) == 1
    assert isol[0].purpose == "component"
    assert (
        job.previews / "reference_silhouette_wheel_three_quarter.png"
    ).is_file()
    assert (job.previews / "reference_silhouette_side.png").is_file()
