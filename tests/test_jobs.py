"""Job directory helpers."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import parse_asset_spec
from mason.core.jobs import AssetJob, list_jobs
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
