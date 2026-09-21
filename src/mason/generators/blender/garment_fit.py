"""Ease, silhouette push, optional cloth, then solidify."""

CREATE_GARMENT_FIT_SRC = r'''
from mathutils.bvhtree import BVHTree


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
    """Round the extract so it is not a vacuum-sealed body copy."""
    fit = cfg.get("fit") or "fitted"
    boost = {
        "skin_tight": 0.2, "fitted": 0.45, "regular": 0.7,
        "loose": 1.0, "oversized": 1.35,
    }.get(fit, 0.45)
    style = float(cfg.get("stylization") or 0.7)
    ease = float(cfg.get("ease_offset") or 0.008)
    chest = marks.get("chest")
    mid_x = chest.x if chest else 0.0
    torso_half = ease * 14.0
    base = ease * (0.15 + 0.25 * style) * boost
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        extra = base * 1.25 if abs(world.x - mid_x) <= torso_half else base * 0.4
        if chest is not None and world.z > chest.z:
            extra *= 0.2
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


def _cap_neck(shirt, marks):
    """Flatten above the pinch, then shrink a platter to a hole."""
    neck = marks["neck"]
    top = neck.z
    mins, maxs = body_bounds(shirt)
    height = max(maxs.z - mins.z, 0.01)
    cap_r = height * 0.16
    imw = shirt.matrix_world.inverted()
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        if world.z <= top:
            continue
        world.z = top
        delta = Vector((world.x - neck.x, world.y - neck.y, 0.0))
        if delta.length > cap_r:
            xy = delta.normalized() * cap_r
            world.x = neck.x + xy.x
            world.y = neck.y + xy.y
        vert.co = imw @ world
    shirt.data.update()


def _push_off_body(shirt, body, gap):
    """Move outer verts that sit inside the body out along the surface."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(body, dg)
    imw = shirt.matrix_world.inverted()
    rot = shirt.matrix_world.to_3x3()
    mins, maxs = body_bounds(shirt)
    center = (mins + maxs) * 0.5
    dists = [
        (shirt.matrix_world @ v.co - center).length
        for v in shirt.data.vertices
    ]
    dists.sort()
    cutoff = dists[int(len(dists) * 0.45)] if dists else 0.0
    chest_z = maxs.z - (maxs.z - mins.z) * 0.28
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        high = world.z >= chest_z
        if not high and (world - center).length < cutoff:
            continue
        normal = (rot @ vert.normal).normalized()
        if not high and normal.dot(world - center) < 0.0:
            continue
        loc, nrm, _idx, _d = tree.find_nearest(world)
        if loc is None or nrm is None:
            continue
        nrm = nrm.normalized()
        need = gap * (2.6 if high else 1.35)
        if (world - loc).dot(nrm) >= need:
            continue
        vert.co = imw @ (loc + nrm * need)
    shirt.data.update()


def _push_sleeves_off_arm(
    shirt, body, marks, height, gap, from_idx=0,
):
    """Push only verts inside the arm. Leaves the torso alone."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(body, dg)
    imw = shirt.matrix_world.inverted()
    for vert in shirt.data.vertices:
        if vert.index < from_idx:
            continue
        world = shirt.matrix_world @ vert.co
        if not _is_sleeve_vert(world, marks, height):
            continue
        loc, nrm, _idx, _d = tree.find_nearest(world)
        if loc is None or nrm is None:
            continue
        nrm = nrm.normalized()
        if (world - loc).dot(nrm) >= 0.0:
            continue
        vert.co = imw @ (loc + nrm * gap)
    shirt.data.update()


def _thicken_sleeves(shirt, marks, height, thick, from_idx=0):
    """Solidify remade sleeve verts so tubes have cloth depth."""
    vg = shirt.vertex_groups.new(name="mason_sleeve")
    idxs = [
        v.index for v in shirt.data.vertices
        if v.index >= from_idx
        and _is_sleeve_vert(
            shirt.matrix_world @ v.co, marks, height,
        )
    ]
    if not idxs:
        return
    vg.add(idxs, 1.0, "REPLACE")
    sol = shirt.modifiers.new("ThickSleeve", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    sol.use_even_offset = True
    sol.use_rim = True
    sol.vertex_group = "mason_sleeve"
    _apply_mod(shirt, "ThickSleeve")


def _fit_stylized(shirt, body, marks, height, gap):
    """Keep the extracted body faces. No tubes, remesh, or drape."""
    _ = (body, marks, height, gap)
    shade_smooth(shirt)
    return shirt


def fit_garment(shirt, body, marks=None):
    """Stylized second-skin, or later drape with tubes/cloth."""
    cfg = _garment_cfg()
    refit = cfg.get("mode") == "refit"
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bmins, bmaxs = body_bounds(body)
    height = max(bmaxs.z - bmins.z, 0.01)
    gap = max(
        float(cfg.get("ease_offset") or 0.002) * 2.0,
        height * 0.010,
    )
    if _garment_pipeline() == "stylized":
        return _fit_stylized(shirt, body, marks, height, gap)
    if refit:
        if marks is not None:
            n0 = len(shirt.data.vertices)
            _add_sleeve_tubes(shirt, marks, height, body)
            _push_sleeves_off_arm(
                shirt, body, marks, height, gap, from_idx=n0,
            )
            _thicken_sleeves(
                shirt, marks, height, height * 0.014, from_idx=n0,
            )
    else:
        if marks is not None:
            silhouette_pass(shirt, marks, cfg)
            _clamp_hem(shirt, marks)
            _cap_neck(shirt, marks)
        style = float(cfg.get("stylization") or 0.7)
        smooth = shirt.modifiers.new("Relax", "SMOOTH")
        smooth.iterations = 2 + int(style * 2)
        smooth.factor = 0.22 + style * 0.12
        _apply_mod(shirt, "Relax")
        if marks is not None:
            _clip_batwings(shirt, marks, height, body, keep_tubes=True)
            _add_sleeve_tubes(shirt, marks, height, body)
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
            _cap_neck(shirt, marks)
        if marks is not None:
            _push_sleeves_off_arm(shirt, body, marks, height, gap)
        _push_off_body(shirt, body, gap)
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
        0.0,
    )
    shader = CONFIG.get("shader") or "principled"
    apply_shader(mat, shader, settings.get("shader_params"))
    bump_s = float(CONFIG.get("bump_strength") or 0.0)
    if bump_s > 0.01 and CONFIG.get("bump_image"):
        apply_bump_and_normal(
            mat,
            CONFIG["wrap"],
            CONFIG.get("bump_image") or None,
            CONFIG.get("normal_image") or None,
            bump_s,
        )
    assign_material(obj, mat)
    unwrap_cube(obj, CONFIG.get("tile_size") or 0.25)
'''
