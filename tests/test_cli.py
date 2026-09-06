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
    assert "silhouette_front" in data["inspect"]


def test_inspect_missing(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["inspect", "missing", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "job_not_found"
