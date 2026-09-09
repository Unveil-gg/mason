"""Static-prop geometry: parts, recipes, and part ops."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mason.core.forms import (
    BodySpec,
    PartCurve,
    PartFollow,
    PartOutline,
    PartSkin,
    finalize_form_part,
)


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
    """A textured plane applied to a 3D prop.

    Set `face` to place it on one of the prop's own bounding-box
    faces: location, rotation, and size are then derived from the
    spec's top-level `dimensions` (a verified rotation per face, so
    the plane's world-space footprint always matches that face,
    never an axis-swapped or oversized guess). `inset` nudges it off
    the surface to avoid z-fighting. Faces sharing the +axis normal
    (top, front, right) read the source image unmirrored; back and
    left mirror horizontally, and bottom mirrors vertically -- an
    unavoidable consequence of viewing that face from the outside.
    Omit `face` to place the plane manually with location/rotation/
    size, as before.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    image: ImageSource
    face: Literal[
        "top", "bottom", "front", "back", "left", "right",
    ] | None = None
    inset: float = Field(default=0.0005, ge=0)
    location: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float] | None = None
    size: tuple[float, float] | None = None
    parent: str | None = None
    material: str = "primary"

    @model_validator(mode="after")
    def face_or_manual(self) -> DecalSpec:
        if self.face is not None:
            if self.location or self.rotation or self.size:
                raise ValueError(
                    "decal.face is exclusive with "
                    "location/rotation/size",
                )
            return self
        if self.location is None or self.size is None:
            raise ValueError(
                "decal needs face, or location and size",
            )
        if self.rotation is None:
            self.rotation = (1.5708, 0.0, 0.0)
        return self


class PartSnap(BaseModel):
    """Move this part so it meets a named face of another part."""

    model_config = ConfigDict(extra="forbid")

    to: str
    on: Literal["top", "bottom", "front", "back", "left", "right"]
    embed: float = Field(default=0.0, ge=0)


class PartCutout(BaseModel):
    """This part subtracts from `target`, then is discarded."""

    model_config = ConfigDict(extra="forbid")

    target: str


class PartBend(BaseModel):
    """Simple-deform bend applied after the primitive is built.

    General modeling op (necks, leaning posts, curved horns) -- not
    tied to any one subject. `angle` is radians. `origin: base`
    plants the min-Z end so the top leans.
    """

    model_config = ConfigDict(extra="forbid")

    axis: Literal["x", "y", "z"] = "x"
    angle: float = 0.0
    origin: Literal["center", "base"] = "center"


class PartDrape(BaseModel):
    """Hem flare: bend the free end away from `origin`.

    `amount` is radians. `origin: top` plants max-Z so the hem
    moves -- the start of cloth drape, not a sim.
    """

    model_config = ConfigDict(extra="forbid")

    axis: Literal["x", "y", "z"] = "x"
    amount: float = 0.08
    origin: Literal["center", "base", "top"] = "top"


class AttachSocket(BaseModel):
    """Named attach point exported as an EMPTY and in metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str
    location: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    parent: str | None = None


class PropPart(BaseModel):
    """One primitive or component instance in a static prop."""

    model_config = ConfigDict(extra="forbid")

    name: str
    shape: Literal[
        "box", "cylinder", "plane", "cone", "torus",
        "tapered_box", "sphere", "lathe",
        "curve", "skin", "outline",
    ] = "box"
    size: tuple[float, float, float] | None = None
    location: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    material: str = "primary"
    family: str | None = None
    wear: float = Field(default=0.0, ge=0, le=1)
    taper: tuple[float, float] | None = None
    profile: list[tuple[float, float]] | None = None
    segments: int = Field(default=24, ge=8, le=64)
    bend: PartBend | None = None
    drape: PartDrape | None = None
    curve: PartCurve | None = None
    skin: PartSkin | None = None
    outline: PartOutline | None = None
    follow: PartFollow | None = None
    helper: bool = False
    texture: ImageSource | None = None
    bump_map: ImageSource | None = None
    normal_map: ImageSource | None = None
    bevel: bool | None = None
    parent: str | None = None
    snap: PartSnap | None = None
    cutout: PartCutout | None = None
    inset: float = Field(default=0.0, ge=0)
    array: PartArray | None = None
    mirror: Literal["x", "y", "z"] | None = None
    component: Literal[
        "bolt", "hinge", "handle", "caster", "bracket", "trim",
        "x_brace", "rail", "wire_wall", "rivet_strip", "cornice",
    ] | None = None
    component_params: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def size_or_lathe(self) -> PropPart:
        if finalize_form_part(self):
            return self
        if self.profile is not None and self.shape != "lathe":
            raise ValueError("profile is only valid on shape: lathe")
        if self.shape == "lathe":
            if not self.profile or len(self.profile) < 2:
                raise ValueError(
                    "lathe needs profile with 2+ [radius, z] points",
                )
            for radius, _z in self.profile:
                if radius < 0:
                    raise ValueError("lathe radius must be >= 0")
            if self.size is None:
                radius = max(point[0] for point in self.profile)
                zs = [point[1] for point in self.profile]
                height = max(zs) - min(zs)
                self.size = (
                    max(2.0 * radius, 0.001),
                    max(2.0 * radius, 0.001),
                    height if height > 0 else 0.001,
                )
            return self
        if self.size is None:
            raise ValueError("part needs size")
        return self


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
    wing_width: float = Field(default=0.64, gt=0)
    tree_height: float = Field(default=1.0, gt=0)
    pool_width: float = Field(default=1.78, gt=0)
    pool_depth: float = Field(default=1.02, gt=0)


from mason.core.garment import GarmentSpec


class GeometrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bevel: bool = True
    bevel_width: float | None = None
    bevel_segments: int | None = None
    decimate: float | None = Field(default=None, gt=0, le=1)
    recipe: Literal[
        "crate", "shelf", "table", "hydrant", "cart",
        "house", "tree", "pool", "estate",
    ] | None = None
    recipe_params: RecipeParams = Field(default_factory=RecipeParams)
    parts: list[PropPart] = Field(default_factory=list)
    bodies: list[BodySpec] = Field(default_factory=list)
    garment: GarmentSpec | None = None

    @model_validator(mode="after")
    def require_parts_or_recipe(self) -> GeometrySpec:
        if (
            not self.parts
            and self.recipe is None
            and self.garment is None
        ):
            raise ValueError(
                "geometry needs parts, a recipe, or garment",
            )
        return self


class Dimensions3D(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    height: float = Field(gt=0)
