"""Assembly compile, dependency gate, and instance script wiring."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.parts import ImageSource, PropPart
from mason.core.styles import load_style
from mason.errors import MasonError
from mason.generators.blender.script_builder import build_blender_script
from mason.pipelines.assemble import (
    apply_assembly,
    assert_assembly_deps,
    compile_assembly,
    needs_assembly_deps,
    resolve_instance_paths,
)
from mason.pipelines.static_prop import apply_style_defaults, resolved_parts


def _parent_spec() -> dict:
    return {
        "type": "static_prop",
        "id": "axle_cart",
        "name": "Axle Cart",
        "dimensions": {"width": 0.6, "depth": 0.36, "height": 0.12},
        "geometry": {"recipe": "crate"},
        "decomposition": {
            "mode": "assets",
            "components": [
                {
                    "id": "deck",
                    "asset": "axle_cart__deck",
                    "dimensions": {
                        "width": 0.6, "depth": 0.36, "height": 0.04,
                    },
                },
                {
                    "id": "wheel",
                    "asset": "axle_cart__wheel",
                    "instance_of": "wheel",
                },
            ],
            "joints": [
                {"child": "deck"},
                {
                    "child": "wheel",
                    "parent": "deck",
                    "parent_socket": "wheel_l",
                    "location": [-0.22, 0.0, 0.0],
                    "copies": [{
                        "parent_socket": "wheel_r",
                        "location": [0.22, 0.0, 0.0],
                        "mirror": "x",
                    }],
                },
            ],
        },
    }


def _seed_component(project: Path, asset_id: str) -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": asset_id,
        "name": asset_id,
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job = AssetJob(project, asset_id)
    job.prepare()
    job.write_spec(spec)
    job.write_meta(None)
    job.set_current_best(1)
    snap = job.iterations / "001" / "output"
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "asset.glb").write_bytes(b"glb")
    (job.output / "asset.glb").write_bytes(b"glb")
    return job


def test_apply_assembly_writes_instances() -> None:
    spec = parse_asset_spec(_parent_spec())
    updated = apply_assembly(spec)
    names = [part.name for part in updated.geometry.parts]
    assert names == ["deck", "wheel_l", "wheel_r"]
    assert all(part.shape == "instance" for part in updated.geometry.parts)
    assert "axle_cart__wheel" in updated.depends_on


def test_assert_deps_requires_current_best(project: Path) -> None:
    spec = parse_asset_spec(_parent_spec())
    spec = apply_assembly(spec)
    try:
        assert_assembly_deps(spec, project)
    except MasonError as exc:
        assert exc.code in (
            "component_missing", "component_not_accepted",
        )
        return
    raise AssertionError("expected missing component")


def test_assert_deps_accepts_best(project: Path) -> None:
    spec = parse_asset_spec(_parent_spec())
    spec = apply_assembly(spec)
    _seed_component(project, "axle_cart__deck")
    _seed_component(project, "axle_cart__wheel")
    assert_assembly_deps(spec, project)
    job = AssetJob(project, "axle_cart")
    job.prepare()
    paths = resolve_instance_paths(job, spec.geometry.parts)
    assert "deck" in paths
    assert "wheel_l" in paths
    assert paths["wheel_l"] == paths["wheel_r"]


def test_instance_part_parses() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "rig",
        "name": "Rig",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "wheel",
                "shape": "instance",
                "source": {
                    "asset": "axle_cart__wheel",
                    "file": "output/asset.glb",
                },
                "location": [0, 0, 0],
            }],
        },
    })
    part = spec.geometry.parts[0]
    assert part.shape == "instance"
    assert part.source.asset == "axle_cart__wheel"
    assert part.size == (1.0, 1.0, 1.0)
    assert needs_assembly_deps(spec)


def test_blender_script_imports_instance(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "rig",
        "name": "Rig",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [{
                "name": "mass",
                "shape": "box",
                "size": [1, 1, 1],
                "location": [0, 0, 0.5],
            }],
        },
    })
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec)
    parts.append(PropPart(
        name="wheel",
        shape="instance",
        source=ImageSource(
            asset="axle_cart__wheel", file="output/asset.glb",
        ),
        location=(0.0, 0.0, 0.0),
    ))
    bw, bs, r, m = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "rig",
        bevel_width=bw, bevel_segments=bs, roughness=r, metallic=m,
        instance_paths={"wheel": "/tmp/wheel.glb"},
    )
    assert "def import_instance" in script
    assert "import_scene.gltf" in script
    assert "instance_paths" in script


def test_compile_parts_mode_is_empty() -> None:
    from mason.core.decompose import Decomposition
    graph = Decomposition.model_validate({
        "mode": "parts",
        "components": [{"id": "skull", "technique": "box"}],
        "joints": [{"child": "skull"}],
    })
    try:
        compile_assembly(graph)
    except MasonError as exc:
        assert exc.code == "joint_no_asset"
        return
    raise AssertionError("parts mode has no assets to compile")
