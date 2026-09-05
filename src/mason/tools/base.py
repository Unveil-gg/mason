"""Adapter contract and ToolInfo."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from mason.core.results import ExecutionResult


class ToolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    available: bool
    path: str | None = None
    version: str | None = None
    error: str | None = None
    extras: dict[str, str] = Field(default_factory=dict)


class ToolAdapter(Protocol):
    id: str

    def detect(self, override: Path | None = None) -> ToolInfo:
        """Find the executable and parse version."""
        ...

    def validate_installation(self, info: ToolInfo) -> None:
        """Raise MasonError if this tool cannot be used."""
        ...

    def capabilities(self) -> list[str]:
        """Capability ids this tool provides when available."""
        ...

    def execute(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 300,
        executable: Path | None = None,
    ) -> ExecutionResult:
        """Run the tool with argv (no shell)."""
        ...
