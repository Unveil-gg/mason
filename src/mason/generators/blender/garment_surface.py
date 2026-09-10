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


def _is_sleeve_vert(point, marks, height):
    """True if a world point sits on a short/long sleeve ray."""
    for side in ("l", "r"):
        sh = marks.get("shoulder_" + side)
        wr = marks.get("wrist_" + side)
        if sh is None or wr is None:
            continue
        end = sh.lerp(wr, 0.24)
        if _near_segment(point, sh, end, height * 0.09):
            return True
    return False


def _keep_face_center(center, marks, cfg, height):
    """Whether a world-space face center belongs on the garment."""
    hem_z = marks["hem"].z
    neck_z = marks["neck"].z
    pad = height * 0.04
    if center.z < hem_z - pad or center.z > neck_z + pad * 1.4:
        return False
    head = marks.get("head")
    if head is not None and center.z > marks["shoulders"].z:
        if (center - head).length < (center - marks["neck"]).length * 0.8:
            return False
    regions = cfg.get("body_regions") or ["torso"]
    if "upper_arms" in regions or cfg.get("sleeve") in ("short", "long"):
        reach = 0.22 if cfg.get("sleeve") != "long" else 0.92
        for side in ("l", "r"):
            sh = marks.get("shoulder_" + side)
            wr = marks.get("wrist_" + side)
            if sh is None or wr is None:
                continue
            end = sh.lerp(wr, reach)
            rad = height * 0.08
            if _near_segment(center, sh, end, rad):
                return True
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


def _tighten_sleeves(garment, marks, height):
    """Pull short-sleeve verts into a tube around the arm."""
    imw = garment.matrix_world.inverted()
    radius = height * 0.052
    chest = marks.get("chest")
    mid_x = chest.x if chest is not None else 0.0
    for side in ("l", "r"):
        sh = marks.get("shoulder_" + side)
        wr = marks.get("wrist_" + side)
        if sh is None or wr is None:
            continue
        end = sh.lerp(wr, 0.24)
        span = end - sh
        denom = max(span.length_squared, 1e-8)
        for vert in garment.data.vertices:
            world = garment.matrix_world @ vert.co
            if abs(world.x - mid_x) < height * 0.14:
                continue
            if not _near_segment(world, sh, end, height * 0.10):
                continue
            t = max(0.0, min(1.0, (world - sh).dot(span) / denom))
            axis = sh + span * t
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
        bm, edges=[e for e in bm.edges if e.is_boundary], sides=8,
    )
    bm.to_mesh(garment.data)
    bm.free()
    if len(garment.data.polygons) < 12:
        bpy.data.objects.remove(garment, do_unlink=True)
        return None
    _tighten_sleeves(garment, marks, height)
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
    meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
    shirt = meshes[0]
    shirt.name = "shirt"
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
