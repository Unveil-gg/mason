"""Result model JSON shape."""

from __future__ import annotations

from mason.core.results import BuildResult, ValidationCheck, ValidationReport


def test_build_result_json() -> None:
    result = BuildResult(
        success=True,
        asset_id="simple_crate",
        asset_type="static_prop",
        outputs={"glb": ".mason/jobs/simple_crate/output/asset.glb"},
        previews={"front": ".mason/jobs/simple_crate/previews/front.png"},
        validation={"passed": True, "triangles": 840},
        job_dir=".mason/jobs/simple_crate",
    )
    data = result.model_dump()
    assert data["success"] is True
    assert data["previews"]["front"].endswith("front.png")
    assert data["validation"]["triangles"] == 840


def test_validation_report() -> None:
    report = ValidationReport(
        passed=True,
        checks=[ValidationCheck(name="output_exists", passed=True)],
        metrics={"triangles": 12},
    )
    data = report.model_dump()
    assert data["checks"][0]["name"] == "output_exists"
