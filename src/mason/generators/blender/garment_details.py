"""Clothing construction cues: collar, cuffs, hem, placket, buttons."""

CREATE_GARMENT_DETAILS_SRC = r'''
def _join_onto(target, extras):
    """Join extra meshes into target. Skips missing objects."""
    alive = [o for o in extras if o is not None]
    if not alive:
        return target
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    for extra in alive:
        extra.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return target


def _ring_mesh(name, center, radius, tube, normal=None):
    """Small torus used as a collar, cuff, or hem band."""
    bpy.ops.mesh.primitive_torus_add(
        major_radius=max(radius, 0.002),
        minor_radius=max(tube, 0.0006),
        location=center,
        major_segments=16,
        minor_segments=6,
    )
    obj = bpy.context.active_object
    obj.name = name
    if normal is not None:
        obj.rotation_euler = normal.to_track_quat("Z", "Y").to_euler()
    return obj


def _cuff_point(marks, side, sleeve):
    """Forearm cuff for short sleeves; wrist for long."""
    sh = marks.get("shoulder_" + side)
    wr = marks.get("wrist_" + side)
    if sh is None:
        return None
    if wr is None:
        return sh
    t = 0.40 if sleeve == "short" else 0.92
    return sh.lerp(wr, t)


def _slice_radii(obj, z, pad):
    """Half-width and half-depth of shirt verts near world Z."""
    xs, ys = [], []
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if abs(world.z - z) <= pad:
            xs.append(world.x)
            ys.append(world.y)
    if not xs:
        return pad, pad
    rx = max(max(xs) - min(xs), pad) * 0.5
    ry = max(max(ys) - min(ys), pad) * 0.5
    return rx, ry


def _front_y(obj, z, pad):
    """Most-negative Y of centerline verts near world Z."""
    ys = []
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if abs(world.z - z) <= pad * 2 and abs(world.x) <= pad * 6:
            ys.append(world.y)
    return min(ys) if ys else z


def add_garment_details(shirt, marks):
    """Add cues sized from the shirt cross-section at each band."""
    cfg = _garment_cfg()
    wanted = set(cfg.get("details") or [])
    if not wanted:
        return shirt
    mins, maxs = body_bounds(shirt)
    span = max(maxs.x - mins.x, 0.01)
    height = max(maxs.z - mins.z, 0.01)
    pad = height * 0.04
    tube = max(height * 0.028, 0.0008)
    sleeve = cfg.get("sleeve")
    extras = []
    front_y = _front_y(shirt, marks["chest"].z, pad)
    if "collar" in wanted:
        loc = marks["neck"].copy()
        loc.y = _front_y(shirt, marks["neck"].z, pad) - tube * 0.4
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        col = bpy.context.active_object
        col.name = "collar"
        col.dimensions = (height * 0.18, tube * 1.5, tube * 2.4)
        bpy.ops.object.transform_apply(scale=True)
        extras.append(col)
    if "cuffs" in wanted and sleeve != "none":
        for side, name in (("l", "cuff_l"), ("r", "cuff_r")):
            loc = _cuff_point(marks, side, sleeve)
            if loc is None:
                continue
            extras.append(_ring_mesh(name, loc, height * 0.05, tube * 0.7))
    if "placket" in wanted:
        front = marks["chest"].copy()
        front.y = front_y - tube * 0.3
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=front)
        plank = bpy.context.active_object
        plank.name = "placket"
        plank.dimensions = (span * 0.045, tube * 1.1, height * 0.42)
        bpy.ops.object.transform_apply(scale=True)
        extras.append(plank)
        if "buttons" in wanted:
            for i in range(3):
                loc = front.copy()
                loc.z = mins.z + height * (0.22 + 0.22 * i)
                loc.y -= tube * 0.4
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=span * 0.018, depth=tube * 0.7, location=loc,
                )
                btn = bpy.context.active_object
                btn.rotation_euler = (1.5708, 0.0, 0.0)
                extras.append(btn)
    if "hood" in wanted:
        hood_c = marks["neck"].copy()
        hood_c.z += height * 0.12
        hood_c.y += height * 0.04
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=height * 0.16, location=hood_c, segments=12, ring_count=8,
        )
        extras.append(bpy.context.active_object)
    return _join_onto(shirt, extras)
'''
