"""Krita tool adapter."""

from __future__ import annotations

from pathlib import Path

from mason.core.results import ExecutionResult
from mason.errors import MasonError
from mason.tools.base import ToolInfo
from mason.tools.detect import run_logged
from mason.tools.krita.detection import (
    find_krita,
    find_kritarunner,
    krita_version,
)


class KritaAdapter:
    id = "krita"

    def detect(self, override: Path | None = None) -> ToolInfo:
        path = find_krita(override)
        if path is None:
            return ToolInfo(
                id=self.id,
                available=False,
                error="Krita executable not found",
            )
        version = krita_version(path)
        runner = find_kritarunner(path)
        extras = {}
        if runner:
            extras["kritarunner"] = str(runner)
        return ToolInfo(
            id=self.id,
            available=True,
            path=str(path),
            version=version,
            extras=extras,
            error=None if version else "Could not parse krita --version",
        )

    def validate_installation(self, info: ToolInfo) -> None:
        if info.available and info.path:
            return
        raise MasonError(
            "Krita is required for the layered_raster pipeline "
            "but was not found.",
            code="krita_missing",
            hint=(
                "Install Krita or configure its executable path, "
                "then run `mason doctor`."
            ),
        )

    def capabilities(self) -> list[str]:
        return ["raster_document", "layered_raster", "image_export"]

    def execute(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 300,
        executable: Path | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> ExecutionResult:
        if executable is None:
            raise MasonError("Krita executable is required.", code="krita_missing")
        if stdout_path is None or stderr_path is None:
            raise MasonError("Log paths are required.", code="internal")
        return run_logged(
            [str(executable), *args],
            stdout_path,
            stderr_path,
            cwd=cwd,
            timeout=timeout,
        )
