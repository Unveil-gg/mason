"""Seeded marks and part vary stay reproducible."""

from __future__ import annotations

from pathlib import Path

import pytest

from mason.core.assets import load_asset_spec, parse_asset_spec
from mason.core.entropy import PartVary, unit
from mason.core.parts import PropPart
from mason.core.styles import StyleProcess, load_style
from mason.core.vocab import vocab_payload
from mason.errors import MasonError
from mason.generators.blender.part_ops import expand_part_ops
from mason.generators.blender.script_builder import build_blender_script
from mason.generators.raster.marks import layer_dabs
from mason.pipelines.static_prop import (
    apply_style_defaults,
    resolved_parts,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_unit_is_stable_and_named() -> None:
    assert 0.0 <= unit(7, "sky", 0, 0) < 1.0
    assert unit(7, "sky", 0, 0) == unit(7, "sky", 0, 0)
    assert unit(7, "sky", 0, 0) != unit(7, "bank", 0, 0)
    assert unit(7, "sky", 0, 0) != unit(8, "sky", 0, 0)


def test_zero_vary_stays_exact() -> None:
    part = PropPart(
        name="block",
        size=(1.0, 0.5, 0.2),
        location=(0.0, 0.0, 0.1),
        vary=PartVary(
            scale=0,
            rotation=0,
            spacing=0,
            bevel=0,
            silhouette=0,
            breakup=0,
            material=0,
        ),
    )
    loud = StyleProcess(
        jitter=1, irregularity=1, breakup=1, variation=1,
    )
    got = expand_part_ops([part], seed=4, process=loud)
    assert len(got) == 1
    assert got[0].size == (1.0, 0.5, 0.2)
    assert got[0].location == (0.0, 0.0, 0.1)
    assert got[0].vary is None
    assert got[0].bevel_width is None


def test_name_key_ignores_neighbor_order() -> None:
    def box(name: str) -> PropPart:
        return PropPart(
            name=name,
            size=(0.2, 0.2, 0.2),
            location=(0.0, 0.0, 0.1),
            vary=PartVary(scale=0.2),
        )

    alone = expand_part_ops([box("alpha")], seed=5)
    paired = expand_part_ops([box("beta"), box("alpha")], seed=5)
    assert alone[0].size == paired[1].size


def test_stroke_without_hand_is_even(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "layered_raster",
        "id": "wash",
        "name": "Wash",
        "dimensions": {"width": 32, "height": 16},
        "layers": [{
            "name": "crest",
            "fill": "ink",
            "stroke": {
                "points": [[2, 8], [28, 8]],
                "radius": 3,
                "spacing": 0.5,
            },
        }],
    })
    style = load_style(project / "styles" / "default.yaml")
    dabs = layer_dabs(spec.layers[0], spec.seed, style)
    assert dabs is not None
    assert dabs[0] == (2.0, 8.0, 3.0, 0.85)
    assert dabs[-1][0] == 28.0
    assert all(dab[1] == 8.0 and dab[2] == 3.0 for dab in dabs)


def test_mark_and_stroke_conflict() -> None:
    with pytest.raises(MasonError) as exc:
        parse_asset_spec({
            "type": "layered_raster",
            "id": "both",
            "name": "Both",
            "dimensions": {"width": 8, "height": 8},
            "layers": [{
                "name": "ink",
                "fill": "ink",
                "stroke": {"points": [[0, 0], [4, 4]]},
                "mark": {"kind": "dab", "at": [1, 1], "radius": 2},
            }],
        })
    assert exc.value.code == "invalid_asset_spec"


def test_reed_bank_is_deterministic() -> None:
    spec = load_asset_spec(FIXTURES / "reed_bank.yaml")
    style = load_style(FIXTURES / "watercolor.yaml")
    assert style.process.overlap == 0.62
    first = [
        layer_dabs(layer, spec.seed, style) for layer in spec.layers
    ]
    second = [
        layer_dabs(layer, spec.seed, style) for layer in spec.layers
    ]
    assert first == second
    sky = first[0]
    bank = first[1]
    branch = first[2]
    reeds = first[3]
    shade = first[4]
    foam = first[5]
    assert sky and bank and branch and reeds and shade and foam
    assert len(reeds) == 18
    assert len(foam) == 1
    assert foam[0][0] == 40.0
    assert foam[0][1] == 58.0
    assert branch[0][2] > branch[-1][2]
    assert len(bank) > 20
    assert len(shade) > 4
    renamed = spec.layers[4].model_copy(update={"name": "gloom"})
    _ = layer_dabs(renamed, spec.seed, style)
    assert layer_dabs(spec.layers[0], spec.seed, style) == sky
    moved = layer_dabs(spec.layers[3], spec.seed + 1, style)
    assert moved != reeds


def test_shingle_row_varies_copies() -> None:
    spec = load_asset_spec(FIXTURES / "shingle_row.yaml")
    parts = resolved_parts(spec)
    again = resolved_parts(spec)
    assert [part.name for part in parts] == [
        "shingle", "shingle_2", "shingle_3",
        "shingle_4", "shingle_5", "shingle_6",
    ]
    assert [(p.location, p.size, p.bevel_width) for p in parts] == [
        (p.location, p.size, p.bevel_width) for p in again
    ]
    gaps = [
        parts[i + 1].location[0] - parts[i].location[0]
        for i in range(5)
    ]
    assert len({round(gap, 5) for gap in gaps}) > 1
    assert len({round(p.size[0], 5) for p in parts}) > 1
    assert all(part.bevel_width is not None for part in parts)
    assert len({round(p.bevel_width or 0, 5) for p in parts}) > 1
    assert len({round(p.color_bias, 5) for p in parts}) > 1
    other = spec.model_copy(update={"seed": spec.seed + 1})
    assert resolved_parts(other)[1].location != parts[1].location


def test_stone_pile_silhouette_and_flecks() -> None:
    spec = load_asset_spec(FIXTURES / "stone_pile.yaml")
    parts = resolved_parts(spec)
    assert resolved_parts(spec)[0].size == parts[0].size
    hosts = [part for part in parts if "_chip_" not in part.name]
    chips = [part for part in parts if "_chip_" in part.name]
    assert [part.name for part in hosts] == [
        "stone", "stone_2", "stone_3",
    ]
    assert len(chips) == 12
    assert all(part.size[2] == 0.12 for part in hosts)
    assert len({round(part.size[0], 5) for part in hosts}) > 1
    for host in hosts:
        owned = [
            chip for chip in chips
            if chip.name.startswith(host.name + "_chip_")
        ]
        assert len(owned) == 4
        assert all(chip.location[2] > host.location[2] for chip in owned)


def test_script_reads_part_bevel(project: Path) -> None:
    spec = load_asset_spec(FIXTURES / "shingle_row.yaml")
    style = load_style(project / "styles" / "default.yaml")
    parts = resolved_parts(spec, style)
    bw, bs, rough, metal = apply_style_defaults(spec, style)
    script = build_blender_script(
        spec, style, parts, project / ".mason" / "jobs" / "shingle",
        bevel_width=bw, bevel_segments=bs,
        roughness=rough, metallic=metal,
    )
    assert "def _scale_hex" in script
    assert 'part.get("bevel_width")' in script


def test_vocab_names_entropy() -> None:
    card = vocab_payload()
    assert "seed" in card["entropy"]
    assert "stroke_path" in card["entropy"]
    assert "family.variation" in card["entropy"]
