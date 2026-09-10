"""Import or build a garment body and sample landmarks / slices."""

CREATE_GARMENT_BODY_SRC = r'''
import math


def _garment_cfg():
    """Return the garment CONFIG dict."""
    return CONFIG.get("garment") or {}


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
    """If the body is cm-scale, shrink 1 m spec values to match."""
    cfg = _garment_cfg()
    mins, maxs = body_bounds(body)
    height = maxs.z - mins.z
    if height >= 0.35 or height < 1e-4:
        return 1.0
    scale = height / 1.0
    for key in ("clearance", "thickness", "hem", "neck"):
        if cfg.get(key) is not None:
            cfg[key] = float(cfg[key]) * scale
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
    """World AABB (mins, maxs) of one mesh."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for corner in obj.bound_box:
        world = obj.matrix_world @ Vector(corner)
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
    """Named world points from bones when present, else the AABB."""
    mins, maxs = body_bounds(obj)
    mid = (mins + maxs) * 0.5
    h = max(maxs.z - mins.z, 0.001)
    def at(t):
        return mins.z + h * t
    width = maxs.x - mins.x
    marks = {
        "neck": Vector((mid.x, mid.y, at(0.72))),
        "shoulders": Vector((mid.x, mid.y, at(0.62))),
        "shoulder_l": Vector((mins.x + width * 0.22, mid.y, at(0.60))),
        "shoulder_r": Vector((maxs.x - width * 0.22, mid.y, at(0.60))),
        "chest": Vector((mid.x, mid.y, at(0.52))),
        "belly": Vector((mid.x, mid.y, at(0.40))),
        "hips": Vector((mid.x, mid.y, at(0.28))),
        "hem": Vector((mid.x, mid.y, at(0.18))),
        "tail": Vector((mid.x, maxs.y, at(0.30))),
    }
    arm = None
    for cand in bpy.data.objects:
        if cand.type == "ARMATURE":
            arm = cand
            break
    if arm is None:
        return marks
    neck = _bone_head(arm, ("neck.x", "c_neck.x", "neck", "Neck"))
    chest = _bone_head(arm, ("spine_03.x", "spine_02.x", "spine.003"))
    belly = _bone_head(arm, ("spine_02.x", "spine_01.x", "spine.002"))
    hips = _bone_head(arm, ("c_root.x", "root.x", "hips", "Hips"))
    sl = _bone_head(arm, ("shoulder.l", "c_shoulder.l", "shoulder.L"))
    sr = _bone_head(arm, ("shoulder.r", "c_shoulder.r", "shoulder.R"))
    if neck:
        marks["neck"] = neck
    if chest:
        marks["chest"] = chest
    if belly:
        marks["belly"] = belly
    if hips:
        marks["hips"] = hips
    if sl:
        marks["shoulder_l"] = sl
    if sr:
        marks["shoulder_r"] = sr
    if sl and sr:
        marks["shoulders"] = (sl + sr) * 0.5
    return marks


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
    marks = extract_landmarks(body)
    hem = float(cfg.get("hem") if cfg.get("hem") is not None else marks["hem"].z)
    marks["hem"] = Vector((marks["hem"].x, marks["hem"].y, hem))
    return body, marks
'''
