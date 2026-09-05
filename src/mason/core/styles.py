"""Style profiles: defaults that asset specs can override."""

from __future__ import annotations

from pathlib import Path

import yaml
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mason.errors import MasonError


class StyleGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bevel_width: float = 0.02
    bevel_segments: int = 2


class StyleMaterials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roughness: float = 0.75
    metallic: float = 0.0


class RenderResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=512, gt=0)
    height: int = Field(default=512, gt=0)


class StyleRender(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: RenderResolution = Field(
        default_factory=RenderResolution,
    )
    samples: int = Field(default=16, gt=0)
    engine: Literal["eevee", "cycles"] = "eevee"


class StyleLighting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: str = "neutral_studio"


class StyleTextures(BaseModel):
    """Defaults for mapping 2D textures onto 3D parts (one texture
    strategy, encoded once instead of per-asset)."""

    model_config = ConfigDict(extra="forbid")

    tile_size: float = Field(default=1.0, gt=0)
    wrap: Literal["repeat", "clamp"] = "repeat"


class StyleProfile(BaseModel):
    """Named palette and default geometry/material/render settings."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: int = 1
    units: str = "meters"
    palette: dict[str, str] = Field(default_factory=dict)
    geometry: StyleGeometry = Field(default_factory=StyleGeometry)
    materials: StyleMaterials = Field(default_factory=StyleMaterials)
    render: StyleRender = Field(default_factory=StyleRender)
    lighting: StyleLighting = Field(default_factory=StyleLighting)
    textures: StyleTextures = Field(default_factory=StyleTextures)

    def color(self, key: str) -> str:
        """Return a palette hex color or raise if missing."""
        if key not in self.palette:
            raise MasonError(
                f"Palette key '{key}' is not in style '{self.name}'.",
                code="unknown_palette_key",
                hint="Use a key from the style palette.",
                context={
                    "key": key,
                    "available": sorted(self.palette),
                },
            )
        return self.palette[key]


def load_style(path: Path) -> StyleProfile:
    """Parse a YAML style file. Returns StyleProfile."""
    if not path.is_file():
        raise MasonError(
            f"Style file not found: {path}",
            code="style_not_found",
            hint="Create styles/<name>.yaml or run mason init.",
            context={"path": str(path)},
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MasonError(
            f"Style file must be a mapping: {path}",
            code="invalid_style",
        )
    try:
        return StyleProfile.model_validate(data)
    except Exception as exc:
        raise MasonError(
            f"Invalid style file {path}: {exc}",
            code="invalid_style",
            context={"path": str(path)},
        ) from exc


def resolve_style(
    project_root: Path,
    name: str,
    default_style: str = "default",
) -> StyleProfile:
    """Load styles/<name>.yaml from the project. Returns StyleProfile."""
    style_name = name or default_style
    path = project_root / "styles" / f"{style_name}.yaml"
    return load_style(path)


DEFAULT_STYLE_YAML = """name: default
version: 1

units: meters

palette:
  wood_dark: "#654936"
  wood_light: "#A77C54"
  cream: "#DDD0B4"
  accent: "#8066A8"
  primary: "#654936"
  ink: "#1A1410"
  label_green: "#2E7D4F"

geometry:
  bevel_width: 0.02
  bevel_segments: 2

materials:
  roughness: 0.75
  metallic: 0.0

render:
  resolution:
    width: 512
    height: 512
  samples: 16
  engine: eevee

lighting:
  preset: neutral_studio

textures:
  tile_size: 1.0
  wrap: repeat
"""
