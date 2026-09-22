"""Join static parts and bake one atlas at GLB export."""

PROP_PACK_SRC = r'''
import math

import mathutils
import numpy as np


def _mesh_objects():
    """Exported meshes, skipping helper objects."""
    return [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and not obj.name.startswith("_mason_")
    ]


def _part_objects(name):
    """Object plus array copies (`name_2`) and mirrors (`name_m`)."""
    found = []
    prefix = name + "_"
    for obj in _mesh_objects():
        if obj.name == name or obj.name == name + "_m":
            found.append(obj)
            continue
        if not obj.name.startswith(prefix):
            continue
        rest = obj.name[len(prefix):]
        stem = rest[:-2] if rest.endswith("_m") else rest
        if stem.isdigit():
            found.append(obj)
    return found


def _under_mover(obj, names):
    """True when obj or an ancestor is a mover root."""
    cur = obj
    while cur is not None:
        if cur.name in names:
            return True
        cur = cur.parent
    return False


def _world_aabb(objects):
    """World AABB of mesh objects. Returns (min, max) or None."""
    mins = [1e9, 1e9, 1e9]
    maxs = [-1e9, -1e9, -1e9]
    count = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        count += 1
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for axis in range(3):
                mins[axis] = min(mins[axis], world[axis])
                maxs[axis] = max(maxs[axis], world[axis])
    if count == 0:
        return None
    return mins, maxs


def emit_export_volumes():
    """EMPTY hulls with mason_min/max extras. Call before joins."""
    specs = CONFIG.get("export_volumes") or []
    movers = set(CONFIG.get("export_movers") or [])
    for spec in specs:
        name = str(spec.get("name") or "volume")
        if bpy.data.objects.get(name) is not None:
            continue
        if spec.get("min") and spec.get("max"):
            bounds = (list(spec["min"]), list(spec["max"]))
        else:
            parts = spec.get("parts") or []
            if parts:
                objs = []
                for part in parts:
                    objs.extend(_part_objects(part))
            else:
                objs = [
                    obj for obj in _mesh_objects()
                    if not _under_mover(obj, movers)
                ]
            bounds = _world_aabb(objs)
        if bounds is None:
            continue
        mins, maxs = bounds
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "CUBE"
        empty.empty_display_size = 0.05
        empty.location = [
            (mins[i] + maxs[i]) * 0.5 for i in range(3)
        ]
        empty["mason_kind"] = spec.get("kind") or "box"
        empty["mason_min"] = [float(v) for v in mins]
        empty["mason_max"] = [float(v) for v in maxs]
        bpy.context.collection.objects.link(empty)


def _descendants(root):
    """Mesh descendants, not the root itself."""
    found = []

    def walk(obj):
        for child in obj.children:
            if (
                child.type == "MESH"
                and not child.name.startswith("_mason_")
            ):
                found.append(child)
            walk(child)

    walk(root)
    return found


def _keep_world(obj, parent):
    """Reparent without moving the object in world space."""
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def _join_into(active, others):
    """Join mesh objects into active. Active origin is kept."""
    others = [
        obj for obj in others
        if obj.type == "MESH" and obj != active
    ]
    if not others or active is None or active.type != "MESH":
        return active
    for obj in others:
        _keep_world(obj, None)
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass
    bpy.ops.object.select_all(action="DESELECT")
    for obj in others:
        obj.hide_set(False)
        obj.select_set(True)
    active.hide_set(False)
    active.select_set(True)
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.join()
    return active


def _reparent_empties(root, kids):
    """Keep sockets on the mover root when children are joined away."""
    kid_set = set(kids)
    for obj in list(bpy.data.objects):
        if obj.type != "EMPTY" or obj.parent not in kid_set:
            continue
        _keep_world(obj, root if root.type == "MESH" else None)


def _join_prop_meshes():
    """One mesh per mover root, plus a single static body."""
    movers = list(CONFIG.get("export_movers") or [])
    protected = set()
    for name in movers:
        root = bpy.data.objects.get(name)
        if root is None:
            continue
        kids = _descendants(root)
        _reparent_empties(root, kids)
        if root.type == "MESH":
            _join_into(root, kids)
            protected.add(root.name)
        elif kids:
            host = kids[0]
            _join_into(host, kids[1:])
            _keep_world(host, root)
            protected.add(host.name)
    statics = [
        obj for obj in _mesh_objects() if obj.name not in protected
    ]
    if not statics:
        return
    if len(statics) == 1:
        statics[0].name = "body"
        return
    host = next(
        (obj for obj in statics if obj.name == "cabinet"), statics[0],
    )
    _join_into(host, statics)
    host.name = "body"


def _capture_part_bounds():
    """Remember per-part AABBs so touch checks survive the join."""
    global PART_BOUNDS
    captured = {}
    for obj in _mesh_objects():
        omins = [1e9, 1e9, 1e9]
        omaxs = [-1e9, -1e9, -1e9]
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for axis in range(3):
                omins[axis] = min(omins[axis], world[axis])
                omaxs[axis] = max(omaxs[axis], world[axis])
        captured[obj.name] = {"min": omins, "max": omaxs}
    PART_BOUNDS = captured


def pack_prop_for_export():
    """Merge statics, keep mover roots, bake one atlas.

    Authoring stays in the .blend. This runs only inside export_glb.
    """
    _capture_part_bounds()
    emit_export_volumes()
    _join_prop_meshes()
    flatten_materials_for_gltf()
    _bake_prop_atlas()
'''
