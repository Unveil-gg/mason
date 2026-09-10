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


def add_garment_details(shirt, marks):
    """Reshape extract rims. Do not glue on boxes or toruses."""
    cfg = _garment_cfg()
    wanted = (set(cfg.get("details") or []) & _GEO_DETAILS)
    if not wanted:
        return shirt
    mins, maxs = body_bounds(shirt)
    height = max(maxs.z - mins.z, 0.01)
    pad = height * 0.045
    amt = float(cfg.get("ease_offset") or 0.002) * 0.9
    sleeve = cfg.get("sleeve")
    if "collar" in wanted:
        _offset_band(shirt, marks["neck"].z, pad, amt * 1.3)
    if "hem" in wanted or "waistband" in wanted:
        _offset_band(shirt, marks["hem"].z, pad, amt)
    if "cuffs" in wanted and sleeve != "none":
        for side in ("l", "r"):
            loc = _cuff_point(marks, side, sleeve)
            if loc is not None:
                _offset_near(shirt, loc, pad * 1.4, amt)
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
