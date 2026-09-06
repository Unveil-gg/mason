"""Blender source snippets for box primitives."""

CREATE_BOX_SRC = r'''
def create_box(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a cube sized and placed in world space. Returns the object."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def shade_smooth(obj):
    """Mark faces smooth so cylinders and spheres do not facet."""
    mesh = obj.data
    for poly in mesh.polygons:
        poly.use_smooth = True


def create_cylinder(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a cylinder; size is (diameter_x, diameter_y, height)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.5,
        depth=1.0,
        location=location,
        vertices=24,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj


def create_plane(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a plane; size is (width, depth, ignored)."""
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = (size[0], size[1], 0.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def create_cone(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a cone; size is (diameter_x, diameter_y, height)."""
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.5,
        radius2=0.0,
        depth=1.0,
        location=location,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj


def create_torus(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a torus; size is the world AABB (major/minor via dims)."""
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.35,
        minor_radius=0.1,
        location=location,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj


def create_sphere(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a UV sphere; size is (diameter_x, diameter_y, diameter_z)."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.5, location=location, segments=24, ring_count=12,
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj


def create_tapered_box(name, size, location, rotation=(0.0, 0.0, 0.0), taper=(0.72, 0.72)):
    """Box whose +Z face is scaled by taper (sx, sy)."""
    obj = create_box(name, size, location, rotation)
    mesh = obj.data
    zs = [v.co.z for v in mesh.vertices]
    mid = (max(zs) + min(zs)) * 0.5
    sx, sy = float(taper[0]), float(taper[1])
    for vert in mesh.vertices:
        if vert.co.z > mid:
            vert.co.x *= sx
            vert.co.y *= sy
    mesh.update()
    return obj


def create_primitive(part):
    """Dispatch a part dict to the matching constructor."""
    shape = part.get("shape") or "box"
    args = (
        part["name"],
        tuple(part["size"]),
        tuple(part["location"]),
        tuple(part.get("rotation") or (0.0, 0.0, 0.0)),
    )
    if shape == "cylinder":
        return create_cylinder(*args)
    if shape == "plane":
        return create_plane(*args)
    if shape == "cone":
        return create_cone(*args)
    if shape == "torus":
        return create_torus(*args)
    if shape == "sphere":
        return create_sphere(*args)
    if shape == "tapered_box":
        return create_tapered_box(
            *args,
            tuple(part.get("taper") or (0.72, 0.72)),
        )
    return create_box(*args)


def unwrap_cube(obj, tile_size):
    """Deterministic box-projected UVs, sized so tileable textures
    repeat consistently across parts regardless of object size."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(
        cube_size=float(tile_size),
        correct_aspect=True,
        clip_to_bounds=False,
        scale_to_bounds=False,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def unwrap_stretch(obj):
    """Stretch UVs to fill 0..1 on a single-quad plane, so one decal
    image (a label, sign face, poster) shows whole and centered
    instead of being cropped by tile-based projection."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    for face in mesh.polygons:
        for i, loop_index in enumerate(face.loop_indices):
            uv_layer[loop_index].uv = corners[i % 4]


def apply_bevel(obj, width, segments):
    """Apply a Bevel modifier and keep it applied."""
    if width <= 0 or segments < 1:
        return
    mod = obj.modifiers.new(name="Bevel", type="BEVEL")
    mod.width = float(width)
    mod.segments = int(segments)
    mod.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
'''
