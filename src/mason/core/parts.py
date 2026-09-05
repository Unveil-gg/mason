"""Static-prop geometry: parts, recipes, and part ops."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImageSource(BaseModel):
    """A reference to a PNG: either a literal project path, or another
    asset's built output (asset id + file, e.g. "output/asset.png")."""

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


class PartArray(BaseModel):
    """Linear copies of a part along an offset."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=2)
    offset: tuple[float, float, float]


class PropPart(BaseModel):
    """One primitive in a static prop (box, cylinder, or plane)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    shape: Literal["box", "cylinder", "plane"] = "box"
    size: tuple[float, float, float]
    location: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    material: str = "primary"
    texture: ImageSource | None = None
    bevel: bool | None = None
    parent: str | None = None
    inset: float = Field(default=0.0, ge=0)
    array: PartArray | None = None


class RecipeParams(BaseModel):
    """Optional parameters for crate/shelf/table expanders."""

    model_config = ConfigDict(extra="forbid")

    board_thickness: float = Field(default=0.03, gt=0)
    shelf_count: int = Field(default=4, ge=1)
    side_panels: bool = True
    back_panel: bool = False
    leg_thickness: float = Field(default=0.06, gt=0)


class GeometrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bevel: bool = True
    bevel_width: float | None = None
    bevel_segments: int | None = None
    recipe: Literal["crate", "shelf", "table"] | None = None
    recipe_params: RecipeParams = Field(default_factory=RecipeParams)
    parts: list[PropPart] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_parts_or_recipe(self) -> GeometrySpec:
        if not self.parts and self.recipe is None:
            raise ValueError("geometry needs parts or a recipe")
        return self


class Dimensions3D(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    height: float = Field(gt=0)
