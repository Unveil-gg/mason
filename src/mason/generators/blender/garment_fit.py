"""Ease, silhouette push, optional cloth, then solidify."""

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
    """Pinned cloth bake. Drops the modifier if it explodes."""
    if body.modifiers.get("Collision") is None:
        body.modifiers.new("Collision", "COLLISION")
    pin = shirt.vertex_groups.get("mason_pin")
    if pin is None:
        pin = shirt.vertex_groups.new(name="mason_pin")
    idxs = [v.index for v in shirt.data.vertices]
    pin.add(idxs, 0.75, "REPLACE")
    cloth = shirt.modifiers.new("Cloth", "CLOTH")
    stiff = float(cfg.get("stiffness") or 0.6)
    cloth.settings.quality = 4
    cloth.settings.mass = 0.15
    cloth.settings.tension_stiffness = 14.0 * stiff + 4.0
    cloth.settings.vertex_group_mass = "mason_pin"
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    before = _bbox_span(shirt)
    bpy.context.view_layer.objects.active = shirt
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
    ev = shirt.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if _bbox_span(ev) > before * 1.45:
        shirt.modifiers.remove(cloth)
        return
    _apply_mod(shirt, "Cloth")


def silhouette_pass(shirt, marks, cfg):
    """Push garment regions so shrinkwrap cannot vacuum-seal them."""
    fit = cfg.get("fit") or "fitted"
    boost = {
        "skin_tight": 0.2, "fitted": 0.45, "regular": 0.7,
        "loose": 1.0, "oversized": 1.35,
    }.get(fit, 0.45)
    ease = float(cfg.get("ease_offset") or 0.008)
    shoulders = marks.get("shoulders")
    chest = marks.get("chest")
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        extra = 0.0
        if shoulders and abs(world.z - shoulders.z) < ease * 8:
            extra += ease * 0.6 * boost
        if chest and abs(world.z - chest.z) < ease * 10:
            extra += ease * 0.35 * boost
        if extra:
            vert.co += vert.normal * extra
    shirt.data.update()


def _clamp_hem(shirt, marks):
    """Keep every vert at or above the hem plane."""
    floor_z = marks["hem"].z
    imw = shirt.matrix_world.inverted()
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        if world.z < floor_z:
            world.z = floor_z
            vert.co = imw @ world
    shirt.data.update()


def fit_garment(shirt, body, marks=None):
    """Silhouette, optional cloth, thicken. No vacuum shrinkwrap."""
    cfg = _garment_cfg()
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    if marks is not None:
        silhouette_pass(shirt, marks, cfg)
        _clamp_hem(shirt, marks)
    smooth = shirt.modifiers.new("Relax", "SMOOTH")
    smooth.iterations = 3
    smooth.factor = 0.3
    _apply_mod(shirt, "Relax")
    fit = cfg.get("fit") or "fitted"
    frames = int(cfg.get("cloth_frames") or 0)
    if frames > 0 and fit in ("loose", "oversized"):
        try:
            _run_cloth(shirt, body, frames, cfg)
        except Exception:
            pass
    weight = cfg.get("fabric_weight") or "medium"
    thick = float(cfg.get("thickness") or 0.004)
    if weight == "thin":
        thick *= 0.7
    elif weight == "thick":
        thick *= 1.6
    sol = shirt.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    sol.use_even_offset = True
    _apply_mod(shirt, "Thick")
    if marks is not None:
        _clamp_hem(shirt, marks)
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
