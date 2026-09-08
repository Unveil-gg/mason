"""Job directory helpers."""

from __future__ import annotations

from pathlib import Path

from datetime import datetime, timezone

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob, list_jobs
from mason.core.results import BuildResult
from mason.core.runs import RunContext, load_run, patch_run, record_build_run
from mason.core.styles import load_style


def test_job_roundtrip(project: Path) -> None:
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
    assert job.exists()
    loaded = job.load_spec()
    assert loaded.id == "box"
    assert list_jobs(project)[0].asset_id == "box"
    assert job.rel(job.output).startswith(".mason/")


def test_run_json_roundtrip(project: Path) -> None:
    spec = parse_asset_spec({
        "type": "static_prop",
        "id": "box",
        "name": "Box",
        "dimensions": {"width": 1, "depth": 1, "height": 1},
        "geometry": {"recipe": "crate"},
        "art_direction": {"subject": "a wooden crate"},
    })
    job = AssetJob(project, spec.id)
    job.prepare()
    job.write_spec(spec)
    job.write_meta(None)
    job.run_ctx = RunContext(
        started_at=datetime.now(timezone.utc),
        command="build",
        prompt="a wooden crate",
    )
    result = BuildResult(
        success=True,
        asset_id="box",
        asset_type="static_prop",
        tool="blender",
        validation={"triangles": 48},
        style="default",
    )
    record_build_run(job, result, 1)
    run = load_run(job)
    assert run is not None
    assert run.prompt == "a wooden crate"
    assert run.triangles == 48
    assert run.tokens is None
    job.snapshot_iteration(1)
    snap = job.iterations / "001" / "run.json"
    assert snap.is_file()
    patched = patch_run(job, model="test-model", tokens=12)
    assert patched.model == "test-model"
    assert patched.tokens == 12
