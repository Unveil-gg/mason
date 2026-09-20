"""Import or build a garment body and sample landmarks / slices."""

CREATE_GARMENT_BODY_SRC = r'''
import math


def _garment_cfg():
    """Return the garment CONFIG dict."""
    return CONFIG.get("garment") or {}


def _garment_pipeline():
    """stylized second-skin (default) or later drape."""
    raw = _garment_cfg().get("pipeline") or "stylized"
    if raw == "drape":
        return "drape"
    return "stylized"


def import_body_glb(path):
    """Import a character GLB. Returns the character mesh."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [
        o for o in bpy.data.objects
        if o not in before and o.type == "MESH"
    ]
    if not meshes:
        return None
    preferred = [
        o for o in meshes
        if o.name.lower() in ("mouse", "body", "character")
    ]
    if preferred:
        body = preferred[0]
    else:
        meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
        body = meshes[0]
    body.name = "_mason_body"
    for extra in meshes:
        if extra == body:
            continue
        extra.name = "_mason_body_" + extra.name
        extra.hide_set(True)
        extra.hide_render = True
    _scale_garment_to_body(body)
    return body


def _scale_garment_to_body(body):
    """Scale 1 m spec values to the body. Sets ease_offset."""
    cfg = _garment_cfg()
    mins, maxs = body_bounds(body)
    height = maxs.z - mins.z
    scale = 1.0
    if 1e-4 < height < 0.35:
        scale = height / 1.0
        for key in ("clearance", "thickness", "hem", "neck"):
            if cfg.get(key) is not None:
                cfg[key] = float(cfg[key]) * scale
    ease = {
        "skin_tight": 0.003, "fitted": 0.006, "regular": 0.010,
        "loose": 0.022, "oversized": 0.035,
    }
    fit = cfg.get("fit") or "fitted"
    # Tiny characters need a visible world gap or the shirt
    # vacuum-seals and clips through the body ball.
    cfg["ease_offset"] = max(
        ease.get(fit, 0.008) * scale, height * 0.018,
    )
    return scale


def create_small_animal_body():
    """Build a ~1 m torso cage. Returns the remeshed mesh."""
    specs = [
        ((0.0, 0.01, 0.26), (0.30, 0.20, 0.14)),
        ((0.0, 0.02, 0.38), (0.36, 0.24, 0.28)),
        ((0.0, -0.01, 0.50), (0.32, 0.22, 0.18)),
        ((-0.16, 0.0, 0.54), (0.14, 0.12, 0.12)),
        ((0.16, 0.0, 0.54), (0.14, 0.12, 0.12)),
        ((-0.22, 0.0, 0.50), (0.10, 0.09, 0.09)),
        ((0.22, 0.0, 0.50), (0.10, 0.09, 0.09)),
        ((0.0, 0.0, 0.62), (0.14, 0.14, 0.10)),
    ]
    chunks = []
    for loc, size in specs:
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.5, location=loc, segments=16, ring_count=10,
        )
        obj = bpy.context.active_object
        obj.dimensions = size
        bpy.ops.object.transform_apply(scale=True)
        chunks.append(obj)
    target = chunks[0]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in chunks:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    rm = target.modifiers.new(name="Cage", type="REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.02
    bpy.ops.object.modifier_apply(modifier=rm.name)
    sm = target.modifiers.new(name="CageSmooth", type="SMOOTH")
    sm.iterations = 6
    bpy.ops.object.modifier_apply(modifier=sm.name)
    target.name = "_mason_body"
    shade_smooth(target)
    return target


def body_bounds(obj):
    """World AABB from mesh verts. bound_box is often stale."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        mins.x = min(mins.x, world.x)
        mins.y = min(mins.y, world.y)
        mins.z = min(mins.z, world.z)
        maxs.x = max(maxs.x, world.x)
        maxs.y = max(maxs.y, world.y)
        maxs.z = max(maxs.z, world.z)
    return mins, maxs


def _bone_head(arm, names):
    """World location of the first matching pose bone head."""
    for name in names:
        bone = arm.pose.bones.get(name)
        if bone is not None:
            return arm.matrix_world @ bone.head
    return None


def extract_landmarks(obj):
    """Named world points. Delegates to analyze_anatomy."""
    return analyze_anatomy(obj)


def _refine_stacked_body(obj, marks):
    """Collar at the pinch of two stacked masses; longer hem.

    Mousey is two spheres, not a human neck. Bone neck often sits
    too low on the body ball, so sleeves root under the arm sockets.
    """
    mins, maxs = body_bounds(obj)
    height = max(maxs.z - mins.z, 0.001)
    mid = (mins + maxs) * 0.5
    pinch_z = mins.z + height * 0.62
    head = marks.get("head")
    if head is not None:
        pinch_z = min(pinch_z, head.z - height * 0.14)
    if pinch_z <= marks["neck"].z + height * 0.01:
        pinch_z = marks["neck"].z + height * 0.04
    marks["neck"] = Vector((mid.x, mid.y, pinch_z))
    marks["shoulders"] = Vector((
        mid.x, mid.y, pinch_z - height * 0.03,
    ))
    hips = marks.get("hips")
    if hips is not None:
        shirt_hem = min(hips.z + height * 0.02, mins.z + height * 0.22)
    else:
        shirt_hem = mins.z + height * 0.20
    marks["hem"] = Vector((marks["hem"].x, marks["hem"].y, shirt_hem))
    marks["stacked_spheres"] = True


def _measure_torso_half(body, marks):
    """Body-ball half-width. Ignores hands in the AABB."""
    mins, maxs = body_bounds(body)
    chest = marks.get("chest")
    mid = chest.x if chest is not None else (mins.x + maxs.x) * 0.5
    aabb_half = max(maxs.x - mins.x, 1e-6) * 0.5
    z0 = marks["hips"].z
    z1 = marks["chest"].z
    xs = []
    for vert in body.data.vertices:
        world = body.matrix_world @ vert.co
        if world.z < z0 or world.z > z1:
            continue
        dx = abs(world.x - mid)
        if dx < aabb_half * 0.70:
            xs.append(dx)
    if not xs:
        return aabb_half * 0.45
    return max(xs)


def _bind_sleeve_axes(body, marks):
    """Sleeve start/end from bones, else farthest hand verts."""
    mins, maxs = body_bounds(body)
    chest = marks.get("chest")
    mid = chest.x if chest is not None else (mins.x + maxs.x) * 0.5
    torso = _measure_torso_half(body, marks)
    marks["torso_half_x"] = float(torso)
    mid_y = (mins.y + maxs.y) * 0.5
    ankle = marks.get("ankle_l") or marks.get("ankle_r")
    z_floor = ankle.z if ankle is not None else mins.z
    for side, sign in (("l", 1.0), ("r", -1.0)):
        bone_sh = marks.get("arm_" + side) or marks.get(
            "shoulder_" + side,
        )
        bone_wr = marks.get("wrist_" + side)
        if bone_sh is not None:
            start = bone_sh.copy()
            start.x = mid + sign * torso * 1.04
        else:
            start = Vector((
                mid + sign * torso * 1.04,
                mid_y,
                marks["shoulders"].z,
            ))
        hand = bone_wr.copy() if bone_wr is not None else None
        if hand is None:
            hand_dx = -1.0
            for vert in body.data.vertices:
                world = body.matrix_world @ vert.co
                if world.z < z_floor:
                    continue
                dx = (world.x - mid) * sign
                if dx > hand_dx:
                    hand_dx = dx
                    hand = world.copy()
        if hand is None:
            hand = Vector((
                mid + sign * max(torso * 1.8, 0.01),
                start.y,
                start.z,
            ))
        # Wrist bones can sit inside the torso ball. Aim the
        # cuff along the arm mesh, level with the shoulder.
        far = abs(hand.x - mid)
        hips_z = marks["hips"].z
        neck_z = marks["neck"].z
        for vert in body.data.vertices:
            world = body.matrix_world @ vert.co
            if world.z < hips_z or world.z > neck_z + (
                maxs.z - mins.z
            ) * 0.04:
                continue
            dx = (world.x - mid) * sign
            if dx > far:
                far = dx
        out = max(far, torso * 1.85)
        hand.x = mid + sign * out
        hand.y = start.y
        hand.z = start.z
        marks["sleeve_start_" + side] = start
        marks["sleeve_end_" + side] = hand


def slice_ring(obj, z, n=16, clearance=0.012, max_radius=None):
    """Outward-offset ring at world Z. Returns world Vectors."""
    mins, maxs = body_bounds(obj)
    center = Vector(((mins.x + maxs.x) * 0.5, (mins.y + maxs.y) * 0.5, z))
    imw = obj.matrix_world.inverted()
    radius = max(maxs.x - mins.x, maxs.y - mins.y) * 0.8 + 0.2
    if max_radius:
        radius = min(radius, float(max_radius) * 2.4)
    pts = []
    for i in range(n):
        ang = 2.0 * math.pi * i / n
        direc = Vector((math.cos(ang), math.sin(ang), 0.0))
        start = center + direc * radius
        local_start = imw @ start
        local_dir = (imw.to_3x3() @ (-direc)).normalized()
        hit, loc, _nrm, _idx = obj.ray_cast(
            local_start, local_dir, distance=radius * 2.2,
        )
        if hit:
            world = obj.matrix_world @ loc
            pts.append(world + direc * clearance)
        else:
            fallback = min(maxs.x - mins.x, maxs.y - mins.y) * 0.25
            if max_radius:
                fallback = min(fallback, float(max_radius))
            pts.append(center + direc * (fallback + clearance))
    ring = _clamp_ring(pts, 1.35)
    if max_radius:
        ring = _clamp_ring(ring, 1.15)
        cap = float(max_radius)
        mid = Vector((0.0, 0.0, 0.0))
        for point in ring:
            mid += point
        mid /= float(len(ring))
        capped = []
        for point in ring:
            delta = point - mid
            span = delta.xy.length
            if span > cap and span > 1e-6:
                xy = delta.xy.normalized() * cap
                point = Vector((mid.x + xy.x, mid.y + xy.y, point.z))
            capped.append(point)
        ring = capped
    return ring


def _clamp_ring(ring, max_scale=1.35):
    """Pull outlier ring points back toward the median radius."""
    acc = Vector((0.0, 0.0, 0.0))
    for point in ring:
        acc += point
    mid = acc / float(len(ring))
    radii = [(point - mid).xy.length for point in ring]
    ordered = sorted(radii)
    median = ordered[len(ordered) // 2] or 0.08
    cap = median * max_scale
    out = []
    for point, radius in zip(ring, radii):
        if radius <= cap or radius < 1e-6:
            out.append(point)
            continue
        delta = point - mid
        xy = delta.xy.normalized() * cap
        out.append(Vector((mid.x + xy.x, mid.y + xy.y, point.z)))
    return out


def prepare_garment_body():
    """Load or build the body. Returns (body, landmarks)."""
    cfg = _garment_cfg()
    mode = cfg.get("mode") or "template"
    body = None
    if mode in ("fit", "refit") and cfg.get("body_path"):
        body = import_body_glb(cfg["body_path"])
    if body is None:
        body = create_small_animal_body()
        _scale_garment_to_body(body)
    marks = extract_landmarks(body)
    _refine_stacked_body(body, marks)
    _bind_sleeve_axes(body, marks)
    mins, maxs = body_bounds(body)
    height = max(maxs.z - mins.z, 0.001)
    if cfg.get("hem") is not None:
        spec_hem = float(cfg["hem"])
        anat = marks["hem"].z
        neck = marks["neck"].z
        if anat < spec_hem < neck - height * 0.04:
            marks["hem"] = Vector((
                marks["hem"].x, marks["hem"].y, spec_hem,
            ))
    return body, marks
'''
