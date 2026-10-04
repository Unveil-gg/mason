"""Evaluate, history, inspect, and iteration snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mason.cli import app
from mason.core.art import VisualEvaluation
from mason.core.assets import parse_asset_spec
from mason.core.form_plan import GeometricPlan, Landmark
from mason.core.inspect import inspect_payload
from mason.pipelines.eval_next import next_packet
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.core.styles import load_style
from mason.pipelines.common import finish_result

runner = CliRunner()


def _seed_job(project: Path) -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "art_direction": {"subject": "crate", "silhouette": "box"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_style(load_style(project / "styles" / "default.yaml"))
    job.write_meta("assets/box.yaml")
    (job.previews / "front.png").write_bytes(b"png")
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
        previews={"front": job.rel(job.previews / "front.png")},
        report=report,
        source_spec="assets/box.yaml",
    )
    result = job.load_result()
    assert result is not None
    assert result.preview_roles["primary"] == "three_quarter"
    return job


def test_finish_result_snapshots_iteration(project: Path) -> None:
    job = _seed_job(project)
    meta = job.load_meta()
    assert meta is not None
    assert meta.iteration == 1
    snap = job.iterations / "001" / "previews" / "front.png"
    assert snap.is_file()
    assert job.art_direction_yaml.is_file()


def test_inspect_includes_art_and_iteration(project: Path) -> None:
    job = _seed_job(project)
    card = inspect_payload(job)
    assert card["triangles"] == 12
    assert card["atlas_baked"] is False
    assert card["preview_primary"] == "three_quarter"
    assert "spec" not in card
    assert "art_direction" not in card
    payload = inspect_payload(job, full=True)
    assert payload["iteration"] == 1
    assert payload["current_best"] is None
    assert payload["art_direction"]["subject"] == "crate"
    assert payload["evaluation"] is None
    assert payload["previews"]["front"].endswith("front.png")
    assert payload["compare"] is None
    assert payload["silhouette_regressed"] is False
    assert payload["decomposition"] is None
    assert payload["preview_roles"]["primary"] == "three_quarter"
    assert payload["preview_roles"]["context"] is None
    assert "clay_three_quarter" in payload["preview_roles"]["diagnostic"]
    assert "silhouette_side" in payload["preview_roles"]["silhouette"]
    assert "spec" in payload
    assert payload["art_direction"]["silhouette"] == "box"


def test_evaluate_and_history(project: Path, monkeypatch) -> None:
    _seed_job(project)
    monkeypatch.chdir(project)
    eval_path = project / "crit.json"
    eval_path.write_text(json.dumps({
        "passed": False,
        "ship": False,
        "primary_failure": "silhouette reads as a cube",
        "correction_targets": [{"part": "lid"}],
        "scores": {
            "silhouette": 5,
            "proportions": 5,
            "secondary_forms": 5,
            "tertiary_detail": 5,
            "materials": 5,
            "visual_hierarchy": 5,
            "style_consistency": 5,
            "game_readability": 5,
        },
        "issues": [{
            "category": "silhouette",
            "severity": "medium",
            "description": "Reads as a cube",
            "suggested_change": "Add a lid lip",
        }],
    }), encoding="utf-8")
    result = runner.invoke(
        app, ["evaluate", "box", str(eval_path), "--json"],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["iteration"] == 1
    assert data["ship"] is False
    assert data["checkpoint"]["current_best"] == 1
    assert data["next"]["primary_failure"] == (
        "silhouette reads as a cube"
    )
    assert data["next"]["unresolved"] == ["lid"]
    assert data["next"]["measured"]["validation_passed"] is True
    assert "scores" not in data["next"]
    hist = runner.invoke(app, ["history", "box", "--json"])
    assert hist.exit_code == 0
    payload = json.loads(hist.stdout)
    assert payload["iterations"][0]["evaluation_ship"] is False
    assert payload["current_best"] == 1
    assert payload["iterations"][0]["is_best"] is True
    summary = runner.invoke(app, ["history", "box", "--json", "--summary"])
    assert summary.exit_code == 0
    slim = json.loads(summary.stdout)
    assert "previews" not in slim["iterations"][0]
    assert "scores" not in slim["iterations"][0]
    head = list(slim["iterations"][0])[:4]
    assert head == [
        "iteration",
        "primary_failure",
        "correction_targets",
        "verdict",
    ]
    assert slim["iterations"][0]["primary_failure"] == (
        "silhouette reads as a cube"
    )
    assert slim["iterations"][0]["unresolved"] == ["lid"]
    assert slim["iterations"][0]["primary_preview"].endswith(
        "front.png",
    )
    inspect = runner.invoke(
        app, ["inspect", "box", "--json", "--full"],
    )
    assert inspect.exit_code == 0
    info = json.loads(inspect.stdout)
    assert info["evaluation"]["scores"]["silhouette"] == 5
    assert info["current_best"] == 1


def test_evaluate_requires_correction_target(
    project: Path, monkeypatch,
) -> None:
    _seed_job(project)
    monkeypatch.chdir(project)
    path = project / "crit.json"
    path.write_text(json.dumps({
        "passed": False,
        "ship": False,
        "primary_failure": "lid too tall",
        "scores": {"game_readability": 4},
    }), encoding="utf-8")
    result = runner.invoke(
        app, ["evaluate", "box", str(path), "--json"],
    )
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "invalid_evaluation"
    assert "correction_targets" in data["error"]["message"]


def test_next_resolves_landmark_and_iou(project: Path) -> None:
    job = _seed_job(project)
    spec = job.load_spec()
    spec.geometric_plan = GeometricPlan(landmarks=[
        Landmark(id="waterline", role="contact"),
    ])
    job.write_spec(spec)
    metrics = job.iterations / "001" / "silhouette_metrics.json"
    metrics.write_text(json.dumps({"iou": 0.8}), encoding="utf-8")
    later = job.iterations / "002"
    later.mkdir()
    (later / "silhouette_metrics.json").write_text(
        json.dumps({"iou": 0.6}), encoding="utf-8",
    )
    evaluation = VisualEvaluation.model_validate({
        "passed": False,
        "ship": False,
        "primary_failure": "The river sits above the waterline.",
        "correction_targets": [
            {"landmark": "waterline"},
            {"part": "missing"},
        ],
        "scores": {"game_readability": 4},
        "iteration": 2,
        "compare": {"best_iteration": 1, "verdict": "reject"},
    })
    packet = next_packet(job, evaluation)
    assert packet["unresolved"] == ["missing"]
    assert packet["measured"]["silhouette_iou"] == 0.6
    assert packet["measured"]["silhouette_iou_delta"] == -0.2
    assert "validation_passed" not in packet["measured"]
