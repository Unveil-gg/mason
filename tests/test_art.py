"""ArtDirection, ConstructionPlan, and VisualEvaluation."""

from __future__ import annotations

from pathlib import Path

from mason.core.art import (
    ArtDirection,
    ConstructionPlan,
    VisualEvaluation,
)
from mason.core.assets import dump_asset_spec, parse_asset_spec
from mason.core.styles import load_style


def test_art_direction_defaults() -> None:
    brief = ArtDirection(subject="cafe chair")
    assert brief.usage.importance == "standard_prop"
    assert brief.detail_density == "medium"
    assert brief.forms.primary == []


def test_spec_with_art_loop_roundtrip(tmp_path: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "chair",
        "name": "Chair",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "art_direction": {
            "subject": "wooden chair",
            "silhouette": "readable dining chair",
            "forms": {"primary": ["seat", "back", "legs"]},
        },
        "construction_plan": {
            "primary_forms": [
                {"type": "beveled_box", "purpose": "seat"},
            ],
            "notes": ["taper legs"],
        },
        "depends_on": ["plank_texture"],
    })
    assert spec.art_direction.subject == "wooden chair"
    assert spec.construction_plan.notes == ["taper legs"]
    assert spec.depends_on == ["plank_texture"]
    dest = tmp_path / "chair.yaml"
    dump_asset_spec(spec, dest)
    loaded = parse_asset_spec(
        __import__("yaml").safe_load(dest.read_text(encoding="utf-8")),
    )
    assert loaded.art_direction.forms.primary == ["seat", "back", "legs"]


def test_old_spec_has_no_art_fields() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "crate",
        "name": "Crate",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    assert spec.art_direction is None
    assert spec.construction_plan is None
    assert spec.depends_on == []


def test_visual_evaluation_scores() -> None:
    evaluation = VisualEvaluation.model_validate({
        "passed": False,
        "ship": False,
        "scores": {
            "silhouette": 8,
            "proportions": 6,
            "secondary_forms": 4,
            "tertiary_detail": 3,
            "materials": 4,
            "visual_hierarchy": 7,
            "style_consistency": 8,
            "game_readability": 8,
        },
        "issues": [{
            "category": "secondary_forms",
            "severity": "high",
            "description": "Missing braces",
            "suggested_change": "Add two supports",
        }],
    })
    assert evaluation.scores.secondary_forms == 4
    assert evaluation.issues[0].severity == "high"


def test_construction_plan_empty() -> None:
    plan = ConstructionPlan()
    assert plan.primary_forms == []
    assert plan.materials == []


def test_style_quality_optional(tmp_path: Path) -> None:
    path = tmp_path / "styled.yaml"
    path.write_text(
        "name: styled\npalette:\n  primary: '#111111'\n"
        "quality:\n  hero:\n    detail_density: high\n",
        encoding="utf-8",
    )
    style = load_style(path)
    assert style.quality["hero"].detail_density == "high"
    assert "standard_prop" not in style.quality
