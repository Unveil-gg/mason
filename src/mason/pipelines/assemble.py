"""Compile a decomposition graph into instance parts and build."""

from __future__ import annotations

from pathlib import Path

from mason.core.assets import StaticPropSpec, dump_asset_spec
from mason.core.decompose import Decomposition, Joint
from mason.core.jobs import AssetJob, require_job
from mason.core.parts import ImageSource, PropPart
from mason.core.paths import resolve_image_source
from mason.core.workspace import find_project_root
from mason.errors import MasonError


def needs_assembly_deps(spec: StaticPropSpec) -> bool:
    """True when build must wait on accepted component jobs."""
    if spec.decomposition and spec.decomposition.mode == "assets":
        return True
    return any(part.shape == "instance" for part in spec.geometry.parts)


def assembly_asset_ids(spec: StaticPropSpec) -> list[str]:
    """Unique component job ids this spec instances."""
    found: list[str] = []
    if spec.decomposition:
        found.extend(spec.decomposition.asset_ids())
    for part in spec.geometry.parts:
        if part.shape != "instance" or not part.source:
            continue
        if part.source.asset and part.source.asset not in found:
            found.append(part.source.asset)
    return found


def resolve_component_glb(root: Path, asset_id: str) -> Path:
    """Prefer current_best GLB so rejects never enter an assembly."""
    job = AssetJob(root, asset_id)
    meta = job.load_meta()
    best = meta.current_best if meta else None
    if best:
        snap = job.iterations / f"{best:03d}" / "output" / "asset.glb"
        if snap.is_file():
            return snap
    live = job.output / "asset.glb"
    if live.is_file():
        return live
    raise MasonError(
        f"No assembled GLB for component '{asset_id}'.",
        code="component_glb_missing",
        hint="Build and evaluate the component first.",
        context={"asset_id": asset_id},
    )


def assert_assembly_deps(spec: StaticPropSpec, root: Path) -> None:
    """Fail if an instanced component has no accepted current_best."""
    if not needs_assembly_deps(spec):
        return
    for asset_id in assembly_asset_ids(spec):
        job = AssetJob(root, asset_id)
        if not job.exists():
            raise MasonError(
                f"Component job '{asset_id}' is missing.",
                code="component_missing",
                hint="Build and evaluate each unique component first.",
                context={"asset_id": asset_id},
            )
        meta = job.load_meta()
        if meta is None or meta.current_best is None:
            raise MasonError(
                f"Component '{asset_id}' has no current_best.",
                code="component_not_accepted",
                hint="Evaluate the component against its isolate.",
                context={"asset_id": asset_id},
            )
        resolve_component_glb(root, asset_id)


def resolve_instance_paths(
    job: AssetJob, parts: list[PropPart],
) -> dict[str, str]:
    """Map instance part names to accepted component GLB paths."""
    found: dict[str, str] = {}
    for part in parts:
        if part.shape != "instance" or not part.source:
            continue
        if part.source.asset:
            path = resolve_component_glb(job.project_root, part.source.asset)
        else:
            path = resolve_image_source(part.source, job.project_root)
        if not path.is_file():
            raise MasonError(
                f"Instance source for '{part.name}' not found: {path}",
                code="instance_missing",
                context={"part": part.name, "path": str(path)},
            )
        found[part.name] = str(path)
    return found


def compile_assembly(graph: Decomposition) -> list[PropPart]:
    """Expand joints into shape:instance parts. Reuses instance_of."""
    parts: list[PropPart] = []
    for joint in graph.joints:
        source = graph.source_component(joint.child)
        if source is None or not source.asset:
            raise MasonError(
                f"Joint '{joint.child}' has no source asset.",
                code="joint_no_asset",
                context={"child": joint.child},
            )
        size = _component_size(source)
        placements = _joint_placements(joint)
        for name, location, rotation, mirror in placements:
            parts.append(PropPart(
                name=name,
                shape="instance",
                source=ImageSource(
                    asset=source.asset, file="output/asset.glb",
                ),
                size=size,
                location=location,
                rotation=rotation,
                parent=joint.parent,
                mirror=mirror,
            ))
    return parts


def apply_assembly(spec: StaticPropSpec) -> StaticPropSpec:
    """Write compiled instance parts onto an assets-mode spec."""
    graph = spec.decomposition
    if graph is None:
        raise MasonError(
            "assemble needs a decomposition graph.",
            code="decomposition_missing",
            hint="mason decompose <id> <graph.yaml>",
        )
    if graph.mode == "assets":
        spec.geometry.parts = compile_assembly(graph)
        spec.depends_on = list(dict.fromkeys(
            [*spec.depends_on, *graph.asset_ids()],
        ))
    return spec


def run_assemble(asset_id: str):
    """Compile the graph, persist, and rebuild the parent job."""
    root = find_project_root()
    job = require_job(root, asset_id)
    spec = job.load_spec()
    if spec.type != "static_prop":
        raise MasonError(
            "assemble only applies to static_prop.",
            code="assemble_not_prop",
        )
    spec = apply_assembly(spec)
    assert_assembly_deps(spec, root)
    job.write_spec(spec)
    job.write_art_sidecars(spec)
    meta = job.load_meta()
    if meta and meta.source_spec:
        dest = root / meta.source_spec
        dest.parent.mkdir(parents=True, exist_ok=True)
        dump_asset_spec(spec, dest)
    from mason.pipelines.dispatch import run_rebuild
    return run_rebuild(asset_id)


def _component_size(component) -> tuple[float, float, float]:
    dims = component.dimensions
    if dims is None:
        return (1.0, 1.0, 1.0)
    return (dims.width, dims.depth, dims.height)


def _joint_placements(
    joint: Joint,
) -> list[tuple[
    str,
    tuple[float, float, float],
    tuple[float, float, float],
    str | None,
]]:
    """Name, location, rotation, mirror for the joint and copies."""
    first = (
        joint.parent_socket or joint.child,
        joint.location,
        joint.rotation,
        None,
    )
    rows = [first]
    for index, copy in enumerate(joint.copies, start=1):
        name = copy.parent_socket or f"{joint.child}_{index}"
        rows.append((
            name,
            copy.location if copy.location is not None else joint.location,
            copy.rotation if copy.rotation is not None else joint.rotation,
            copy.mirror,
        ))
    return rows
