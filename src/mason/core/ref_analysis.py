"""Measured multi-view reference facts. Not compiled into meshes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ImageLandmark(BaseModel):
    """Semantic point in a reference, in subject-bbox UV (0..1)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    uv: tuple[float, float]
    role: str = ""


class WidthSample(BaseModel):
    """Subject width at a normalized height (0 = bottom)."""

    model_config = ConfigDict(extra="forbid")

    t: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)


class ReferenceView(BaseModel):
    """One reference image used as a geometric constraint."""

    model_config = ConfigDict(extra="forbid")

    view: str
    path: str = ""
    purpose: str = "silhouette"
    component: str | None = None
    height_width_ratio: float = 1.0
    contour: list[tuple[float, float]] = Field(default_factory=list)
    profile: list[tuple[float, float]] = Field(default_factory=list)
    com: tuple[float, float] | None = None
    widths: list[WidthSample] = Field(default_factory=list)
    landmarks: list[ImageLandmark] = Field(default_factory=list)
    negative_space: str = ""
    curves: str = ""


class ReferenceAnalysis(BaseModel):
    """Reference-conditioned brief written before / during modeling."""

    model_config = ConfigDict(extra="forbid")

    views: list[ReferenceView] = Field(default_factory=list)
    defining_silhouette: str = ""
    primary_masses: list[str] = Field(default_factory=list)
    proportions: str = ""
    style: str = ""
    abstraction: str = ""
    notes: list[str] = Field(default_factory=list)
