"""Geometric planning: masses, landmarks, and quality stages.

Intent only -- not compiled into meshes. Agents bind landmarks to
skin nodes / curve points so critiques can name a control to move.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QUALITY_STAGES = (
    "blockout",
    "silhouette",
    "secondary",
    "tertiary",
    "material",
    "final",
)

QualityStage = Literal[
    "blockout",
    "silhouette",
    "secondary",
    "tertiary",
    "material",
    "final",
]


class Landmark(BaseModel):
    """One semantic control. Prefer a part+node over a raw vertex."""

    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    part: str | None = None
    node: str | None = None
    at: tuple[float, float, float] | None = None
    notes: str = ""


class MassNote(BaseModel):
    """One primary or connecting volume."""

    model_config = ConfigDict(extra="forbid")

    name: str
    role: Literal["primary", "secondary", "join"] = "primary"
    connects_to: list[str] = Field(default_factory=list)
    notes: str = ""


class GeometricPlan(BaseModel):
    """Form analysis written before parts. Not compiled."""

    model_config = ConfigDict(extra="forbid")

    primary_read: str = ""
    recognition: Literal[
        "silhouette", "proportion", "detail", "material", "mixed",
    ] = "mixed"
    must_survive_small: list[str] = Field(default_factory=list)
    masses: list[MassNote] = Field(default_factory=list)
    silhouette: str = ""
    silhouette_vs_similar: str = ""
    proportions: str = ""
    symmetry: Literal[
        "rotational", "bilateral", "asymmetric", "local",
    ] = "bilateral"
    negative_space: str = ""
    abstraction: str = ""
    landmarks: list[Landmark] = Field(default_factory=list)
    stage: QualityStage = "blockout"
    notes: list[str] = Field(default_factory=list)
