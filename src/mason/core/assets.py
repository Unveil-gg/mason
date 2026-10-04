"""Asset specs: tagged union for 3D, raster, and image ops."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)

from mason.core.art import ArtFields
from mason.core.parts import (  # noqa: F401
    AttachSocket,
    DecalSpec,
    Dimensions3D,
    GeometrySpec,
    ImageSource,
    PartArray,
    PartCutout,
    PartSnap,
    PropPart,
    RecipeParams,
)
from mason.errors import MasonError


class PixelDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ExportVolume(BaseModel):
    """Gameplay hull written as a glTF empty plus extras.

    `min`/`max` are world AABB. When omitted, Mason unions the
    named parts (or every static mesh, if `parts` is empty).
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["box"] = "box"
    parts: list[str] = Field(default_factory=list)
    min: tuple[float, float, float] | None = None
    max: tuple[float, float, float] | None = None


class Export3D(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["glb"] = "glb"
    save_blend: bool = True
    install_to: str | None = None
    # kit: one object per part. prop: merge statics, bake one atlas.
    profile: Literal["kit", "prop"] = "kit"
    # Roots that stay separate, plus their children. Empty on a
    # prop falls back to attachment parents.
    movers: list[str] = Field(default_factory=list)
    atlas_size: int = Field(default=1024, ge=64, le=2048)
    volumes: list[ExportVolume] = Field(default_factory=list)


class MaterialsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["family", "palette", "atlas"] = "family"
    primary: str = "primary"
    roughness: float | None = None
    metallic: float | None = None
    atlas: str | None = None
    entry: str | None = None
    palette_overrides: dict[str, str] = Field(default_factory=dict)
    shader: Literal["principled", "fabric"] | None = None
    bump_map: ImageSource | None = None
    normal_map: ImageSource | None = None
    bump_strength: float = Field(default=0.04, ge=0, le=1)

    @model_validator(mode="after")
    def atlas_needs_ids(self) -> MaterialsSpec:
        if self.strategy == "atlas" and (
            not self.atlas or not self.entry
        ):
            raise ValueError("atlas strategy needs atlas and entry")
        return self


class MaterialVariant(BaseModel):
    """One palette-swap sibling asset, fanned out at build time."""

    model_config = ConfigDict(extra="forbid")

    suffix: str
    primary: str | None = None
    palette_overrides: dict[str, str] = Field(default_factory=dict)


class StaticPropSpec(ArtFields):
    """Procedural 3D prop built from primitive parts."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["static_prop"]
    id: str
    name: str
    dimensions: Dimensions3D
    style: str = "default"
    geometry: GeometrySpec
    materials: MaterialsSpec = Field(default_factory=MaterialsSpec)
    decals: list[DecalSpec] = Field(default_factory=list)
    variants: list[MaterialVariant] = Field(default_factory=list)
    export: Export3D = Field(default_factory=Export3D)
    attachments: list[AttachSocket] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class LayerRect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


# Transparent cells in a `pixels` map. Any other character must appear
# in that layer's `keys` dict (palette lookup happens at build time).
PIXEL_TRANSPARENT = frozenset(". _")


class DabStroke(BaseModel):
    """Polyline of round dabs. Baked to a PNG before Krita."""

    model_config = ConfigDict(extra="forbid")

    points: list[tuple[float, float]] = Field(min_length=2)
    radius: float = Field(default=6.0, gt=0)
    spacing: float = Field(default=0.45, gt=0, le=2)
    strength: float = Field(default=0.85, ge=0, le=1)


class LayerExpression(BaseModel):
    """Sandboxed formula over x/y/u/v/w/h/seed. Mason bakes a PNG
    and hands it to Krita as a role:image layer."""

    model_config = ConfigDict(extra="forbid")

    formula: str
    mode: Literal["alpha", "color", "height", "normal"] = "alpha"
    to: str | None = None
    seed: int = 0


class RasterLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: Literal[
        "background", "fill", "text", "image", "overlay",
        "underlay", "paint", "mask", "lettering",
    ] | None = None
    fill: str | None = None
    rect: LayerRect | None = None
    text: str | None = None
    font_size: int = Field(default=48, gt=0)
    font: str = "DejaVu Sans"
    align: Literal["left", "center", "right"] = "center"
    image: str | None = None
    pixels: list[str] | None = None
    keys: dict[str, str] = Field(default_factory=dict)
    stamp: Literal[
        "l_corner", "gem", "rule", "bond",
        "dapple", "vignette", "figure", "speckle",
        "courses", "pavers",
    ] | None = None
    stamp_corner: Literal["tl", "tr", "bl", "br"] = "tl"
    stamp_inner: str | None = None
    stamp_seed: int | None = None
    shape: Literal["rect", "ellipse"] = "rect"
    opacity: float = Field(default=1.0, ge=0, le=1)
    expression: LayerExpression | None = None
    stroke: DabStroke | None = None

    @model_validator(mode="after")
    def need_content(self) -> RasterLayer:
        if self.stroke:
            if not self.fill:
                raise ValueError("stroke needs fill")
            return self
        if self.expression:
            if not self.fill or self.rect is None:
                raise ValueError("expression needs fill and rect")
            if self.expression.mode == "color" and not self.expression.to:
                raise ValueError("expression color mode needs to")
            return self
        if self.stamp:
            if not self.fill or self.rect is None:
                raise ValueError("stamp needs fill and rect")
            return self
        if self.role in ("paint", "mask", "lettering", "underlay"):
            if self.role == "underlay" and not self.image:
                raise ValueError("underlay needs image")
            return self
        if not self.fill and not self.text and not self.image and not self.pixels:
            raise ValueError("layer needs fill, text, image, or pixels")
        if self.pixels:
            used = {
                ch for row in self.pixels for ch in row
                if ch not in PIXEL_TRANSPARENT
            }
            missing = sorted(used - set(self.keys))
            if missing:
                raise ValueError(
                    "pixels uses characters with no keys entry: "
                    + ", ".join(missing),
                )
        return self


class RasterExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kra: bool = True
    png: bool = True
    install_to: str | None = None


class LayeredRasterSpec(ArtFields):
    """Layered raster document for Krita."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["layered_raster"]
    id: str
    name: str
    dimensions: PixelDimensions | None = None
    style: str = "default"
    layers: list[RasterLayer] = Field(min_length=1)
    export: RasterExport = Field(default_factory=RasterExport)
    metadata: dict[str, str] = Field(default_factory=dict)


class ResizeOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["resize"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fit: Literal["contain", "cover", "stretch"] = "contain"


class CropOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["crop"]
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class TrimOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["trim"]
    fuzz: float = Field(default=0.0, ge=0)


class CompositeOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["composite"]
    path: str | None = None
    asset: str | None = None
    file: str | None = None
    gravity: str = "center"
    offset_x: int = 0
    offset_y: int = 0

    @model_validator(mode="after")
    def overlay_source(self) -> CompositeOp:
        if self.path and (self.asset or self.file):
            raise ValueError("use path or asset+file for overlay")
        if self.asset and not self.file:
            raise ValueError("composite asset requires file")
        if not self.path and not self.asset:
            raise ValueError("composite needs path or asset+file")
        return self


class QuantizeOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["quantize"]
    palette: Literal["style"] | None = "style"
    colors: int | None = Field(default=None, gt=0)
    dither: bool = True


class ConvertOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["convert"]
    format: Literal["png", "webp", "jpg"]


class HeightToNormalOp(BaseModel):
    """Turn a grayscale height PNG into a tangent-space normal."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["height_to_normal"]
    strength: float = Field(default=1.0, gt=0, le=8)


ImageOp = Annotated[
    ResizeOp | CropOp | TrimOp | CompositeOp | QuantizeOp
    | ConvertOp | HeightToNormalOp,
    Field(discriminator="op"),
]


class ImageExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["png", "webp", "jpg"] = "png"
    install_to: str | None = None


class ImageProcessSpec(ArtFields):
    """ImageMagick post-process of an existing raster."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["image_process"]
    id: str
    name: str
    style: str = "default"
    source: ImageSource
    operations: list[ImageOp] = Field(min_length=1)
    export: ImageExport = Field(default_factory=ImageExport)
    metadata: dict[str, str] = Field(default_factory=dict)


class SpriteFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_ms: int = Field(default=100, gt=0)
    layers: list[RasterLayer] = Field(min_length=1)


class SpriteAnimation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    loop: bool = True
    frames: list[SpriteFrame] = Field(min_length=1)


class SpriteExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    png: bool = True
    frames: bool = True
    aseprite: bool = True
    install_to: str | None = None


class SpriteSheetSpec(ArtFields):
    """Aseprite sprite sheet: named animations of timed frames."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["sprite_sheet"]
    id: str
    name: str
    canvas: PixelDimensions
    style: str = "default"
    animations: list[SpriteAnimation] = Field(min_length=1)
    master_frame: str | None = None
    export: SpriteExport = Field(default_factory=SpriteExport)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_animation_names(self) -> SpriteSheetSpec:
        names = [anim.name for anim in self.animations]
        if len(names) != len(set(names)):
            raise ValueError("animation names must be unique")
        return self


AssetSpec = Annotated[
    StaticPropSpec
    | LayeredRasterSpec
    | ImageProcessSpec
    | SpriteSheetSpec,
    Field(discriminator="type"),
]

_ASSET_ADAPTER: TypeAdapter[AssetSpec] = TypeAdapter(AssetSpec)


def parse_asset_spec(data: object) -> AssetSpec:
    """Validate a mapping as an AssetSpec. Returns the spec."""
    try:
        return _ASSET_ADAPTER.validate_python(data)
    except Exception as exc:
        raise MasonError(
            f"Invalid asset spec: {exc}",
            code="invalid_asset_spec",
        ) from exc


def load_asset_spec(path: Path) -> AssetSpec:
    """Parse an asset YAML file. Returns AssetSpec."""
    if not path.is_file():
        raise MasonError(
            f"Asset spec not found: {path}",
            code="spec_not_found",
            context={"path": str(path)},
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parse_asset_spec(data)


def dump_asset_spec(spec: AssetSpec, path: Path) -> None:
    """Write an asset spec as YAML."""
    data = spec.model_dump(mode="json", exclude_none=True)
    if not data.get("depends_on"):
        data.pop("depends_on", None)
    if not data.get("decomposition"):
        data.pop("decomposition", None)
    if not data.get("workflow"):
        data.pop("workflow", None)
    if not data.get("master_frame"):
        data.pop("master_frame", None)
    if not data.get("decals"):
        data.pop("decals", None)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )
