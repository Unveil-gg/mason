"""Aseprite tool adapter (discovery only in v0.1)."""

from __future__ import annotations

from pathlib import Path

from mason.core.results import ExecutionResult
from mason.errors import MasonError
from mason.tools.aseprite.detection import aseprite_version, find_aseprite
from mason.tools.base import ToolInfo
from mason.tools.detect import run_logged


class AsepriteAdapter:
    id = "aseprite"

    def detect(self, override: Path | None = None) -> ToolInfo:
        path = find_aseprite(override)
        if path is None:
            return ToolInfo(
                id=self.id,
                available=False,
                error="Aseprite executable not found",
            )
        version = aseprite_version(path)
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
            "Aseprite was not found.",
            code="aseprite_missing",
            hint="Install Aseprite or set tools.aseprite.path.",
        )

    def capabilities(self) -> list[str]:
        return ["sprite_animation"]

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
        if executable is None or stdout_path is None or stderr_path is None:
            raise MasonError("Aseprite execute is incomplete.", code="internal")
        return run_logged(
            [str(executable), *args],
            stdout_path,
            stderr_path,
            cwd=cwd,
            timeout=timeout,
        )
