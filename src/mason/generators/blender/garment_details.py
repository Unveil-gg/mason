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


def add_garment_details(shirt, marks):
    """Add the few cues that make the kind readable. Joins onto shirt."""
    cfg = _garment_cfg()
    wanted = set(cfg.get("details") or [])
    if not wanted:
        return shirt
    height = max((marks["neck"] - marks["hem"]).length, 0.01)
    thick = float(cfg.get("thickness") or 0.004)
    neck_w = float(cfg.get("neck") or height * 0.14)
    extras = []
    if "collar" in wanted:
        extras.append(_ring_mesh(
            "collar", marks["neck"], neck_w * 0.38, thick * 1.6,
        ))
    if "cuffs" in wanted and cfg.get("sleeve") != "none":
        for key, name in (("wrist_l", "cuff_l"), ("wrist_r", "cuff_r")):
            if key not in marks:
                continue
            extras.append(_ring_mesh(
                name, marks[key], height * 0.06, thick * 1.3,
            ))
        if cfg.get("sleeve") == "short":
            for extra in extras[-2:]:
                extra.location = extra.location.lerp(marks["shoulders"], 0.35)
    if "hem" in wanted or "waistband" in wanted:
        extras.append(_ring_mesh(
            "hem_band", marks["hem"], height * 0.16, thick * 1.4,
        ))
    if "placket" in wanted:
        front = marks["chest"].copy()
        front.y = marks["chest"].y - height * 0.12
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=front)
        plank = bpy.context.active_object
        plank.name = "placket"
        plank.dimensions = (thick * 3.0, thick * 2.0, height * 0.42)
        bpy.ops.object.transform_apply(scale=True)
        extras.append(plank)
        if "buttons" in wanted:
            for i in range(3):
                loc = front.copy()
                loc.z = marks["hem"].z + height * (0.18 + 0.18 * i)
                loc.y -= thick * 2.0
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=thick * 1.2, depth=thick * 0.8, location=loc,
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
