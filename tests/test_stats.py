"""mason stats reads stored triangle counts."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.core.styles import load_style
from mason.pipelines.common import finish_result

runner = CliRunner()


def _seed(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_style(load_style(project / "styles" / "default.yaml"))
    job.write_meta("assets/box.yaml")
    report = ValidationReport(
        passed=True,
        checks=[ValidationCheck(name="ok", passed=True)],
        metrics={"triangles": 24, "mesh_count": 1, "materials": 3},
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


def test_stats_one_asset(project: Path, monkeypatch) -> None:
    _seed(project)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["stats", "box", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["asset_id"] == "box"
    assert data["triangles"] == 24
    assert data["meshes"] == 1


def test_stats_all_jobs(project: Path, monkeypatch) -> None:
    _seed(project)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["assets"][0]["triangles"] == 24
