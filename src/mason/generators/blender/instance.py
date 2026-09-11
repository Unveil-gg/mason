"""Import another asset's GLB as a named instance cluster."""

CREATE_INSTANCE_SRC = r'''
def import_instance(part):
    """Import a built GLB under a named empty. Returns the empty."""
    name = part["name"]
    path = (CONFIG.get("instance_paths") or {}).get(name) or ""
    loc = tuple(part.get("location") or (0.0, 0.0, 0.0))
    rot = tuple(part.get("rotation") or (0.0, 0.0, 0.0))
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    root = bpy.context.active_object
    root.name = name
    root.rotation_euler = rot
    axis = part.get("mirror")
    if axis == "x":
        root.scale[0] *= -1
    elif axis == "y":
        root.scale[1] *= -1
    elif axis == "z":
        root.scale[2] *= -1
    if not path:
        return root
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [obj for obj in bpy.data.objects if obj not in before]
    for obj in imported:
        if obj.parent and obj.parent in imported:
            continue
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
        obj.matrix_world = world
        if obj.type == "MESH" and not obj.name.startswith(name + "_"):
            obj.name = name + "_" + obj.name
    return root
'''
