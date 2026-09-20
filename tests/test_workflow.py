"""Workflow router, plan gate, critique, locks, paint, masters."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from mason.cli import app
from mason.core.approvals import (
    ApprovalLock,
    JobApprovals,
    locked_paths_changed,
)
from mason.core.art import ArtDirection, VisualEvaluation
from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob
from mason.core.plan_gate import plan_payload
from mason.core.workflow import infer_workflow, route_card
from mason.core.styles import load_style
from mason.pipelines.checkpoint import apply_checkpoint, restart_parts
from mason.pipelines.common import finish_result
from mason.core.results import ValidationCheck, ValidationReport

runner = CliRunner()


def _png(path: Path, color=(40, 40, 40)) -> Path:
    Image.new("RGB", (32, 32), color).save(path)
    return path


def _scores(**extra) -> dict:
    base = {
        "proportions": 5,
        "secondary_forms": 5,
        "tertiary_detail": 5,
        "materials": 5,
        "visual_hierarchy": 5,
        "style_consistency": 5,
        "game_readability": 5,
        "silhouette": 5,
    }
    base.update(extra)
    return base


def _seed_box(project: Path) -> AssetJob:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "workflow": "prop",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "parts": [
                {
                    "name": "body",
                    "shape": "box",
                    "size": [1, 1, 1],
                    "location": [0, 0, 0],
                },
                {
                    "name": "lid",
                    "shape": "box",
                    "size": [1, 1, 0.1],
                    "location": [0, 0, 0.55],
                },
            ],
        },
        "art_direction": {
            "subject": "wooden crate",
            "silhouette": "box with lid",
            "focal_point": "lid lip",
        },
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_style(load_style(project / "styles" / "default.yaml"))
    job.write_meta("assets/box.yaml")
    _png(job.previews / "three_quarter.png")
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
        outputs={"glb": job.rel(job.output / "asset.glb")},
        previews={
            "three_quarter": job.rel(job.previews / "three_quarter.png"),
        },
        report=report,
        source_spec="assets/box.yaml",
    )
    (job.output / "asset.glb").write_bytes(b"live-glb")
    snap = job.iterations / "001" / "output"
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "asset.glb").write_bytes(b"best-glb")
    return job


def test_infer_garment_pipeline() -> None:
    fitted = parse_asset_spec({
        "type": "static_prop",
        "id": "tee",
        "name": "Tee",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"garment": {"mode": "template"}},
    })
    assert infer_workflow("shirt", fitted) == "clothing_fitted"
    drape = parse_asset_spec({
        "type": "static_prop",
        "id": "coat",
        "name": "Coat",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "garment": {"mode": "template", "pipeline": "drape"},
        },
    })
    assert infer_workflow("shirt", drape) == "clothing_loose"
    loose = parse_asset_spec({
        "type": "static_prop",
        "id": "hoodie",
        "name": "Hoodie",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {
            "garment": {"mode": "template", "fit": "loose"},
        },
    })
    assert infer_workflow("hoodie", loose) == "clothing_loose"


def test_infer_workflow_keywords() -> None:
    assert infer_workflow("Staunton chess knight") == "sculptural"
    assert infer_workflow("turned vase profile") == "turned"
    assert infer_workflow("NYC townhouse facade") == "building"
    assert infer_workflow("fitted shirt") == "clothing_fitted"
    assert infer_workflow("board game cover") == "illustrated"
    assert infer_workflow("pixel sprite walk cycle") == "pixel"
    assert infer_workflow("import licensed mesh") == "import"


def test_route_card_turned() -> None:
    card = route_card("chess queen lathe")
    assert card.workflow == "turned"
    assert card.type == "static_prop"
    assert "lathe" in card.operations
    assert card.painterly is False


def test_route_and_vocab_cli(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["route", "wooden shelf", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["workflow"] == "prop"
    scoped = runner.invoke(
        app, ["vocab", "--workflow", "turned", "--json"],
    )
    assert scoped.exit_code == 0, scoped.stdout
    card = json.loads(scoped.stdout)
    assert card["workflow"] == "turned"
    assert "lathe" in card["shapes"]
    assert "stamps" not in card
    assert "garment" not in card


def test_plan_gate_turned_missing_refs() -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "pawn",
        "name": "Pawn",
        "workflow": "turned",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "art_direction": {"subject": "pawn"},
    })
    payload = plan_payload(spec)
    assert payload["passed"] is False
    assert "art_direction.silhouette" in payload["missing"]


def test_plan_cli(project: Path, monkeypatch) -> None:
    job = _seed_box(project)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["plan", job.asset_id, "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["passed"] is True
    assert data["workflow"] == "prop"


def test_evaluate_requires_primary_failure(
    project: Path, monkeypatch,
) -> None:
    _seed_box(project)
    monkeypatch.chdir(project)
    path = project / "crit.json"
    path.write_text(json.dumps({
        "passed": False,
        "ship": False,
        "scores": _scores(),
    }), encoding="utf-8")
    result = runner.invoke(app, ["evaluate", "box", str(path), "--json"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["error"]["code"] == "invalid_evaluation"


def test_ship_blocked_by_critical(project: Path) -> None:
    job = _seed_box(project)
    evaluation = VisualEvaluation.model_validate({
        "passed": False,
        "ship": True,
        "primary_failure": "lid too flat",
        "scores": _scores(),
        "iteration": 1,
        "discrepancies": [{
            "rank": "critical",
            "category": "silhouette",
            "description": "lid",
        }],
    })
    status = apply_checkpoint(job, evaluation)
    assert status["verdict"] == "reject"
    stored = job.load_evaluation(1)
    assert stored is not None
    assert stored.ship is False


def test_approval_lock_rejects_edit(project: Path) -> None:
    job = _seed_box(project)
    apply_checkpoint(job, VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "scores": _scores(silhouette=7),
        "iteration": 1,
        "approved": ["part.body"],
        "compare": {"verdict": "accept"},
    }))
    live = job.load_spec()
    live.geometry.parts[0].size = (2.0, 2.0, 2.0)
    job.write_spec(live)
    status = apply_checkpoint(job, VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "scores": _scores(silhouette=8),
        "iteration": 1,
        "compare": {"verdict": "accept"},
    }))
    assert status["verdict"] == "reject"
    assert "part.body" in status["locked_changed"]


def test_restart_keeps_named_part(project: Path) -> None:
    job = _seed_box(project)
    apply_checkpoint(job, VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "scores": _scores(silhouette=7),
        "iteration": 1,
        "compare": {"verdict": "accept"},
    }))
    payload = restart_parts(job, keep=["body"], rebuild=["lid"])
    assert "body" in payload["kept"]
    assert "lid" in payload["removed"]
    live = job.load_spec()
    names = [p.name for p in live.geometry.parts]
    assert "lid" not in names
    assert "body" in names


def test_paint_prepares_underlay(project: Path, monkeypatch) -> None:
    job = _seed_box(project)
    monkeypatch.chdir(project)
    result = runner.invoke(
        app, ["paint", job.asset_id, "--from", "render", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["parent"] == "box"
    assert data["from"] == "render"
    spec = parse_asset_spec(
        __import__("yaml").safe_load(
            (project / data["spec"]).read_text(encoding="utf-8"),
        ),
    )
    roles = [layer.role for layer in spec.layers]
    assert "underlay" in roles
    assert "paint" in roles


def test_approve_master(project: Path, monkeypatch) -> None:
    job = _seed_box(project)
    apply_checkpoint(job, VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "scores": _scores(silhouette=8),
        "iteration": 1,
        "compare": {"verdict": "accept"},
    }))
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["approve", "box", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["id"] == "box"
    assert (project / "masters" / "box.yaml").is_file()
    meta = job.load_meta()
    assert meta is not None
    assert meta.approved_master is True


def test_stats_accepted(project: Path, monkeypatch) -> None:
    job = _seed_box(project)
    apply_checkpoint(job, VisualEvaluation.model_validate({
        "passed": True,
        "ship": False,
        "scores": _scores(silhouette=8),
        "iteration": 1,
        "compare": {"verdict": "accept"},
    }))
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["stats", "--accepted", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["accepted"][0]["asset_id"] == "box"
    assert data["accepted"][0]["iterations_to_accept"] == 1


def test_garment_pipeline_helper() -> None:
    from mason.tools.blender.validation import _garment_pipeline
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "tee",
        "name": "Tee",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"garment": {"mode": "template"}},
    })
    assert _garment_pipeline(spec) == "stylized"
    spec.geometry.garment.pipeline = "drape"
    assert _garment_pipeline(spec) == "drape"


def test_pose_score_gate() -> None:
    from mason.tools.blender.validation import _pose_tests_ok
    ok, _ = _pose_tests_ok({})
    assert ok is True
    ok, detail = _pose_tests_ok({
        "pose_scores": {"stand": {"penetration": 0.4}},
    })
    assert ok is False
    assert "stand" in detail


def test_pixel_plan_needs_master_frame() -> None:
    spec = parse_asset_spec({
        "type": "sprite_sheet",
        "id": "hero",
        "name": "Hero",
        "workflow": "pixel",
        "canvas": {"width": 16, "height": 16},
        "art_direction": {"subject": "hero", "focal_point": "sword"},
        "animations": [
            {
                "name": "idle",
                "frames": [{"layers": [{"name": "a", "fill": "ink"}]}],
            },
            {
                "name": "walk",
                "frames": [{"layers": [{"name": "a", "fill": "ink"}]}],
            },
        ],
    })
    payload = plan_payload(spec)
    assert "master_frame" in payload["missing"]


def test_art_direction_gameplay_defaults() -> None:
    brief = ArtDirection(subject="barista")
    assert brief.focal_point == ""
    assert brief.asymmetry == "none"
    assert brief.gameplay.must_read == []


def test_locked_paths_helper(project: Path) -> None:
    job = _seed_box(project)
    live = job.load_spec()
    best = job.load_spec()
    approvals = JobApprovals(locks=[
        ApprovalLock(path="part.body", iteration_approved=1),
    ])
    assert locked_paths_changed(live, best, approvals) == []
    live.geometry.parts[0].size = (3.0, 1.0, 1.0)
    assert locked_paths_changed(live, best, approvals) == ["part.body"]
