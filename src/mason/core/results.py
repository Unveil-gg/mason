"""Build, validation, preview, and execution result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Metrics cheap enough to always show. Bulky per-item arrays (e.g.
# a layered_raster's layer_names, a static_prop's object_bounds) are
# dropped by default -- see slim_validation and mason.core.inspect.
SLIM_METRICS_KEYS = (
    "triangles", "materials", "mesh_count", "bounds", "width",
    "height", "layers",
)


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: list[str]
    exit_code: int
    stdout_path: str
    stderr_path: str
    success: bool


class ValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    detail: str | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    checks: list[ValidationCheck] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class PreviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    views: dict[str, str] = Field(default_factory=dict)


class BuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    asset_id: str
    asset_type: str
    tool: str | None = None
    tool_version: str | None = None
    outputs: dict[str, str] = Field(default_factory=dict)
    previews: dict[str, str] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    job_dir: str = ""
    built_at: str = ""
    source_spec: str | None = None
    style: str | None = None
    error: dict[str, Any] | None = None
    variants: list[dict[str, Any]] = Field(default_factory=list)
    preview_roles: dict[str, Any] = Field(default_factory=dict)


class ExportResult(BaseModel):
    """Result of copying finished outputs into another project."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    asset_id: str
    engine: str
    installed: dict[str, str] = Field(default_factory=dict)
    manifest: str | None = None
    optimized: dict[str, str] = Field(default_factory=dict)


def slim_validation(validation: dict[str, Any]) -> dict[str, Any]:
    """Filter a BuildResult.validation dict down to failed_checks
    plus a few cheap metrics, for default (non --full) --json
    output. Mirrors mason.core.inspect's slimming of ValidationReport."""
    return {
        "passed": validation.get("passed"),
        "failed_checks": validation.get("failed_checks", []),
        **{
            key: validation[key]
            for key in SLIM_METRICS_KEYS if key in validation
        },
    }


class KitExportResult(BaseModel):
    """Result of exporting every member of a kit. Export-only -- no
    member is built here."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    kit_id: str
    engine: str
    members: dict[str, ExportResult] = Field(default_factory=dict)
    manifest: str | None = None
