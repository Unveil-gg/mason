"""Deterministic draws keyed by name, not a shared stream."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def unit(
    seed: int,
    name: str,
    index: int = 0,
    channel: int = 0,
) -> float:
    """Return a float in [0, 1) for this key.

    seed: asset seed. name: layer or part. index: copy or dab.
    channel: which draw on that dab. Same inputs always match.
    """
    name_hash = 0xCBF29CE484222325
    for byte in name.encode("utf-8"):
        name_hash ^= byte
        name_hash = (name_hash * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    mixed = (seed & 0xFFFFFFFFFFFFFFFF) ^ name_hash
    mixed ^= (index & 0xFFFFFFFF) * 0x9E3779B97F4A7C15
    mixed ^= (channel & 0xFFFF) * 0xBF58476D1CE4E5B9
    mixed = _mix64(mixed)
    return (mixed >> 11) / float(1 << 53)


def signed(
    seed: int,
    name: str,
    index: int = 0,
    channel: int = 0,
) -> float:
    """Return a float in [-1, 1) for this key."""
    return unit(seed, name, index, channel) * 2.0 - 1.0


def _mix64(value: int) -> int:
    """SplitMix64 finalizer. Returns a 64-bit int."""
    value &= 0xFFFFFFFFFFFFFFFF
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9
    value &= 0xFFFFFFFFFFFFFFFF
    value = (value ^ (value >> 27)) * 0x94D049BB133111EB
    value &= 0xFFFFFFFFFFFFFFFF
    return value ^ (value >> 31)


class PartVary(BaseModel):
    """Opt-in construction ranges. Empty uses the style hand."""

    model_config = ConfigDict(extra="forbid")

    scale: float | None = Field(default=None, ge=0, le=1)
    rotation: float | None = Field(default=None, ge=0, le=0.5)
    spacing: float | None = Field(default=None, ge=0, le=1)
    bevel: float | None = Field(default=None, ge=0, le=1)
    silhouette: float | None = Field(default=None, ge=0, le=1)
    axis: Literal["x", "y", "z"] = "z"
    breakup: float | None = Field(default=None, ge=0, le=1)
    breakup_count: int | None = Field(default=None, ge=0, le=24)
    material: float | None = Field(default=None, ge=0, le=1)
    face: Literal[
        "top", "bottom", "front", "back", "left", "right",
    ] = "top"
