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


class RadialArray(BaseModel):
    """Copies around an axis. Location is the ring center."""

    model_config = ConfigDict(extra="forbid")

    radius: float = Field(gt=0)
    axis: Literal["x", "y", "z"] = "z"
    start_angle: float = 0.0


class PartArray(BaseModel):
    """Linear copies, or a radial ring when `radial` is set."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=2)
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radial: RadialArray | None = None


class DecalSpec(BaseModel):
    """A textured plane applied to a 3D prop."""

    model_config = ConfigDict(extra="forbid")

    name: str
    image: ImageSource
    location: tuple[float, float, float]
    rotation: tuple[float, float, float] = (1.5708, 0.0, 0.0)
    size: tuple[float, float]
    parent: str | None = None
    material: str = "primary"


class PartSnap(BaseModel):
    """Move this part so it meets a named face of another part."""

    model_config = ConfigDict(extra="forbid")

    to: str
    on: Literal["top", "bottom", "front", "back", "left", "right"]
    embed: float = Field(default=0.0, ge=0)


class PropPart(BaseModel):
    """One primitive or component instance in a static prop."""

    model_config = ConfigDict(extra="forbid")

    name: str
    shape: Literal[
        "box", "cylinder", "plane", "cone", "torus",
        "tapered_box", "sphere",
    ] = "box"
    size: tuple[float, float, float]
    location: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    material: str = "primary"
    family: str | None = None
    wear: float = Field(default=0.0, ge=0, le=1)
    taper: tuple[float, float] | None = None
    texture: ImageSource | None = None
    bevel: bool | None = None
    parent: str | None = None
    snap: PartSnap | None = None
    inset: float = Field(default=0.0, ge=0)
    array: PartArray | None = None
    mirror: Literal["x", "y", "z"] | None = None
    component: Literal[
        "bolt", "hinge", "handle", "caster", "bracket", "trim",
        "x_brace", "rail", "wire_wall", "rivet_strip", "cornice",
    ] | None = None
    component_params: dict[str, float] = Field(default_factory=dict)


class RecipeParams(BaseModel):
    """Optional parameters for recipe expanders."""

    model_config = ConfigDict(extra="forbid")

    board_thickness: float = Field(default=0.03, gt=0)
    shelf_count: int = Field(default=4, ge=1)
    side_panels: bool = True
    back_panel: bool = False
    leg_thickness: float = Field(default=0.06, gt=0)
    body_radius: float = Field(default=0.11, gt=0)
    body_height: float = Field(default=0.42, gt=0)
    cap_count: int = Field(default=2, ge=1, le=3)
    bolt_count: int = Field(default=6, ge=3)
    flare: float = Field(default=0.18, ge=0, le=0.6)
    basket_height: float = Field(default=0.42, gt=0)
    handle_rise: float = Field(default=0.16, gt=0)


class GeometrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bevel: bool = True
    bevel_width: float | None = None
    bevel_segments: int | None = None
    recipe: Literal[
        "crate", "shelf", "table", "hydrant", "cart",
    ] | None = None
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
