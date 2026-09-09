"""Garment fit spec: template, GLB-fit, and refit modes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mason.core.parts import ImageSource


class GarmentSpec(BaseModel):
    """Body-first clothing. Not compiled from box parts."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["template", "fit", "refit"] = "template"
    kind: Literal["shirt", "tunic", "vest"] = "shirt"
    body: ImageSource | None = None
    source: ImageSource | None = None
    archetype: Literal["small_animal"] = "small_animal"
    fit: Literal["fitted", "loose"] = "fitted"
    clearance: float = Field(default=0.012, ge=0.0, le=0.08)
    thickness: float = Field(default=0.004, gt=0.0, le=0.03)
    hem: float = Field(default=0.22, ge=0.0)
    sleeve: Literal["none", "short"] = "short"
    neck: float = Field(default=0.14, gt=0.0, le=0.4)
    tail_opening: bool = False
    stylization: float = Field(default=0.7, ge=0.0, le=1.0)
    stiffness: float = Field(default=0.6, ge=0.0, le=1.0)
    wrinkle: float = Field(default=0.2, ge=0.0, le=1.0)
    cloth_frames: int = Field(default=8, ge=0, le=24)
    pose_tests: bool = True

    @model_validator(mode="after")
    def mode_sources(self) -> GarmentSpec:
        if self.mode == "fit" and self.body is None:
            raise ValueError("garment.mode fit needs body")
        if self.mode == "refit":
            if self.body is None or self.source is None:
                raise ValueError("garment.mode refit needs body and source")
        if self.kind == "vest":
            self.sleeve = "none"
        return self
