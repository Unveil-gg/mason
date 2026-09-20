"""Extract garment faces from the body; loft only as fallback."""

CREATE_GARMENT_SURFACE_SRC = r'''
import bmesh


def _ring_center(ring):
    """Average of ring points."""
    acc = Vector((0.0, 0.0, 0.0))
    for point in ring:
        acc += point
    return acc / float(len(ring))


def _near_segment(point, start, end, radius):
    """True if point is within radius of the start-end segment."""
    span = end - start
    denom = max(span.length_squared, 1e-8)
    t = max(0.0, min(1.0, (point - start).dot(span) / denom))
    return (point - (start + span * t)).length <= radius


def _axis_t(point, start, end):
    """Parameter of point along start-end, unclamped."""
    span = end - start
    denom = max(span.length_squared, 1e-8)
    return (point - start).dot(span) / denom


def _sleeve_reach_t():
    """0-1 along shoulder-wrist kept as sleeve mesh."""
    sleeve = _garment_cfg().get("sleeve")
    if sleeve == "long":
        return 0.92
    if sleeve == "none":
        return 0.0
    return 0.45


SLEEVE_TUBE_LOG = []


def _sleeve_axis(marks, side, body=None):
    """Arm-head to wrist. Prefers mesh axes bound from the body."""
    start = marks.get("sleeve_start_" + side)
    end = marks.get("sleeve_end_" + side)
    if start is not None and end is not None:
        return start.copy(), end.copy()
    start = marks.get("arm_" + side) or marks.get("shoulder_" + side)
    end = marks.get("wrist_" + side)
    _ = body
    return start, end


def _is_sleeve_vert(point, marks, height):
    """True if a world point sits on a short/long sleeve ray."""
    reach = _sleeve_reach_t()
    if reach <= 0.0:
        return False
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    if abs(point.x - mid) < height * 0.14:
        return False
    rad = height * 0.09
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side)
        if sh is None or wr is None:
            continue
        end = sh.lerp(wr, reach)
        if _near_segment(point, sh, end, rad):
            return True
    return False


def _is_arm_flesh(point, marks, height):
    """Arm mesh past the torso wall. Sphere sides are not arms."""
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    torso = float(marks.get("torso_half_x") or height * 0.18)
    hips = marks.get("hips")
    if hips is not None and point.z < hips.z - height * 0.02:
        return False
    head = marks.get("head")
    if head is not None and (point - head).length < height * 0.16:
        return False
    if abs(point.x - mid) < torso * 1.02:
        return False
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side)
        if sh is None or wr is None:
            continue
        span = wr - sh
        denom = max(span.length_squared, 1e-8)
        t = (point - sh).dot(span) / denom
        if t < 0.12 or t > 1.08:
            continue
        if _near_segment(point, sh, wr, height * 0.07):
            return True
    return False


def _arm_radius(body, sh, wr, height):
    """Median body radius around one shoulder-wrist axis."""
    span = wr - sh
    denom = max(span.length_squared, 1e-8)
    rads = []
    for vert in body.data.vertices:
        world = body.matrix_world @ vert.co
        t = (world - sh).dot(span) / denom
        if t < 0.50 or t > 0.85:
            continue
        axis = sh + span * t
        rad = (world - axis).length
        if rad < height * 0.07:
            rads.append(rad)
    if not rads:
        return height * 0.018
    rads.sort()
    return rads[len(rads) // 2]


def _sleeve_radius(body, marks, height):
    """Fitted tube radius: arm median plus ease."""
    ease = float(_garment_cfg().get("ease_offset") or 0.002)
    samples = []
    if body is not None:
        for side in ("l", "r"):
            sh, wr = _sleeve_axis(marks, side, body)
            if sh is not None and wr is not None:
                samples.append(_arm_radius(body, sh, wr, height))
    arm = sum(samples) / len(samples) if samples else height * 0.016
    return min(arm * 1.28 + ease * 0.35, height * 0.038)


def _axis_frame(direction):
    """Orthonormal frame with Z along direction."""
    z = direction.normalized()
    x = z.cross(Vector((0.0, 0.0, 1.0)))
    if x.length < 0.1:
        x = z.cross(Vector((0.0, 1.0, 0.0)))
    x.normalize()
    y = z.cross(x).normalized()
    return x, y, z


def _circle_pts(center, x, y, rad, segs):
    """World-space circle around center in the x/y frame."""
    pts = []
    for i in range(segs):
        ang = 6.28318530718 * i / segs
        pts.append(
            center
            + x * (math.cos(ang) * rad)
            + y * (math.sin(ang) * rad),
        )
    return pts


def _arm_radius_at(body, sh, wr, t, height):
    """Median body radius near parameter t on shoulder-wrist."""
    if body is None:
        return height * 0.018
    span = wr - sh
    denom = max(span.length_squared, 1e-8)
    rads = []
    for vert in body.data.vertices:
        world = body.matrix_world @ vert.co
        tt = (world - sh).dot(span) / denom
        if abs(tt - t) > 0.14:
            continue
        axis = sh + span * max(0.0, min(1.0, tt))
        rad = (world - axis).length
        if rad < height * 0.08:
            rads.append(rad)
    if not rads:
        return _arm_radius(body, sh, wr, height)
    rads.sort()
    return rads[int(len(rads) * 0.75)]


def _shirt_radius_at(shirt, sh, wr, t, height):
    """Shirt radius near parameter t. Used to match the armhole cut."""
    span = wr - sh
    denom = max(span.length_squared, 1e-8)
    rads = []
    for vert in shirt.data.vertices:
        world = shirt.matrix_world @ vert.co
        tt = (world - sh).dot(span) / denom
        if abs(tt - t) > 0.12:
            continue
        axis = sh + span * max(0.0, min(1.0, tt))
        rad = (world - axis).length
        if rad < height * 0.16:
            rads.append(rad)
    if not rads:
        return height * 0.058
    rads.sort()
    return rads[int(len(rads) * 0.65)]


def _append_tube(shirt, start, end, rad, segs=10):
    """Write a two-ring tube into the shirt mesh in local space."""
    _append_loft(shirt, [
        _circle_pts(start, *_axis_frame(end - start)[:2], rad, segs),
        _circle_pts(end, *_axis_frame(end - start)[:2], rad, segs),
    ])


def _append_loft(shirt, rings_world, weld=0.0008):
    """Bridge world-space rings into the shirt and weld nearby verts."""
    if len(rings_world) < 2:
        return
    segs = len(rings_world[0])
    imw = shirt.matrix_world.inverted()
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    rings = []
    for ring in rings_world:
        rings.append([bm.verts.new(imw @ p) for p in ring])
    for row in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            try:
                bm.faces.new((
                    rings[row][i], rings[row][j],
                    rings[row + 1][j], rings[row + 1][i],
                ))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld)
    bm.to_mesh(shirt.data)
    bm.free()
    shirt.data.update()


def _strip_old_sleeves(shirt, marks, height):
    """Drop every hanging sleeve vert. Flat cones miss the arm ray."""
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    torso = float(marks.get("torso_half_x") or height * 0.18)
    hips = marks.get("hips")
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    kill = []
    for vert in bm.verts:
        world = shirt.matrix_world @ vert.co
        if hips is not None and world.z < hips.z - height * 0.02:
            continue
        # torso_half_x can include the arm stubs. Cap to the body ball
        # so the flat 062 cones actually get deleted.
        keep = min(torso * 1.04, height * 0.255)
        if abs(world.x - mid) <= keep:
            continue
        kill.append(vert)
    if kill and len(kill) < len(bm.verts) * 0.70:
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        bm.to_mesh(shirt.data)
    bm.free()
    shirt.data.update()


def _log_sleeve_axes(marks, height, body=None):
    """Record sleeve axes for validation without adding mesh."""
    global SLEEVE_TUBE_LOG
    SLEEVE_TUBE_LOG = []
    reach = _sleeve_reach_t()
    if reach <= 0.0:
        return
    rad = _sleeve_radius(body, marks, height)
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side, body)
        if sh is None or wr is None:
            continue
        end = sh.lerp(wr, reach)
        SLEEVE_TUBE_LOG.append({
            "side": side,
            "start": [float(sh.x), float(sh.y), float(sh.z)],
            "end": [float(end.x), float(end.y), float(end.z)],
            "radius": float(rad),
            "length": float((end - sh).length),
        })


def _add_sleeve_tubes(shirt, marks, height, body=None):
    """Replace hanging cones with chubby tubes. Leaves the torso."""
    global SLEEVE_TUBE_LOG
    SLEEVE_TUBE_LOG = []
    reach = _sleeve_reach_t()
    if reach <= 0.0:
        return shirt
    stubs = {}
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side, body)
        if sh is None or wr is None:
            continue
        stubs[side] = _shirt_radius_at(shirt, sh, wr, 0.06, height)
    _strip_old_sleeves(shirt, marks, height)
    cfg = _garment_cfg()
    sleeve = cfg.get("sleeve")
    ease = float(cfg.get("ease_offset") or 0.002)
    n_rings = 5 if sleeve == "long" else 4
    segs = 14
    cap = height * (0.42 if sleeve == "long" else 0.28)
    min_len = height * (0.28 if sleeve == "long" else 0.16)
    floor = height * 0.055
    rad_cap = height * 0.095
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side, body)
        if sh is None or wr is None:
            continue
        end = sh.lerp(wr, reach)
        delta = end - sh
        if delta.length < min_len:
            direction = wr - sh
            if direction.length > 1e-8:
                end = sh + direction.normalized() * min_len
                delta = end - sh
        if delta.length > cap:
            end = sh + delta.normalized() * cap
            delta = end - sh
        if delta.length < height * 0.05:
            continue
        x, y, _z = _axis_frame(delta)
        stub = stubs.get(side, floor)
        rings = []
        last_rad = floor
        for i in range(n_rings):
            t = i / float(n_rings - 1)
            # First ring sits on the armhole so the cut stays covered.
            along = 0.04 + t * 0.96
            center = sh.lerp(end, along)
            arm = _arm_radius_at(body, sh, wr, along * reach, height)
            rad = max(arm * 1.20 + ease * 0.5, floor)
            rad = min(rad, rad_cap)
            if i == 0:
                rad = max(rad, stub * 0.95, floor * 1.15)
            else:
                rad = rad * (1.0 - 0.10 * t)
            last_rad = rad
            ring = _circle_pts(center, x, y, rad, segs)
            if i == n_rings - 1:
                for pt in ring:
                    if pt.z < center.z:
                        pt.z -= height * 0.005
            rings.append(ring)
        origin = sh.lerp(end, 0.04)
        _append_loft(shirt, rings, weld=height * 0.006)
        SLEEVE_TUBE_LOG.append({
            "side": side,
            "start": [float(origin.x), float(origin.y), float(origin.z)],
            "end": [float(end.x), float(end.y), float(end.z)],
            "radius": float(last_rad),
            "length": float(delta.length),
        })
    return shirt


def _clip_batwings(shirt, marks, height, body, keep_tubes=False):
    """Delete cape verts past the torso. Sleeves are tubes, not wings."""
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    torso = float(marks.get("torso_half_x") or height * 0.18)
    hips_z = marks["hips"].z
    reach = _sleeve_reach_t()
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    kill = []
    for vert in bm.verts:
        world = shirt.matrix_world @ vert.co
        ax = abs(world.x - mid)
        if ax < torso * 0.90:
            continue
        if _is_sleeve_vert(world, marks, height):
            continue
        if keep_tubes:
            near_tube = False
            for side in ("l", "r"):
                sh, wr = _sleeve_axis(marks, side)
                if sh is None or wr is None:
                    continue
                end = sh.lerp(wr, reach)
                if _near_segment(world, sh, end, height * 0.06):
                    near_tube = True
                    break
            if near_tube:
                continue
        hang = False
        for side in ("l", "r"):
            sh, wr = _sleeve_axis(marks, side)
            if sh is None:
                continue
            if world.z < sh.z - height * 0.05 and ax > torso * 1.18:
                hang = True
        if hang:
            kill.append(vert)
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        bm.to_mesh(shirt.data)
    bm.free()
    shirt.data.update()


def _keep_face_center(center, marks, cfg, height):
    """Whether a world-space face center belongs on the garment."""
    hem_z = marks["hem"].z
    neck_z = marks["neck"].z
    pad = height * 0.04
    if center.z < hem_z - pad or center.z > neck_z + pad * 0.20:
        return False
    on_sleeve = _is_sleeve_vert(center, marks, height)
    on_arm = _is_arm_flesh(center, marks, height)
    if _garment_pipeline() == "stylized":
        if on_sleeve:
            return True
        if on_arm:
            return False
    elif on_sleeve or on_arm:
        return False
    head = marks.get("head")
    if head is not None and center.z > neck_z:
        if (center - head).length < (center - marks["neck"]).length * 0.9:
            return False
    if cfg.get("kind") == "vest":
        mid = marks["shoulders"]
        if abs(center.x - mid.x) > height * 0.22 and center.z > marks["chest"].z:
            return False
    tail = marks.get("tail")
    if tail is not None:
        near_tail = (center - tail).length < height * 0.11
        if cfg.get("tail_opening") and near_tail:
            return False
        if not cfg.get("tail_opening"):
            if center.y > marks["hips"].y + height * 0.08 and near_tail:
                return False
    return True


def _half_x_lut(obj, mid, zmin, zmax, marks, height, bins=10):
    """Per-Z torso half-width, ignoring arm verts."""
    lut = [0.0] * bins
    span = max(zmax - zmin, 1e-6)
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if _is_arm_flesh(world, marks, height):
            continue
        if _is_sleeve_vert(world, marks, height):
            continue
        t = (world.z - zmin) / span
        if 0.0 <= t <= 1.0:
            i = min(int(t * (bins - 1)), bins - 1)
            lut[i] = max(lut[i], abs(world.x - mid))
    filled = max(lut) if any(lut) else 0.0
    lut = [v if v > 0.0 else filled * 0.5 for v in lut]
    return lut, zmin, span


def _lut_at(lut, zmin, span, z):
    """Half-width at world Z from a `_half_x_lut`."""
    t = max(0.0, min(1.0, (z - zmin) / span))
    i = min(int(t * (len(lut) - 1)), len(lut) - 1)
    return lut[i]


def _tighten_sleeves(garment, marks, height, body=None):
    """Pinch sleeve verts to a tube around the arm axis."""
    imw = garment.matrix_world.inverted()
    radius = _sleeve_radius(body, marks, height)
    chest = marks.get("chest")
    mid_x = chest.x if chest is not None else 0.0
    reach = _sleeve_reach_t()
    for side in ("l", "r"):
        sh, wr = _sleeve_axis(marks, side)
        if sh is None or wr is None or reach <= 0.0:
            continue
        end = sh.lerp(wr, reach)
        axis_span = end - sh
        denom = max(axis_span.length_squared, 1e-8)
        for vert in garment.data.vertices:
            world = garment.matrix_world @ vert.co
            if abs(world.x - mid_x) < height * 0.17:
                continue
            if not _near_segment(world, sh, end, height * 0.13):
                continue
            t = max(0.0, min(1.0, (world - sh).dot(axis_span) / denom))
            axis = sh + axis_span * t
            radial = world - axis
            if radial.length <= radius or radial.length < 1e-8:
                continue
            world = axis + radial.normalized() * radius
            vert.co = imw @ world
    garment.data.update()


def _bisect_fill(obj, origin, normal, drop_below):
    """Cut obj on a plane, drop one side, and fill the cap."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(
        plane_co=origin,
        plane_no=normal,
        clear_inner=drop_below,
        clear_outer=not drop_below,
        use_fill=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def _torso_origin(body, marks):
    """Centroid of torso-band verts, ignoring arms."""
    chest = marks.get("chest")
    mid_x = chest.x if chest is not None else 0.0
    torso = float(marks.get("torso_half_x") or 0.02)
    z0 = marks["hem"].z
    z1 = marks["neck"].z
    xs, ys, zs = [], [], []
    for vert in body.data.vertices:
        world = body.matrix_world @ vert.co
        if world.z < z0 or world.z > z1:
            continue
        if abs(world.x - mid_x) > torso * 1.05:
            continue
        xs.append(world.x)
        ys.append(world.y)
        zs.append(world.z)
    if not xs:
        mins, maxs = body_bounds(body)
        return Vector((
            mid_x, (mins.y + maxs.y) * 0.5, (z0 + z1) * 0.5,
        ))
    n = float(len(xs))
    return Vector((sum(xs) / n, sum(ys) / n, sum(zs) / n))


def _ray_on_body(body, origin, direction, reach):
    """World hit of a ray in object space."""
    imw = body.matrix_world.inverted()
    rot = body.matrix_world.to_3x3()
    local_d = (rot.inverted() @ direction).normalized()
    hit = body.ray_cast(imw @ origin, local_d, distance=reach)
    ok, loc, nrm, _idx = hit
    if not ok:
        return None, None
    return body.matrix_world @ loc, (rot @ nrm).normalized()


def _torso_shell_radii(body, marks, gap):
    """Raycast the body surface from the torso center."""
    origin = _torso_origin(body, marks)
    mins, maxs = body_bounds(body)
    reach = max((maxs - mins).length, 0.05)
    xs, ys = [], []
    rays = (
        (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
        (0.7, 0.7, 0.0), (-0.7, 0.7, 0.0),
        (0.7, -0.7, 0.0), (-0.7, -0.7, 0.0),
    )
    for raw in rays:
        loc, _n = _ray_on_body(body, origin, Vector(raw), reach)
        if loc is None:
            continue
        xs.append(abs(loc.x - origin.x))
        ys.append(abs(loc.y - origin.y))
    torso = float(marks.get("torso_half_x") or 0.02)
    rx = max(max(xs) if xs else 0.0, torso) + gap
    ry = max(max(ys) if ys else 0.0, torso * 0.65) + gap
    rz = (marks["neck"].z - marks["hem"].z) * 0.5 + gap
    return rx, ry, rz, origin.x, origin.y


def _extract_stylized_shell(body, marks):
    """Closed hull sized from body raycasts, plus a thin ease."""
    cfg = _garment_cfg()
    mins, maxs = body_bounds(body)
    height = max(maxs.z - mins.z, 0.001)
    gap = min(
        float(cfg.get("ease_offset") or 0.002),
        height * 0.012,
    )
    rx, ry, rz, mid_x, mid_y = _torso_shell_radii(body, marks, gap)
    hem_z = marks["hem"].z
    neck_z = marks["neck"].z
    mid_z = (hem_z + neck_z) * 0.5
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0,
        location=(mid_x, mid_y, mid_z),
        segments=24,
        ring_count=16,
    )
    garment = bpy.context.active_object
    garment.name = cfg.get("kind") or "shirt"
    garment.scale = (
        max(rx, height * 0.06),
        max(ry, height * 0.05),
        max(rz, height * 0.06),
    )
    bpy.ops.object.transform_apply(scale=True)
    _bisect_fill(
        garment, (mid_x, mid_y, hem_z), (0.0, 0.0, 1.0), True,
    )
    _bisect_fill(
        garment, (mid_x, mid_y, neck_z), (0.0, 0.0, 1.0), False,
    )
    shade_smooth(garment)
    return garment


def extract_garment_surface(body, marks):
    """Duplicate body faces in garment regions and offset them."""
    if _garment_pipeline() == "stylized":
        return _extract_stylized_shell(body, marks)
    cfg = _garment_cfg()
    mins, maxs = body_bounds(body)
    height = max(maxs.z - mins.z, 0.001)
    garment = body.copy()
    garment.data = body.data.copy()
    garment.name = cfg.get("kind") or "shirt"
    bpy.context.collection.objects.link(garment)
    garment.parent = None
    garment.matrix_world = body.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    drop = []
    for face in bm.faces:
        center = garment.matrix_world @ face.calc_center_median()
        if not _keep_face_center(center, marks, cfg, height):
            drop.append(face)
    if drop and len(drop) < len(bm.faces):
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=height * 0.002)
    bmesh.ops.holes_fill(
        bm, edges=[e for e in bm.edges if e.is_boundary], sides=12,
    )
    bm.to_mesh(garment.data)
    bm.free()
    if len(garment.data.polygons) < 12:
        bpy.data.objects.remove(garment, do_unlink=True)
        return None
    _clip_batwings(garment, marks, height, body)
    bm = bmesh.new()
    bm.from_mesh(garment.data)
    bmesh.ops.holes_fill(
        bm, edges=[e for e in bm.edges if e.is_boundary], sides=12,
    )
    bm.to_mesh(garment.data)
    bm.free()
    if _garment_pipeline() != "stylized":
        _tighten_sleeves(garment, marks, height, body)
    ease = float(cfg.get("ease_offset") or cfg.get("clearance") or 0.008)
    torso_ease = ease * 1.25
    sleeve_ease = ease * 0.7
    for vert in garment.data.vertices:
        world = garment.matrix_world @ vert.co
        amt = sleeve_ease if _is_sleeve_vert(
            world, marks, height,
        ) else torso_ease
        vert.co += vert.normal * amt
    garment.data.update()
    shade_smooth(garment)
    return garment


def import_garment_source(path):
    """Import a previous garment GLB as the surface mesh."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [
        o for o in bpy.data.objects
        if o not in before and o.type == "MESH"
        and not o.name.startswith("_mason_")
    ]
    if not meshes:
        return None

    def _span(obj):
        mins, maxs = body_bounds(obj)
        return (maxs - mins).length

    named = [o for o in meshes if "shirt" in o.name.lower()]
    small = [o for o in meshes if 0.01 < _span(o) < 0.5]
    pool = named or small or meshes
    pool.sort(key=lambda o: len(o.data.vertices), reverse=True)
    shirt = pool[0]
    shirt.name = "shirt"
    for extra in meshes:
        if extra != shirt:
            bpy.data.objects.remove(extra, do_unlink=True)
    return shirt


def _fit_ring_width(ring, width):
    """Scale a ring in XY so its max span matches width."""
    center = _ring_center(ring)
    span = 0.0
    for point in ring:
        span = max(span, (point - center).xy.length * 2.0)
    if span < 1e-6:
        return ring
    scale = width / span
    out = []
    for point in ring:
        delta = point - center
        out.append(Vector((
            center.x + delta.x * scale,
            center.y + delta.y * scale,
            point.z,
        )))
    return out


def loft_rings(rings, name):
    """Bridge equal-length rings with quads. Returns the object."""
    mesh = bpy.data.meshes.new(name)
    verts = []
    faces = []
    n = len(rings[0])
    for ring in rings:
        verts.extend([(p.x, p.y, p.z) for p in ring])
    for row in range(len(rings) - 1):
        for i in range(n):
            a = row * n + i
            b = row * n + (i + 1) % n
            c = (row + 1) * n + (i + 1) % n
            d = (row + 1) * n + i
            faces.append((a, b, c, d))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def loft_garment(body, marks):
    """Fallback tube from body slices when extract yields too little."""
    cfg = _garment_cfg()
    clearance = float(cfg.get("ease_offset") or cfg.get("clearance") or 0.012)
    n = 16
    zs = [
        marks["hem"].z, marks["hips"].z, marks["belly"].z,
        marks["chest"].z, marks["shoulders"].z, marks["neck"].z,
    ]
    rings = [slice_ring(body, z, n, clearance) for z in zs]
    rings[-1] = _fit_ring_width(rings[-1], float(cfg.get("neck") or 0.14))
    shirt = loft_rings(rings, cfg.get("kind") or "shirt")
    shade_smooth(shirt)
    return shirt
'''
