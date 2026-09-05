"""Blender source snippets for export and metadata."""

EXPORT_SRC = r'''
def export_glb(path):
    """Export the scene as a GLB file."""
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=False,
    )


def save_blend(path):
    """Save the current file as a .blend."""
    bpy.ops.wm.save_as_mainfile(filepath=path)


def scene_bounds():
    """World-space AABB of all mesh objects. Returns (mins, maxs)."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
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
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    triangles = 0
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
    mins, maxs = scene_bounds()
    size = maxs - mins
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
        "scales": {
            o.name: [float(s) for s in o.scale] for o in meshes
        },
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
'''
