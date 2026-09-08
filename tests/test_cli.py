"""CLI JSON and error paths."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mason.cli import app

runner = CliRunner()


def test_doctor_json() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "tools" in data
    assert "capabilities" in data
    assert "blender" in data["tools"]


def test_init_json(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert (tmp_path / "mason.yaml").is_file()
    assert (tmp_path / "styles" / "default.yaml").is_file()


def test_build_invalid_spec(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    bad = project / "bad.yaml"
    bad.write_text("type: nope\nid: x\nname: X\n", encoding="utf-8")
    result = runner.invoke(app, ["build", str(bad), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["code"] == "invalid_asset_spec"


def test_not_a_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "not_a_project"


def test_vocab_json() -> None:
    result = runner.invoke(app, ["vocab", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "x_brace" in data["components"]
    assert "l_corner" in data["stamps"]
    assert "dapple" in data["stamps"]
    assert "figure" in data["stamps"]
    assert "cart" in data["recipes"]
    assert "estate" in data["recipes"]
    assert "lawn" in data["families"]
    assert "cutout" in data
    assert "silhouette_regressed" in data["inspect"]
    assert "pixels+keys" in data["raster"]
    assert "barbarian.yaml" in data["sprites"]
    assert "shopping_cart.yaml" in data["variants"]
    assert "--demo-lighting" in data["demo_lighting"]
    assert "lathe" in data["shapes"]
    assert "curve" in data["shapes"]
    assert "skin" in data["shapes"]
    assert "outline" in data["shapes"]
    assert "modeling" in data
    assert "construction_plan.techniques" in data["modeling"]
    assert "profile:" in data["lathe"]
    assert "origin: center|base" in data["bend"]
    assert "--fetch" in data["ingest"]
    assert "run.json" in data["run"]


def test_clean_removes_jobs(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    job_dir = project / ".mason" / "jobs" / "box"
    job_dir.mkdir(parents=True)
    (job_dir / "asset.yaml").write_text("id: box\n", encoding="utf-8")
    result = runner.invoke(app, ["clean", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["removed"] == ["box"]
    assert not job_dir.is_dir()


def test_note_requires_run(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    job_dir = project / ".mason" / "jobs" / "box"
    job_dir.mkdir(parents=True)
    (job_dir / "asset.yaml").write_text("id: box\n", encoding="utf-8")
    result = runner.invoke(app, ["note", "box", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "run_not_found"


def test_inspect_missing(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["inspect", "missing", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "job_not_found"
