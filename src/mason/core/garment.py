"""Garment IR: body-first clothing planned before geometry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mason.core.parts import ImageSource

FitEase = Literal[
    "skin_tight", "fitted", "regular", "loose", "oversized",
]
GarmentKind = Literal["shirt", "tunic", "vest", "hoodie"]

_KIND_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "shirt": {
        "body_regions": ["torso", "upper_arms"],
        "anchors": [
            "neck", "shoulder_left", "shoulder_right", "waist",
        ],
        "panels": [
            "front", "back", "sleeve_left", "sleeve_right",
        ],
        "openings": [
            "neck", "waist", "wrist_left", "wrist_right",
        ],
        "details": ["collar", "cuffs", "hem", "placket", "buttons"],
    },
    "tunic": {
        "body_regions": ["torso", "upper_arms"],
        "anchors": ["neck", "shoulder_left", "shoulder_right", "hips"],
        "panels": ["front", "back", "sleeve_left", "sleeve_right"],
        "openings": ["neck", "waist", "wrist_left", "wrist_right"],
        "details": ["collar", "cuffs", "hem"],
    },
    "vest": {
        "body_regions": ["torso"],
        "anchors": ["neck", "shoulder_left", "shoulder_right", "waist"],
        "panels": ["front", "back"],
        "openings": ["neck", "waist", "arm_left", "arm_right"],
        "details": ["hem", "armholes"],
    },
    "hoodie": {
        "body_regions": ["torso", "upper_arms"],
        "anchors": [
            "neck", "shoulder_left", "shoulder_right",
            "wrist_left", "wrist_right", "waist",
        ],
        "panels": [
            "front", "back", "sleeve_left", "sleeve_right", "hood",
        ],
        "openings": [
            "neck", "waist", "wrist_left", "wrist_right",
        ],
        "details": ["hood", "cuffs", "waistband"],
    },
}


class GarmentSpec(BaseModel):
    """Intent for a garment built around a character body."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["template", "fit", "refit"] = "template"
    kind: GarmentKind = "shirt"
    body: ImageSource | None = None
    source: ImageSource | None = None
    archetype: Literal["small_animal"] = "small_animal"
    fit: FitEase = "fitted"
    body_regions: list[str] = Field(default_factory=list)
    anchors: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    openings: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)
    fabric_weight: Literal["thin", "medium", "thick"] = "medium"
    clearance: float = Field(default=0.012, ge=0.0, le=0.08)
    thickness: float = Field(default=0.004, gt=0.0, le=0.03)
    hem: float = Field(default=0.22, ge=0.0)
    sleeve: Literal["none", "short", "long"] = "short"
    neck: float = Field(default=0.14, gt=0.0, le=0.4)
    tail_opening: bool = False
    hide_covered: bool = False
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
        if self.kind == "hoodie" and self.sleeve == "short":
            self.sleeve = "long"
        defaults = _KIND_DEFAULTS[self.kind]
        for key, values in defaults.items():
            if not getattr(self, key):
                setattr(self, key, list(values))
        return self
