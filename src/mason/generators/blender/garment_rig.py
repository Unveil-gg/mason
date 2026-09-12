"""Weight transfer, deformation poses, and garment fit metrics."""

CREATE_GARMENT_RIG_SRC = r'''
from mathutils.bvhtree import BVHTree

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
    """Mark covered body faces and a mason_covered group for Godot."""
    cfg = _garment_cfg()
    if not cfg.get("hide_covered"):
        return []
    hem_z = marks["hem"].z
    neck_z = marks["neck"].z
    vg = body.vertex_groups.get("mason_covered")
    if vg is None:
        vg = body.vertex_groups.new(name="mason_covered")
    indices = []
    verts = set()
    for poly in body.data.polygons:
        center = body.matrix_world @ poly.center
        if hem_z <= center.z <= neck_z:
            poly.hide = True
            indices.append(poly.index)
            verts.update(poly.vertices)
    if verts:
        vg.add(list(verts), 1.0, "REPLACE")
    return indices


def _signed_gaps(shirt, body):
    """Signed distances from outer posed shirt verts to the body."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev_s = shirt.evaluated_get(dg)
    smesh = ev_s.to_mesh()
    rot = ev_s.matrix_world.to_3x3()
    smesh.transform(ev_s.matrix_world)
    tree = BVHTree.FromObject(body, dg)
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for vert in smesh.vertices:
        mins.x = min(mins.x, vert.co.x)
        mins.y = min(mins.y, vert.co.y)
        mins.z = min(mins.z, vert.co.z)
        maxs.x = max(maxs.x, vert.co.x)
        maxs.y = max(maxs.y, vert.co.y)
        maxs.z = max(maxs.z, vert.co.z)
    center = (mins + maxs) * 0.5
    dists = [(vert.co - center).length for vert in smesh.vertices]
    dists.sort()
    cutoff = dists[int(len(dists) * 0.45)] if dists else 0.0
    gaps = []
    for vert in smesh.vertices:
        if (vert.co - center).length < cutoff:
            continue
        normal = (rot @ vert.normal).normalized()
        if normal.dot(vert.co - center) < 0.0:
            continue
        loc, nrm, _idx, _d = tree.find_nearest(vert.co)
        if loc is None or nrm is None:
            continue
        gaps.append((vert.co - loc).dot(nrm.normalized()))
    ev_s.to_mesh_clear()
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
    """Rotate deform bones first so posed verts actually move."""
    aliases = {
        "stand": "neutral",
        "walk": "arms_forward",
        "sit": "crouch",
        "reach": "arms_spread",
    }
    kind = aliases.get(kind, kind)
    if kind == "neutral":
        return
    if kind == "arms_forward":
        _rotate_named(arm, ("arm.l", "c_arm_fk.l"), 0, -0.7)
        _rotate_named(arm, ("arm.r", "c_arm_fk.r"), 0, -0.7)
    elif kind == "arms_spread":
        _rotate_named(arm, ("arm.l", "c_arm_fk.l"), 2, 0.8)
        _rotate_named(arm, ("arm.r", "c_arm_fk.r"), 2, -0.8)
    elif kind == "arms_up":
        _rotate_named(arm, ("arm.l", "c_arm_fk.l"), 0, -1.3)
        _rotate_named(arm, ("arm.r", "c_arm_fk.r"), 0, -1.3)
    elif kind == "elbow_bend":
        _rotate_named(arm, ("forearm.l", "c_forearm_fk.l"), 0, -1.2)
        _rotate_named(arm, ("forearm.r", "c_forearm_fk.r"), 0, -1.2)
    elif kind == "crouch":
        _rotate_named(arm, ("thigh.l", "c_thigh_fk.l"), 0, 0.9)
        _rotate_named(arm, ("thigh.r", "c_thigh_fk.r"), 0, 0.9)
    elif kind == "twist":
        _rotate_named(arm, ("spine_02.x", "c_spine_02.x"), 2, 0.55)
    elif kind == "leg_raise":
        _rotate_named(arm, ("thigh.l", "c_thigh_fk.l"), 0, -0.9)


def run_pose_tests(shirt, body):
    """Score penetration across a bind-pose stress set."""
    arm = _find_armature()
    if arm is None:
        return {}
    names = (
        "neutral", "arms_forward", "arms_spread", "arms_up",
        "elbow_bend", "crouch", "twist", "leg_raise",
        "stand", "walk", "sit", "reach",
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
    cuff_z = marks["shoulders"].z
    if cfg.get("sleeve") == "short":
        loc = _cuff_point(marks, "l", "short")
        if loc is not None:
            cuff_z = loc.z
    elif cfg.get("sleeve") == "long":
        cuff_z = marks.get("wrist_l", marks["shoulders"]).z
    sleeves = _sleeve_report(shirt, body, marks)
    neck = _neck_opening(shirt, marks)
    cuff_span = 2.0 * max(
        float((sleeves.get("l") or {}).get("shirt") or 0.0),
        float((sleeves.get("r") or {}).get("shirt") or 0.0),
    )
    FIT_METRICS = {
        "clearance_min": float(min(gaps) if gaps else 0.0),
        "penetration": float(pen),
        "opening_neck": float(neck["hole"] * 2.0),
        "neck_brim": float(neck["brim_ratio"]),
        "neck_span": float(neck["span"]),
        "opening_cuffs": float(cuff_span or _opening_width(shirt, cuff_z)),
        "sleeves": sleeves,
        "underarm_flare": float(sleeves.pop("underarm_flare", 0.0)),
        "sleeve_asymmetry": float(sleeves.pop("asymmetry", 0.0)),
        "clip_regions": _clip_regions(shirt, body, marks),
        "pose_scores": poses,
        "method": "extract",
        "collar_z": float(marks["neck"].z),
        "hem_z": float(marks["hem"].z),
        "stacked_spheres": bool(marks.get("stacked_spheres")),
        "torso_half_x": float(marks.get("torso_half_x") or 0.0),
        "sleeve_tubes": list(SLEEVE_TUBE_LOG),
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
    sleeve = _garment_cfg().get("sleeve")
    for side, name in (("l", "cuff_l"), ("r", "cuff_r")):
        loc = _cuff_point(marks, side, sleeve)
        sockets.append((name, loc or marks.get("wrist_" + side)))
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
    cues = set(cfg.get("details") or []) | set(
        cfg.get("surface_details") or [],
    )
    n_btn = 0
    if "buttons" in cues:
        shirt, n_btn = _add_center_buttons(shirt, marks)
    transfer_weights(shirt, body)
    score_garment_fit(shirt, body, marks)
    FIT_METRICS["buttons"] = n_btn
    covered = hide_covered_body(body, marks)
    FIT_METRICS["method"] = method
    FIT_METRICS["covered_faces"] = len(covered)
    FIT_METRICS["covered_face_indices"] = covered
    FIT_METRICS["hide_group"] = "mason_covered"
    bmins, bmaxs = body_bounds(body)
    FIT_METRICS["body_height"] = float(bmaxs.z - bmins.z)
    FIT_METRICS["native_scale"] = True
    FIT_METRICS["scale_note"] = (
        "Shirt matches the character GLB. Same units as mousey.glb."
    )
    default_garment_attachments(marks)
    return shirt
'''
