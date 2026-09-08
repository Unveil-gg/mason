"""Non-destructive iteration: checkpoint, views, revert."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mason.cli import app
from mason.core.art import VisualEvaluation
from mason.core.assets import parse_asset_spec
from mason.core.form_plan import GeometricPlan, ViewWeight
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.core.styles import load_style
from mason.pipelines.checkpoint import (
    apply_checkpoint,
    critical_view_regressed,
    default_critical_views,
    restore_checkpoint,
)
from mason.pipelines.common import finish_result

runner = CliRunner()


def _scores(**extra) -> dict:
    base = {
        "proportions": 5,
        "secondary_forms": 5,
        "tertiary_detail": 5,
        "materials": 5,
        "visual_hierarchy": 5,
        "style_consistency": 5,
        "game_readability": 5,
    }
    base.update(extra)
    return base


def _eval(
    iteration: int,
    *,
    silhouette: int = 5,
    views: list[dict] | None = None,
    compare: dict | None = None,
) -> VisualEvaluation:
    payload = {
        "passed": False,
        "ship": False,
        "scores": _scores(silhouette=silhouette),
        "iteration": iteration,
        "view_scores": views or [],
    }
    if compare is not None:
        payload["compare"] = compare
    return VisualEvaluation.model_validate(payload)


def _seed(project: Path) -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "geometric_plan": {"recognition": "silhouette"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_style(load_style(project / "styles" / "default.yaml"))
    src = project / "assets" / "box.yaml"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("id: box\n", encoding="utf-8")
    job.write_meta("assets/box.yaml")
    report = ValidationReport(
        passed=True,
        checks=[ValidationCheck(name="ok", passed=True)],
        metrics={"triangles": 12},
    )
    finish_result(
        job,
        spec,
        tool="blender",
        version="0",
        outputs={},
        previews={},
        report=report,
        source_spec="assets/box.yaml",
    )
    return job


def test_default_critical_views_prefer_side() -> None:
    views = default_critical_views("silhouette")
    assert views[0].view == "silhouette_side"
    assert views[0].weight > views[-1].weight


def test_critical_view_drop() -> None:
    views = [ViewWeight(view="silhouette_side", weight=3)]
    best = _eval(1, views=[{"view": "silhouette_side", "score": 7}])
    worse = _eval(2, views=[{"view": "silhouette_side", "score": 4}])
    assert critical_view_regressed(worse, best, views) == [
        "silhouette_side",
    ]


def test_first_eval_becomes_best(project: Path) -> None:
    job = _seed(project)
    status = apply_checkpoint(job, _eval(1, silhouette=6))
    assert status["accepted"] is True
    assert job.load_meta().current_best == 1


def test_bump_keeps_current_best(project: Path) -> None:
    job = _seed(project)
    job.set_current_best(1)
    nxt = job.bump_iteration()
    assert nxt == 2
    assert job.load_meta().current_best == 1


def test_critical_drop_overrides_accept(project: Path) -> None:
    job = _seed(project)
    job.write_evaluation(_eval(
        1,
        views=[{"view": "silhouette_side", "score": 7}],
    ))
    job.set_current_best(1)
    candidate = _eval(
        2,
        views=[
            {"view": "silhouette_side", "score": 3},
            {"view": "front", "score": 8},
        ],
        compare={
            "verdict": "accept",
            "improves": ["front identity"],
            "worsens": ["side hook"],
            "reason": "front is clearer",
        },
    )
    status = apply_checkpoint(job, candidate)
    assert status["accepted"] is False
    assert status["verdict"] == "reject"
    assert "silhouette_side" in status["regressed_views"]
    assert "front is clearer" in status["reason"]
    assert job.load_meta().current_best == 1


def test_not_better_is_rejected(project: Path) -> None:
    job = _seed(project)
    job.write_evaluation(_eval(1, silhouette=6))
    job.set_current_best(1)
    status = apply_checkpoint(job, _eval(2, silhouette=6))
    assert status["accepted"] is False
    assert job.load_meta().current_best == 1


def test_revert_restores_spec(project: Path) -> None:
    job = _seed(project)
    job.set_current_best(1)
    mutated = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Mutated",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job.write_spec(mutated)
    payload = restore_checkpoint(job)
    assert payload["restored"] == 1
    assert job.load_spec().name == "Box"


def test_evaluate_cli_checkpoint(project: Path, monkeypatch) -> None:
    _seed(project)
    monkeypatch.chdir(project)
    path = project / "crit.json"
    path.write_text(json.dumps({
        "passed": False,
        "ship": False,
        "scores": _scores(silhouette=6),
    }), encoding="utf-8")
    result = runner.invoke(
        app, ["evaluate", "box", str(path), "--json"],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["checkpoint"]["accepted"] is True
    assert data["checkpoint"]["current_best"] == 1


def test_plan_critical_views_roundtrip() -> None:
    plan = GeometricPlan.model_validate({
        "recognition": "silhouette",
        "critical_views": [
            {"view": "silhouette_side", "weight": 3},
        ],
    })
    assert plan.critical_views[0].view == "silhouette_side"
