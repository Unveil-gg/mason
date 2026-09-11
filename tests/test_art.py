"""ArtDirection, ConstructionPlan, and VisualEvaluation."""

from __future__ import annotations

from pathlib import Path

from mason.core.art import (
    ArtDirection,
    ConstructionPlan,
    VisualEvaluation,
)
from mason.core.form_plan import GeometricPlan
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
            "techniques": [
                {"kind": "box", "purpose": "seat", "applies_to": "primary"},
            ],
            "primary_forms": [
                {"type": "beveled_box", "purpose": "seat"},
            ],
            "notes": ["taper legs"],
        },
        "geometric_plan": {
            "recognition": "silhouette",
            "stage": "blockout",
            "landmarks": [
                {"id": "seat_front", "role": "seat corner", "part": "seat"},
            ],
        },
        "depends_on": ["plank_texture"],
        "decomposition": {
            "mode": "parts",
            "components": [{"id": "seat", "technique": "box"}],
        },
    })
    assert spec.art_direction.subject == "wooden chair"
    assert spec.construction_plan.notes == ["taper legs"]
    assert spec.construction_plan.techniques[0].kind == "box"
    assert spec.geometric_plan.stage == "blockout"
    assert spec.geometric_plan.landmarks[0].id == "seat_front"
    assert spec.depends_on == ["plank_texture"]
    assert spec.decomposition.mode == "parts"
    assert spec.decomposition.components[0].id == "seat"
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
    assert spec.geometric_plan is None
    assert spec.decomposition is None
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
    assert evaluation.scores.overall_visual_quality is None
    assert evaluation.scores.continuity is None
    assert evaluation.scores.form_conviction is None


def test_visual_evaluation_beauty_scores() -> None:
    evaluation = VisualEvaluation.model_validate({
        "passed": True,
        "ship": True,
        "scores": {
            "overall_visual_quality": 7,
            "detail_density": 6,
            "proportions": 7,
            "secondary_forms": 6,
            "tertiary_detail": 5,
            "materials": 6,
            "visual_hierarchy": 7,
            "style_consistency": 8,
            "game_readability": 7,
        },
    })
    assert evaluation.scores.overall_visual_quality == 7
    assert evaluation.scores.silhouette is None
    assert evaluation.scores.form_conviction is None
    assert evaluation.mode == "beauty"
    assert evaluation.discrepancies == []


def test_silhouette_eval_ranked_discrepancies() -> None:
    evaluation = VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "mode": "silhouette",
        "stage": "silhouette",
        "represents_object": True,
        "represents_style": False,
        "scores": {
            "proportions": 5,
            "secondary_forms": 4,
            "tertiary_detail": 3,
            "materials": 5,
            "visual_hierarchy": 5,
            "style_consistency": 4,
            "game_readability": 6,
            "silhouette": 5,
        },
        "discrepancies": [{
            "rank": "critical",
            "category": "silhouette",
            "description": "Neck lacks the backward arch",
            "geometric_intent": "Increase rear neck curvature",
            "suggested_action": "Move neck_apex +Y",
            "landmark": "neck_apex",
        }],
        "actions_taken": ["moved neck_apex toward +Y"],
    })
    assert evaluation.mode == "silhouette"
    assert evaluation.discrepancies[0].rank == "critical"
    assert evaluation.represents_style is False
    assert evaluation.view_scores == []
    assert evaluation.compare is None


def test_geometric_plan_defaults() -> None:
    plan = GeometricPlan()
    assert plan.stage == "blockout"
    assert plan.landmarks == []
    assert plan.critical_views == []


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
