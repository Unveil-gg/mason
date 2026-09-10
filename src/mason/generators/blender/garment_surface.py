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
        reach = 0.45 if cfg.get("sleeve") != "long" else 0.92
        for side in ("l", "r"):
            sh = marks.get("shoulder_" + side)
            wr = marks.get("wrist_" + side)
            if sh is None or wr is None:
                continue
            end = sh.lerp(wr, reach)
            rad = height * 0.12
            if _near_segment(center, sh, end, rad):
                return True
    if cfg.get("kind") == "vest":
        mid = marks["shoulders"]
        if abs(center.x - mid.x) > height * 0.22 and center.z > marks["chest"].z:
            return False
    tail = marks.get("tail")
    if tail is not None and not cfg.get("tail_opening"):
        if center.y > marks["hips"].y + height * 0.08:
            if (center - tail).length < height * 0.18:
                return False
    return True


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
    bm.to_mesh(garment.data)
    bm.free()
    if len(garment.data.polygons) < 12:
        bpy.data.objects.remove(garment, do_unlink=True)
        return None
    ease = float(cfg.get("ease_offset") or cfg.get("clearance") or 0.008)
    for vert in garment.data.vertices:
        vert.co += vert.normal * ease
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
