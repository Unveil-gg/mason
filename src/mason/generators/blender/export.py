"""Blender source snippets for export and metadata."""

EXPORT_SRC = r'''
def export_glb(path):
    """Export visible mesh objects as a GLB. Skip _mason_ helpers."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.startswith("_mason_"):
            continue
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
    )


def save_blend(path):
    """Save the current file as a .blend, replacing any previous file.

    Blender saves via a `<path>@` temp file then renames it; a stale
    leftover (from an interrupted save, or a locking AV/indexer) makes
    the rename fail with "Cannot change old file". Clear both before
    saving.
    """
    for candidate in (path, path + "@"):
        if os.path.isfile(candidate):
            os.remove(candidate)
    bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)


def scene_bounds():
    """World-space AABB of all mesh objects. Returns (mins, maxs)."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.startswith("_mason_"):
            continue
        count += 1
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, world.x)
            mins.y = min(mins.y, world.y)
            mins.z = min(mins.z, world.z)
            maxs.x = max(maxs.x, world.x)
            maxs.y = max(maxs.y, world.y)
            maxs.z = max(maxs.z, world.z)
    if count == 0:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return mins, maxs


def write_metadata(path):
    """Write mesh stats JSON next to outputs."""
    meshes = [
        o for o in bpy.data.objects
        if o.type == "MESH" and not o.name.startswith("_mason_")
    ]
    triangles = 0
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
    mins, maxs = scene_bounds()
    size = maxs - mins
    object_bounds = {}
    for obj in meshes:
        omins = Vector((1e9, 1e9, 1e9))
        omaxs = Vector((-1e9, -1e9, -1e9))
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            omins.x = min(omins.x, world.x)
            omins.y = min(omins.y, world.y)
            omins.z = min(omins.z, world.z)
            omaxs.x = max(omaxs.x, world.x)
            omaxs.y = max(omaxs.y, world.y)
            omaxs.z = max(omaxs.z, world.z)
        object_bounds[obj.name] = {
            "min": [float(omins.x), float(omins.y), float(omins.z)],
            "max": [float(omaxs.x), float(omaxs.y), float(omaxs.z)],
        }
    payload = {
        "objects": [o.name for o in meshes],
        "mesh_count": len(meshes),
        "material_count": len(bpy.data.materials),
        "triangles": triangles,
        "bounds": {
            "x": float(size.x),
            "y": float(size.y),
            "z": float(size.z),
            "min": [float(mins.x), float(mins.y), float(mins.z)],
            "max": [float(maxs.x), float(maxs.y), float(maxs.z)],
        },
        "object_bounds": object_bounds,
        "scales": {
            o.name: [float(s) for s in o.scale] for o in meshes
        },
        "preview_engine": CONFIG.get("preview_engine"),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
'''
