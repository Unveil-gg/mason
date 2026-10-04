"""Style profiles: defaults that asset specs can override."""

from __future__ import annotations

from pathlib import Path

import yaml
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mason.core.parts import ImageSource
from mason.errors import MasonError


class StyleGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bevel_width: float = 0.02
    bevel_segments: int = 2


class MaterialFamily(BaseModel):
    """Reusable PBR-ish settings for a named material family."""

    model_config = ConfigDict(extra="forbid")

    roughness: float = Field(default=0.75, ge=0, le=1)
    metallic: float = Field(default=0.0, ge=0, le=1)
    variation: float = Field(default=0.0, ge=0, le=1)
    noise_scale: float | None = Field(default=None, gt=0)
    albedo: ImageSource | None = None
    roughness_map: ImageSource | None = None
    bump_map: ImageSource | None = None
    normal_map: ImageSource | None = None
    bump_strength: float = Field(default=0.04, ge=0, le=1)
    shader: Literal["principled", "fabric"] = "principled"
    shader_params: dict[str, float] = Field(default_factory=dict)
    tile_size: float | None = Field(default=None, gt=0)


class StyleMaterials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roughness: float = 0.75
    metallic: float = 0.0
    families: dict[str, MaterialFamily] = Field(default_factory=dict)


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

    preset: Literal["neutral_studio", "high_key"] = "neutral_studio"


class QualityGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail_density: Literal["low", "medium", "high"] = "medium"


class StyleTextures(BaseModel):
    """Defaults for mapping 2D textures onto 3D parts (one texture
    strategy, encoded once instead of per-asset)."""

    model_config = ConfigDict(extra="forbid")

    tile_size: float = Field(default=1.0, gt=0)
    wrap: Literal["repeat", "clamp"] = "repeat"


class ContextPreview(BaseModel):
    """Future in-engine / Godot preview. Unused until implemented."""

    model_config = ConfigDict(extra="forbid")

    camera_angle: str = ""
    camera_distance: str = ""
    lighting: str = ""
    environment: str = ""
    scale_ref: str = ""


class StyleProcess(BaseModel):
    """Hand ranges. Zero keeps a mark or part exact."""

    model_config = ConfigDict(extra="forbid")

    jitter: float = Field(default=0.0, ge=0, le=1)
    density: float = Field(default=0.0, ge=0, le=1)
    irregularity: float = Field(default=0.0, ge=0, le=1)
    overlap: float = Field(default=0.0, ge=0, le=1)
    breakup: float = Field(default=0.0, ge=0, le=1)
    variation: float = Field(default=0.0, ge=0, le=1)


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
    process: StyleProcess = Field(default_factory=StyleProcess)
    quality: dict[str, QualityGuidance] = Field(default_factory=dict)
    context_preview: ContextPreview | None = None

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


def hex_rgba(value: str) -> list[int]:
    """Parse `#RRGGBB` or `#RRGGBBAA` into `[r, g, b, a]` (0-255)."""
    text = value.strip().lstrip("#")
    if len(text) == 6:
        text += "FF"
    if len(text) != 8:
        raise MasonError(
            f"Invalid hex color '{value}'.",
            code="invalid_hex",
            hint="Use #RRGGBB or #RRGGBBAA.",
        )
    return [int(text[i : i + 2], 16) for i in (0, 2, 4, 6)]


def load_style(path: Path) -> StyleProfile:
    """Parse a YAML style file. Returns StyleProfile."""
    if not path.is_file():
        raise MasonError(
            f"Style file not found: {path}",
            code="style_not_found",
            hint=(
                "Create styles/<name>.yaml. "
                "The default style is built in."
            ),
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


def packaged_default_style() -> StyleProfile:
    """Return the default style shipped with the CLI."""
    data = yaml.safe_load(DEFAULT_STYLE_YAML)
    return StyleProfile.model_validate(data)


def resolve_style(
    project_root: Path,
    name: str,
    default_style: str = "default",
) -> StyleProfile:
    """Load styles/<name>.yaml, or the built-in default.

    A project file wins. Returns StyleProfile.
    """
    style_name = name or default_style
    path = project_root / "styles" / f"{style_name}.yaml"
    if path.is_file():
        return load_style(path)
    if style_name == "default":
        return packaged_default_style()
    raise MasonError(
        f"Style file not found: {path}",
        code="style_not_found",
        hint=(
            "Create styles/<name>.yaml. "
            "The default style is built in."
        ),
        context={"path": str(path)},
    )


def style_payload(profile: StyleProfile) -> dict[str, Any]:
    """Slim style card for agents (palette keys, families, quality)."""
    return {
        "name": profile.name,
        "palette_keys": sorted(profile.palette),
        "families": sorted(profile.materials.families),
        "quality": {
            key: value.model_dump(mode="json")
            for key, value in profile.quality.items()
        },
        "geometry": profile.geometry.model_dump(mode="json"),
        "render": profile.render.model_dump(mode="json"),
        "lighting": profile.lighting.model_dump(mode="json"),
        "textures": profile.textures.model_dump(mode="json"),
        "process": profile.process.model_dump(mode="json"),
    }


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
  charcoal: "#3A3632"
  smoke: "#5C5548"
  hydrant_red: "#C23B2E"
  brass: "#C4A15A"
  steel: "#8A9196"

geometry:
  bevel_width: 0.02
  bevel_segments: 2

materials:
  roughness: 0.75
  metallic: 0.0
  families:
    painted_metal:
      roughness: 0.45
      metallic: 0.15
      variation: 0.08
    bare_metal:
      roughness: 0.35
      metallic: 0.75
      variation: 0.04
    varnished_wood:
      roughness: 0.35
      metallic: 0.0
      variation: 0.06
      albedo:
        asset: plank_texture
        file: output/asset.png
    rubber:
      roughness: 0.9
      metallic: 0.0
      variation: 0.02
    plastic:
      roughness: 0.4
      metallic: 0.0
      variation: 0.03
    cardboard:
      roughness: 0.85
      metallic: 0.0
      variation: 0.05
    fabric:
      roughness: 0.88
      metallic: 0.0
      variation: 0.06
      shader: fabric
      bump_strength: 0.05

render:
  resolution:
    width: 512
    height: 512
  samples: 16
  engine: eevee

lighting:
  preset: neutral_studio

quality:
  background_prop:
    detail_density: low
  standard_prop:
    detail_density: medium
  focal_prop:
    detail_density: high
  hero:
    detail_density: high

textures:
  tile_size: 1.0
  wrap: repeat
"""
