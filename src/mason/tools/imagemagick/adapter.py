"""ImageMagick tool adapter."""

from __future__ import annotations

from pathlib import Path

from mason.core.results import ExecutionResult
from mason.errors import MasonError
from mason.tools.base import ToolInfo
from mason.tools.detect import run_logged
from mason.tools.imagemagick.detection import find_magick, magick_version


class ImageMagickAdapter:
    id = "imagemagick"

    def detect(self, override: Path | None = None) -> ToolInfo:
        path = find_magick(override)
        if path is None:
            return ToolInfo(
                id=self.id,
                available=False,
                error="ImageMagick magick/convert not found",
            )
        version = magick_version(path)
        if version is None:
            return ToolInfo(
                id=self.id,
                available=False,
                path=str(path),
                error="Not an ImageMagick executable",
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
            "ImageMagick is required for the image_process pipeline "
            "but was not found.",
            code="imagemagick_missing",
            hint=(
                "Install ImageMagick or configure tools.imagemagick.path, "
                "then run `mason doctor`."
            ),
        )

    def capabilities(self) -> list[str]:
        return ["raster_processing"]

    def execute(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 120,
        executable: Path | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> ExecutionResult:
        if executable is None or stdout_path is None or stderr_path is None:
            raise MasonError(
                "ImageMagick execute is incomplete.",
                code="internal",
            )
        return run_logged(
            [str(executable), *args],
            stdout_path,
            stderr_path,
            cwd=cwd,
            timeout=timeout,
        )
