"""Evaluate, history, inspect, and iteration snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.inspect import inspect_payload
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
    payload = inspect_payload(job)
    assert payload["iteration"] == 1
    assert payload["art_direction"]["subject"] == "crate"
    assert payload["evaluation"] is None
    assert payload["previews"]["front"].endswith("front.png")
    assert payload["compare"] is None
    assert payload["silhouette_regressed"] is False
    assert payload["preview_roles"]["primary"] == "three_quarter"
    assert payload["preview_roles"]["context"] is None
    assert "clay_three_quarter" in payload["preview_roles"]["diagnostic"]
    assert "spec" not in payload
    full = inspect_payload(job, full=True)
    assert "spec" in full


def test_evaluate_and_history(project: Path, monkeypatch) -> None:
    _seed_job(project)
    monkeypatch.chdir(project)
    eval_path = project / "crit.json"
    eval_path.write_text(json.dumps({
        "passed": False,
        "ship": False,
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
    hist = runner.invoke(app, ["history", "box", "--json"])
    assert hist.exit_code == 0
    payload = json.loads(hist.stdout)
    assert payload["iterations"][0]["evaluation_ship"] is False
    inspect = runner.invoke(app, ["inspect", "box", "--json"])
    assert inspect.exit_code == 0
    info = json.loads(inspect.stdout)
    assert info["evaluation"]["scores"]["silhouette"] == 5
