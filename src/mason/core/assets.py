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

from mason.core.parts import (  # noqa: F401
    Dimensions3D,
    GeometrySpec,
    PartArray,
    PropPart,
    RecipeParams,
)
from mason.errors import MasonError


class PixelDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(gt=0)
    height: int = Field(gt=0)


class Export3D(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["glb"] = "glb"
    save_blend: bool = True


class MaterialsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = "primary"
    roughness: float | None = None
    metallic: float | None = None


class StaticPropSpec(BaseModel):
    """Procedural 3D prop built from primitive parts."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["static_prop"]
    id: str
    name: str
    dimensions: Dimensions3D
    style: str = "default"
    geometry: GeometrySpec
    materials: MaterialsSpec = Field(default_factory=MaterialsSpec)
    export: Export3D = Field(default_factory=Export3D)
    metadata: dict[str, str] = Field(default_factory=dict)


class LayerRect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class RasterLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: Literal[
        "background", "fill", "text", "image", "overlay",
    ] | None = None
    fill: str | None = None
    rect: LayerRect | None = None
    text: str | None = None
    font_size: int = Field(default=48, gt=0)
    image: str | None = None

    @model_validator(mode="after")
    def need_content(self) -> RasterLayer:
        if not self.fill and not self.text and not self.image:
            raise ValueError("layer needs fill, text, or image")
        return self


class RasterExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kra: bool = True
    png: bool = True


class LayeredRasterSpec(BaseModel):
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


class ImageSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: str | None = None
    file: str | None = None
    path: str | None = None

    @model_validator(mode="after")
    def one_source(self) -> ImageSource:
        if self.path:
            if self.asset or self.file:
                raise ValueError("use path or asset+file, not both")
            return self
        if self.asset and self.file:
            return self
        raise ValueError("source needs path or asset+file")


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


ImageOp = Annotated[
    ResizeOp | CropOp | TrimOp | CompositeOp | QuantizeOp | ConvertOp,
    Field(discriminator="op"),
]


class ImageExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["png", "webp", "jpg"] = "png"


class ImageProcessSpec(BaseModel):
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


AssetSpec = Annotated[
    StaticPropSpec | LayeredRasterSpec | ImageProcessSpec,
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
    path.write_text(
        yaml.safe_dump(
            spec.model_dump(mode="json"),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
