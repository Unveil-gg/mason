"""Shrinkwrap, relax, optional cloth, then solidify."""

CREATE_GARMENT_FIT_SRC = r'''
def _apply_mod(obj, name):
    """Apply one modifier. Object must be active."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.modifiers.get(name):
        bpy.ops.object.modifier_apply(modifier=name)


def _bbox_span(obj):
    """World AABB diagonal length of one mesh."""
    mins, maxs = body_bounds(obj)
    return (maxs - mins).length


def _run_cloth(shirt, body, frames, cfg):
    """Short pinned cloth bake. Drops the modifier if it explodes."""
    if body.modifiers.get("Collision") is None:
        body.modifiers.new("Collision", "COLLISION")
    pin = shirt.vertex_groups.get("mason_pin")
    if pin is None:
        pin = shirt.vertex_groups.new(name="mason_pin")
    pin.add([v.index for v in shirt.data.vertices], 0.82, "REPLACE")
    cloth = shirt.modifiers.new("Cloth", "CLOTH")
    stiff = float(cfg.get("stiffness") or 0.6)
    wrinkle = float(cfg.get("wrinkle") or 0.2)
    cloth.settings.quality = 4
    cloth.settings.mass = 0.15
    cloth.settings.tension_stiffness = 18.0 * stiff + 6.0
    cloth.settings.compression_stiffness = 18.0 * stiff + 6.0
    cloth.settings.bending_stiffness = 1.0 + 12.0 * (1.0 - wrinkle)
    cloth.settings.vertex_group_mass = "mason_pin"
    cloth.collision_settings.distance_min = 0.005
    before = _bbox_span(shirt)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    bpy.context.view_layer.objects.active = shirt
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = shirt.evaluated_get(deps)
    after = _bbox_span(ev)
    if after > before * 1.45 or after < before * 0.55:
        shirt.modifiers.remove(cloth)
        return
    _apply_mod(shirt, "Cloth")


def _restore_verts(obj, stored):
    """Copy stored local coordinates back onto the mesh."""
    for vert, co in zip(obj.data.vertices, stored):
        vert.co = co
    obj.data.update()


def _looks_exploded(obj, rest_span):
    """True if the mesh spiked or grew past the rest size."""
    if _bbox_span(obj) > rest_span * 1.35:
        return True
    mins, maxs = body_bounds(obj)
    center = (mins + maxs) * 0.5
    limit = rest_span * 0.8
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if (world - center).length > limit:
            return True
    return False


def _wrap_group(shirt, marks):
    """Weight torso verts for shrinkwrap; leave openings and sleeves."""
    vg = shirt.vertex_groups.new(name="mason_wrap")
    neck_z = marks["neck"].z if marks else 1e9
    hem_z = marks["hem"].z if marks else -1e9
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        sleeve = abs(world.x) > 0.20
        opening = (
            abs(world.z - neck_z) < 0.035
            or abs(world.z - hem_z) < 0.035
        )
        weight = 0.0 if (sleeve or opening) else 1.0
        vg.add([vert.index], weight, "REPLACE")
    return vg


def fit_garment(shirt, body, marks=None):
    """Project onto the body, smooth, optional cloth, thicken."""
    cfg = _garment_cfg()
    clearance = float(cfg.get("clearance") or 0.012)
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    stored = [vert.co.copy() for vert in shirt.data.vertices]
    rest = _bbox_span(shirt)

    wrap = shirt.modifiers.new("Fit", "SHRINKWRAP")
    wrap.wrap_method = "NEAREST_SURFACEPOINT"
    wrap.wrap_mode = "ABOVE_SURFACE"
    wrap.target = body
    wrap.offset = clearance
    if marks is not None:
        _wrap_group(shirt, marks)
        wrap.vertex_group = "mason_wrap"
    _apply_mod(shirt, "Fit")
    gaps = _signed_gaps(shirt, body)
    total = max(len(shirt.data.vertices), 1)
    pen = sum(1 for gap in gaps if gap < -0.002) / total
    if pen > 0.08 or _looks_exploded(shirt, rest):
        _restore_verts(shirt, stored)

    smooth = shirt.modifiers.new("Relax", "SMOOTH")
    style = float(cfg.get("stylization") or 0.7)
    smooth.iterations = 2 + int(3 * style)
    smooth.factor = 0.35
    _apply_mod(shirt, "Relax")
    if _looks_exploded(shirt, rest):
        _restore_verts(shirt, stored)

    frames = int(cfg.get("cloth_frames") or 0)
    if frames > 0:
        try:
            _run_cloth(shirt, body, frames, cfg)
        except Exception:
            pass
        if _looks_exploded(shirt, rest):
            _restore_verts(shirt, stored)

    thick = shirt.modifiers.new("Thick", "SOLIDIFY")
    thick.thickness = float(cfg.get("thickness") or 0.004)
    thick.offset = 1.0
    thick.use_even_offset = True
    _apply_mod(shirt, "Thick")
    shade_smooth(shirt)
    return shirt


def apply_garment_material(obj):
    """Assign the spec fabric / primary color to the cloth mesh."""
    families = CONFIG.get("families") or {}
    settings = families.get("fabric") or {
        "roughness": CONFIG["roughness"],
        "metallic": CONFIG["metallic"],
        "variation": 0.06,
    }
    hex_color = (
        CONFIG["palette"].get("primary")
        or CONFIG["palette"].get("cotton")
        or "#F4F1EA"
    )
    mat = create_material(
        "garment",
        hex_color,
        settings["roughness"],
        settings["metallic"],
        settings.get("variation") or 0.0,
    )
    shader = (
        settings.get("shader")
        or CONFIG.get("shader")
        or "principled"
    )
    apply_shader(mat, shader, settings.get("shader_params"))
    apply_bump_and_normal(
        mat,
        CONFIG["wrap"],
        CONFIG.get("bump_image") or None,
        CONFIG.get("normal_image") or None,
        settings.get("bump_strength")
        or CONFIG.get("bump_strength")
        or 0.04,
    )
    assign_material(obj, mat)
    unwrap_cube(obj, CONFIG.get("tile_size") or 0.25)
'''
