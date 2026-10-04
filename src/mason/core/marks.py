"""Semantic 2D marks. Each one bakes to a list of dabs."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarkRect(BaseModel):
    """Pixel rect a wash, scatter, hatch, or mass fills."""

    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class MarkBase(BaseModel):
    """Shared hand knobs. Unset means style process, or 0."""

    model_config = ConfigDict(extra="forbid")

    hand: bool = False
    jitter: float | None = Field(default=None, ge=0, le=1)
    density: float | None = Field(default=None, ge=0, le=1)
    irregularity: float | None = Field(default=None, ge=0, le=1)
    overlap: float | None = Field(default=None, ge=0, le=1)
    strength: float | None = Field(default=None, ge=0, le=1)


class DabMark(MarkBase):
    """One disc."""

    kind: Literal["dab"]
    at: tuple[float, float]
    radius: float = Field(gt=0)


class StrokeMark(MarkBase):
    """Polyline of dabs with one radius."""

    kind: Literal["stroke"]
    points: list[tuple[float, float]] = Field(min_length=2)
    radius: float = Field(default=6.0, gt=0)
    spacing: float = Field(default=0.45, gt=0, le=2)


class StrokePathMark(MarkBase):
    """Polyline whose width changes along the path."""

    kind: Literal["stroke_path"]
    points: list[tuple[float, float]] = Field(min_length=2)
    radius: float = Field(default=6.0, gt=0)
    radius_end: float | None = Field(default=None, gt=0)
    spacing: float = Field(default=0.45, gt=0, le=2)


class WashMark(MarkBase):
    """Soft field of large dabs inside a rect."""

    kind: Literal["wash"]
    rect: MarkRect
    shape: Literal["rect", "ellipse"] = "rect"


class ScatterMark(MarkBase):
    """Seeded discs inside a rect."""

    kind: Literal["scatter"]
    rect: MarkRect
    count: int = Field(ge=1, le=400)
    radius: float = Field(gt=0)


class HatchMark(MarkBase):
    """Parallel strokes across a rect."""

    kind: Literal["hatch"]
    rect: MarkRect
    angle: float = 0.0
    count: int | None = Field(default=None, ge=1, le=64)


class MassMark(MarkBase):
    """Packed body plus a ragged contour."""

    kind: Literal["mass"]
    rect: MarkRect | None = None
    points: list[tuple[float, float]] | None = None

    @model_validator(mode="after")
    def need_region(self) -> MassMark:
        if self.points and len(self.points) >= 3:
            return self
        if self.rect is None:
            raise ValueError("mass needs rect or 3+ points")
        return self


Mark = Annotated[
    DabMark
    | StrokeMark
    | StrokePathMark
    | WashMark
    | ScatterMark
    | HatchMark
    | MassMark,
    Field(discriminator="kind"),
]
