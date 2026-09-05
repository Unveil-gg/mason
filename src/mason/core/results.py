"""Build, validation, preview, and execution result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class ExportResult(BaseModel):
    """Result of copying finished outputs into another project."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    asset_id: str
    engine: str
    installed: dict[str, str] = Field(default_factory=dict)
    manifest: str | None = None
