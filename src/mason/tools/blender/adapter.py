"""Blender tool adapter."""

from __future__ import annotations

from pathlib import Path

from mason.core.results import ExecutionResult
from mason.errors import MasonError
from mason.tools.base import ToolInfo
from mason.tools.blender.detection import blender_version, find_blender
from mason.tools.detect import run_logged


class BlenderAdapter:
    id = "blender"

    def detect(self, override: Path | None = None) -> ToolInfo:
        path = find_blender(override)
        if path is None:
            return ToolInfo(
                id=self.id,
                available=False,
                error="Blender executable not found",
            )
        version = blender_version(path)
        if version is None:
            return ToolInfo(
                id=self.id,
                available=False,
                path=str(path),
                error="Could not parse blender --version",
            )
        return ToolInfo(
            id=self.id,
            available=True,
            path=str(path),
            version=version,
        )

    def validate_installation(self, info: ToolInfo) -> None:
        if info.available and info.path:
            return
        raise MasonError(
            "Blender is required for the procedural_3d pipeline "
            "but was not found.",
            code="blender_missing",
            hint=(
                "Install Blender or configure its executable path, "
                "then run `mason doctor`."
            ),
        )

    def capabilities(self) -> list[str]:
        return ["procedural_3d", "render_preview", "glb_export"]

    def execute(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 600,
        executable: Path | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> ExecutionResult:
        if executable is None:
            raise MasonError("Blender executable is required.", code="blender_missing")
        command = [str(executable), *args]
        if stdout_path is None or stderr_path is None:
            raise MasonError("Log paths are required.", code="internal")
        return run_logged(
            command,
            stdout_path,
            stderr_path,
            cwd=cwd,
            timeout=timeout,
        )
