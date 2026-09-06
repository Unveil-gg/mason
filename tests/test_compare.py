"""Compare plate and silhouette regression flag."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.results import ValidationCheck, ValidationReport
from mason.core.styles import load_style
from mason.pipelines.common import finish_result
from mason.core.art import VisualEvaluation
from mason.pipelines.compare import (
    silhouette_regressed,
    write_compare_plate,
)

runner = CliRunner()


def _seed(project: Path) -> AssetJob:
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
    for name in (
        "silhouette_front", "three_quarter", "front",
    ):
        Image.new("RGB", (32, 32), (10, 20, 30)).save(
            job.previews / f"{name}.png",
        )
    report = ValidationReport(
        passed=True,
        checks=[ValidationCheck(name="ok", passed=True)],
        metrics={},
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


def test_write_compare_plate(project: Path) -> None:
    job = _seed(project)
    dest = write_compare_plate(job)
    assert dest is not None and dest.is_file()
    with Image.open(dest) as img:
        assert img.size == (64, 64)


def test_compare_cli(project: Path, monkeypatch) -> None:
    _seed(project)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["compare", "box", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["compare"].endswith("compare.png")
    assert data["silhouette_regressed"] is False


def _eval(iteration: int, silhouette: int) -> VisualEvaluation:
    return VisualEvaluation.model_validate({
        "passed": False,
        "ship": False,
        "scores": {
            "silhouette": silhouette,
            "proportions": 5,
            "secondary_forms": 5,
            "tertiary_detail": 5,
            "materials": 5,
            "visual_hierarchy": 5,
            "style_consistency": 5,
            "game_readability": 5,
        },
        "issues": [],
        "iteration": iteration,
    })


def test_silhouette_regressed(project: Path) -> None:
    job = _seed(project)
    job.write_evaluation(_eval(1, 8))
    job.write_evaluation(_eval(2, 3))
    assert silhouette_regressed(job) is True


def test_silhouette_regressed_skips_missing_score(project: Path) -> None:
    job = _seed(project)
    job.write_evaluation(VisualEvaluation.model_validate({
        "passed": True,
        "ship": True,
        "scores": {
            "overall_visual_quality": 7,
            "proportions": 7,
            "secondary_forms": 6,
            "tertiary_detail": 5,
            "materials": 6,
            "visual_hierarchy": 7,
            "style_consistency": 8,
            "game_readability": 7,
        },
        "iteration": 1,
    }))
    job.write_evaluation(_eval(2, 3))
    assert silhouette_regressed(job) is False
