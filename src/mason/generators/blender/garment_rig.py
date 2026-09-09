"""Weight transfer, pose checks, and garment fit metrics."""

CREATE_GARMENT_RIG_SRC = r'''
FIT_METRICS = {}


def _find_armature():
    """First armature in the scene, or None."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def transfer_weights(shirt, body):
    """Copy vertex groups from the body and parent to its armature."""
    arm = _find_armature()
    if arm is None:
        return
    if body.vertex_groups:
        xfer = shirt.modifiers.new("Weights", "DATA_TRANSFER")
        xfer.object = body
        xfer.use_vert_data = True
        xfer.data_types_verts = {"VGROUP_WEIGHTS"}
        xfer.vert_mapping = "POLYINTERP_NEAREST"
        xfer.layers_vgroup_select_src = "ALL"
        xfer.layers_vgroup_select_dst = "NAME"
        bpy.context.view_layer.objects.active = shirt
        bpy.ops.object.modifier_apply(modifier="Weights")
    shirt.parent = arm
    shirt.parent_type = "ARMATURE"


def _signed_gaps(shirt, body):
    """Signed distances from outer shirt verts to the body surface."""
    imw = body.matrix_world.inverted()
    mins, maxs = body_bounds(shirt)
    center = (mins + maxs) * 0.5
    to_world = shirt.matrix_world.to_3x3()
    gaps = []
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        normal = (to_world @ vert.normal).normalized()
        if normal.dot(world - center) < 0.0:
            continue
        local = imw @ world
        hit, loc, nrm, _idx = body.closest_point_on_mesh(local)
        if not hit:
            continue
        world_hit = body.matrix_world @ loc
        world_nrm = (body.matrix_world.to_3x3() @ nrm).normalized()
        gaps.append((world - world_hit).dot(world_nrm))
    return gaps


def _opening_width(obj, z, band=0.04):
    """Largest XY span of verts near world Z."""
    xs, ys = [], []
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if abs(world.z - z) <= band:
            xs.append(world.x)
            ys.append(world.y)
    if not xs:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _reset_pose(arm):
    """Clear pose-bone Euler rotations."""
    for bone in arm.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)


def _apply_pose(arm, kind):
    """Heuristic limb poses from bone name hints."""
    for bone in arm.pose.bones:
        name = bone.name.lower()
        bone.rotation_mode = "XYZ"
        if kind == "limbs_forward" and ("arm" in name or "hand" in name):
            bone.rotation_euler[0] = -0.55
        elif kind == "limbs_out" and "arm" in name:
            sign = -1.0 if ("l" in name or "left" in name) else 1.0
            bone.rotation_euler[2] = 0.7 * sign
        elif kind == "crouch" and ("leg" in name or "thigh" in name):
            bone.rotation_euler[0] = 0.75
        elif kind == "extreme" and "arm" in name:
            bone.rotation_euler[0] = -1.1


def run_pose_tests(shirt, body):
    """Score penetration in a small pose set. Restores rest pose."""
    arm = _find_armature()
    if arm is None:
        return {}
    names = (
        "neutral", "limbs_forward", "limbs_out", "crouch", "extreme",
    )
    scores = {}
    total = max(len(shirt.data.vertices), 1)
    for name in names:
        _reset_pose(arm)
        if name != "neutral":
            _apply_pose(arm, name)
        bpy.context.view_layer.update()
        gaps = _signed_gaps(shirt, body)
        pen = sum(1 for g in gaps if g < -0.002) / total
        scores[name] = {"penetration": pen, "pinch": 0.0}
    _reset_pose(arm)
    bpy.context.view_layer.update()
    return scores


def score_garment_fit(shirt, body, marks):
    """Write FIT_METRICS for metadata and validation."""
    global FIT_METRICS
    cfg = _garment_cfg()
    gaps = _signed_gaps(shirt, body)
    total = max(len(shirt.data.vertices), 1)
    pen = sum(1 for g in gaps if g < -0.002) / total
    clear = min(gaps) if gaps else 0.0
    cuffs = 1.0
    if cfg.get("sleeve") == "short":
        cuffs = _opening_width(shirt, marks["shoulders"].z)
    poses = {}
    if cfg.get("pose_tests") and _find_armature():
        poses = run_pose_tests(shirt, body)
    FIT_METRICS = {
        "clearance_min": float(clear),
        "penetration": float(pen),
        "opening_neck": float(_opening_width(shirt, marks["neck"].z)),
        "opening_cuffs": float(cuffs),
        "pose_scores": poses,
    }
    return FIT_METRICS


def default_garment_attachments(marks):
    """Fill attach sockets from landmarks when the spec is empty."""
    if CONFIG.get("attachments"):
        return
    CONFIG["attachments"] = [
        {"name": "neck", "location": list(marks["neck"]), "rotation": [0, 0, 0]},
        {"name": "hem", "location": list(marks["hem"]), "rotation": [0, 0, 0]},
        {
            "name": "cuff_l",
            "location": list(marks["shoulder_l"]),
            "rotation": [0, 0, 0],
        },
        {
            "name": "cuff_r",
            "location": list(marks["shoulder_r"]),
            "rotation": [0, 0, 0],
        },
    ]


def build_garment():
    """Body, loft or refit, fit, materials, weights, metrics."""
    cfg = _garment_cfg()
    body, marks = prepare_garment_body()
    shirt = None
    if cfg.get("mode") == "refit" and cfg.get("source_path"):
        shirt = import_garment_source(cfg["source_path"])
    if shirt is None:
        shirt = loft_garment(body, marks)
    fit_garment(shirt, body, marks)
    apply_garment_material(shirt)
    transfer_weights(shirt, body)
    score_garment_fit(shirt, body, marks)
    default_garment_attachments(marks)
    return shirt
'''
