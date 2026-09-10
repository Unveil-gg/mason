"""Weight transfer, deformation poses, and garment fit metrics."""

CREATE_GARMENT_RIG_SRC = r'''
FIT_METRICS = {}


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
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    shirt.parent = arm
    shirt.parent_type = "ARMATURE"
    shirt.matrix_parent_inverse = arm.matrix_world.inverted()


def hide_covered_body(body, marks):
    """Mark body faces under the garment. Body is not exported."""
    cfg = _garment_cfg()
    if not cfg.get("hide_covered"):
        return 0
    hem_z = marks["hem"].z
    neck_z = marks["neck"].z
    count = 0
    for poly in body.data.polygons:
        center = body.matrix_world @ poly.center
        if hem_z <= center.z <= neck_z:
            poly.hide = True
            count += 1
    return count


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


def _opening_width(obj, z, band=None):
    """Largest XY span of verts near world Z."""
    mins, maxs = body_bounds(obj)
    if band is None:
        band = max((maxs.z - mins.z) * 0.08, 0.002)
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


def _rotate_named(arm, names, axis, angle):
    """Rotate the first matching pose bone on axis 0/1/2."""
    for name in names:
        bone = arm.pose.bones.get(name)
        if bone is None:
            continue
        bone.rotation_mode = "XYZ"
        bone.rotation_euler[axis] = angle
        return True
    return False


def _apply_pose(arm, kind):
    """Deformation poses. Prefer Auto-Rig Pro control bones."""
    if kind == "arms_forward":
        _rotate_named(arm, ("c_arm_fk.l", "arm.l"), 0, -0.7)
        _rotate_named(arm, ("c_arm_fk.r", "arm.r"), 0, -0.7)
    elif kind == "arms_spread":
        _rotate_named(arm, ("c_arm_fk.l", "arm.l"), 2, 0.8)
        _rotate_named(arm, ("c_arm_fk.r", "arm.r"), 2, -0.8)
    elif kind == "arms_up":
        _rotate_named(arm, ("c_arm_fk.l", "arm.l"), 0, -1.3)
        _rotate_named(arm, ("c_arm_fk.r", "arm.r"), 0, -1.3)
    elif kind == "elbow_bend":
        _rotate_named(arm, ("c_forearm_fk.l", "forearm.l"), 0, -1.2)
        _rotate_named(arm, ("c_forearm_fk.r", "forearm.r"), 0, -1.2)
    elif kind == "crouch":
        _rotate_named(arm, ("c_thigh_fk.l", "thigh.l"), 0, 0.9)
        _rotate_named(arm, ("c_thigh_fk.r", "thigh.r"), 0, 0.9)
    elif kind == "twist":
        _rotate_named(arm, ("c_spine_02.x", "spine_02.x"), 2, 0.55)
    elif kind == "leg_raise":
        _rotate_named(arm, ("c_thigh_fk.l", "thigh.l"), 0, -0.9)


def run_pose_tests(shirt, body):
    """Score penetration across a bind-pose stress set."""
    arm = _find_armature()
    if arm is None:
        return {}
    names = (
        "neutral", "arms_forward", "arms_spread", "arms_up",
        "elbow_bend", "crouch", "twist", "leg_raise",
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
    poses = {}
    if cfg.get("pose_tests") and _find_armature():
        poses = run_pose_tests(shirt, body)
    FIT_METRICS = {
        "clearance_min": float(min(gaps) if gaps else 0.0),
        "penetration": float(pen),
        "opening_neck": float(_opening_width(shirt, marks["neck"].z)),
        "opening_cuffs": float(_opening_width(
            shirt, marks.get("wrist_l", marks["shoulders"]).z,
        )),
        "pose_scores": poses,
        "method": "extract",
    }
    return FIT_METRICS


def default_garment_attachments(marks):
    """Fill attach sockets from landmarks when the spec is empty."""
    if CONFIG.get("attachments"):
        return
    sockets = [
        ("neck", marks["neck"]),
        ("hem", marks["hem"]),
    ]
    for key, name in (("wrist_l", "cuff_l"), ("wrist_r", "cuff_r")):
        sockets.append((name, marks.get(key, marks["shoulder_" + key[-1]])))
    CONFIG["attachments"] = [
        {"name": n, "location": list(p), "rotation": [0, 0, 0]}
        for n, p in sockets if p is not None
    ]


def build_garment():
    """Analyze, extract or refit, details, fit, weights, tests."""
    cfg = _garment_cfg()
    body, marks = prepare_garment_body()
    shirt = None
    if cfg.get("mode") == "refit" and cfg.get("source_path"):
        shirt = import_garment_source(cfg["source_path"])
    method = "extract"
    if shirt is None:
        shirt = extract_garment_surface(body, marks)
    if shirt is None:
        shirt = loft_garment(body, marks)
        method = "loft"
    add_garment_details(shirt, marks)
    fit_garment(shirt, body, marks)
    apply_garment_material(shirt)
    transfer_weights(shirt, body)
    hide_covered_body(body, marks)
    score_garment_fit(shirt, body, marks)
    FIT_METRICS["method"] = method
    default_garment_attachments(marks)
    return shirt
'''
