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
    rad = height * 0.08
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


def _append_tube(shirt, start, end, rad, segs=10):
    """Write a tube into the shirt mesh in local space."""
    imw = shirt.matrix_world.inverted()
    a = imw @ start
    b = imw @ end
    axis = b - a
    if axis.length < 1e-8:
        return
    z = axis.normalized()
    x = z.cross(Vector((0.0, 0.0, 1.0)))
    if x.length < 0.1:
        x = z.cross(Vector((0.0, 1.0, 0.0)))
    x.normalize()
    y = z.cross(x).normalized()
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    rings = []
    for center in (a, b):
        ring = []
        for i in range(segs):
            ang = 6.28318530718 * i / segs
            off = x * (math.cos(ang) * rad) + y * (math.sin(ang) * rad)
            ring.append(bm.verts.new(center + off))
        rings.append(ring)
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((
            rings[0][i], rings[0][j], rings[1][j], rings[1][i],
        ))
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
    """Join arm-aligned cylinders to the wrists. Returns shirt."""
    global SLEEVE_TUBE_LOG
    SLEEVE_TUBE_LOG = []
    reach = _sleeve_reach_t()
    if reach <= 0.0:
        return shirt
    extras = []
    rad = _sleeve_radius(body, marks, height)
    sleeve = _garment_cfg().get("sleeve")
    cap = height * (0.42 if sleeve == "long" else 0.28)
    min_len = height * (0.28 if sleeve == "long" else 0.16)
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
        bpy.ops.mesh.primitive_cylinder_add(
            radius=rad,
            depth=delta.length,
            location=sh.lerp(end, 0.5),
            vertices=10,
        )
        cyl = bpy.context.active_object
        cyl.rotation_euler = delta.normalized().to_track_quat(
            "Z", "Y",
        ).to_euler()
        bpy.ops.object.transform_apply(rotation=True, scale=True)
        extras.append(cyl)
        SLEEVE_TUBE_LOG.append({
            "side": side,
            "start": [float(sh.x), float(sh.y), float(sh.z)],
            "end": [float(end.x), float(end.y), float(end.z)],
            "radius": float(rad),
            "length": float(delta.length),
        })
    if not extras:
        return shirt
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    for extra in extras:
        extra.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.object.join()
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
    if _is_sleeve_vert(center, marks, height):
        return False
    if _is_arm_flesh(center, marks, height):
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


def extract_garment_surface(body, marks):
    """Duplicate body faces in garment regions and offset them."""
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
