"""Semantic decomposition and assembly graph. Intent plus compile."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IsolateRef(BaseModel):
    """Isolated 2D reference for one component."""

    model_config = ConfigDict(extra="forbid")

    path: str
    view: str = "three_quarter"


class ComponentSize(BaseModel):
    """Local bounds of one component, in world units."""

    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    height: float = Field(gt=0)


class DecompComponent(BaseModel):
    """One semantic component. Unique geometry, or an instance alias."""

    model_config = ConfigDict(extra="forbid")

    id: str
    role: Literal["primary", "secondary", "tertiary"] = "primary"
    technique: Literal[
        "lathe", "box", "curve", "outline", "skin",
        "modular", "remesh", "refine", "sculpt", "fit",
    ] = "box"
    asset: str | None = None
    instance_of: str | None = None
    isolate: IsolateRef | None = None
    origin: tuple[float, float, float] | None = None
    dimensions: ComponentSize | None = None


class JointCopy(BaseModel):
    """One extra placement of a joint's child."""

    model_config = ConfigDict(extra="forbid")

    parent_socket: str | None = None
    location: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float] | None = None
    mirror: Literal["x", "y", "z"] | None = None


class Joint(BaseModel):
    """Parent/child attach. Copies instance the same child asset."""

    model_config = ConfigDict(extra="forbid")

    child: str
    parent: str | None = None
    socket: str | None = None
    parent_socket: str | None = None
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    copies: list[JointCopy] = Field(default_factory=list)


class Decomposition(BaseModel):
    """Agent-authored decompose graph. Compiled by mason assemble."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["parts", "assets"] = "parts"
    source_views: list[str] = Field(default_factory=list)
    components: list[DecompComponent] = Field(default_factory=list)
    joints: list[Joint] = Field(default_factory=list)

    @model_validator(mode="after")
    def graph_is_consistent(self) -> Decomposition:
        ids = [row.id for row in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("decomposition component ids must be unique")
        known = set(ids)
        for row in self.components:
            alias = row.instance_of
            if alias and alias not in known:
                raise ValueError(
                    f"instance_of '{alias}' is not a component",
                )
            if self.mode == "assets":
                source = self.component(alias or row.id)
                if source is None or not source.asset:
                    raise ValueError(
                        f"assets mode needs asset on '{alias or row.id}'",
                    )
        for joint in self.joints:
            if joint.child not in known:
                raise ValueError(
                    f"joint child '{joint.child}' is not a component",
                )
            if joint.parent and joint.parent not in known:
                raise ValueError(
                    f"joint parent '{joint.parent}' is not a component",
                )
        return self

    def component(self, component_id: str) -> DecompComponent | None:
        """Return the named component, or None."""
        for row in self.components:
            if row.id == component_id:
                return row
        return None

    def source_component(
        self, component_id: str,
    ) -> DecompComponent | None:
        """Resolve instance_of to the unique geometry component."""
        row = self.component(component_id)
        if row is None:
            return None
        if row.instance_of and row.instance_of != row.id:
            return self.component(row.instance_of)
        return row

    def asset_ids(self) -> list[str]:
        """Unique component job ids in assets mode."""
        found: list[str] = []
        for row in self.components:
            source = self.source_component(row.id)
            if source is None or not source.asset:
                continue
            if source.asset not in found:
                found.append(source.asset)
        return found
