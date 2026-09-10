"""Silhouette cues only. Surface details stay texture."""

CREATE_GARMENT_DETAILS_SRC = r'''
_GEO_DETAILS = frozenset({
    "collar", "cuffs", "hem", "waistband", "hood", "armholes",
})


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


def _offset_band(shirt, z, pad, amount):
    """Push verts near world Z along their normals."""
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        if abs(world.z - z) <= pad:
            vert.co += vert.normal * amount
    shirt.data.update()


def _offset_near(shirt, point, radius, amount):
    """Push verts near a world point along their normals."""
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        if (world - point).length <= radius:
            vert.co += vert.normal * amount
    shirt.data.update()


def _front_on_shirt(shirt, z):
    """World point on the front centerline near Z."""
    best = None
    best_y = 1e9
    mins, maxs = body_bounds(shirt)
    pad = max((maxs.z - mins.z) * 0.04, 0.002)
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        if abs(world.z - z) <= pad and abs(world.x) <= pad * 1.6:
            if world.y < best_y:
                best_y = world.y
                best = world.copy()
    if best is None:
        return None
    imw = shirt.matrix_world.inverted()
    hit, loc, nrm, _idx = shirt.closest_point_on_mesh(imw @ best)
    if not hit:
        return best
    world = shirt.matrix_world @ loc
    wn = (shirt.matrix_world.to_3x3() @ nrm).normalized()
    return world + wn * 0.0005


def _add_center_buttons(shirt, marks):
    """Three small buttons snapped to the chest midline."""
    mins, maxs = body_bounds(shirt)
    height = max(maxs.z - mins.z, 0.01)
    extras = []
    for i in range(3):
        loc = _front_on_shirt(shirt, mins.z + height * (0.30 + 0.18 * i))
        if loc is None:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=height * 0.038, location=loc, segments=8, ring_count=6,
        )
        btn = bpy.context.active_object
        mat = create_material("button", "#8B7355", 0.45, 0.0, 0.0)
        assign_material(btn, mat)
        extras.append(btn)
    if not extras:
        return shirt
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    for extra in extras:
        extra.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.object.join()
    return shirt


def add_garment_details(shirt, marks):
    """Rim offsets plus optional center buttons. No boxes or toruses."""
    cfg = _garment_cfg()
    cues = set(cfg.get("details") or []) | set(cfg.get("surface_details") or [])
    wanted = cues & _GEO_DETAILS
    mins, maxs = body_bounds(shirt)
    height = max(maxs.z - mins.z, 0.01)
    pad = height * 0.04
    amt = float(cfg.get("ease_offset") or 0.002) * 0.5
    sleeve = cfg.get("sleeve")
    if "hem" in wanted or "waistband" in wanted:
        _offset_band(shirt, marks["hem"].z, pad, amt)
    if "cuffs" in wanted and sleeve != "none":
        for side in ("l", "r"):
            loc = _cuff_point(marks, side, sleeve)
            if loc is not None:
                _offset_near(shirt, loc, pad * 1.2, amt)
    if "hood" in wanted:
        hood_c = marks["neck"].copy()
        hood_c.z += height * 0.12
        hood_c.y += height * 0.03
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=height * 0.14, location=hood_c, segments=10, ring_count=6,
        )
        hood = bpy.context.active_object
        bpy.ops.object.select_all(action="DESELECT")
        shirt.select_set(True)
        hood.select_set(True)
        bpy.context.view_layer.objects.active = shirt
        bpy.ops.object.join()
    return shirt
'''
