"""Loft a shirt, tunic, or vest from body slice rings."""

CREATE_GARMENT_SURFACE_SRC = r'''
def _ring_center(ring):
    """Average of ring points."""
    acc = Vector((0.0, 0.0, 0.0))
    for point in ring:
        acc += point
    return acc / float(len(ring))


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


def _stylize_ring(ring, amount):
    """Blend a slice toward a smooth ellipse."""
    if amount <= 0.0:
        return ring
    center = _ring_center(ring)
    xs = [abs(p.x - center.x) for p in ring]
    ys = [abs(p.y - center.y) for p in ring]
    rx = max(xs) if xs else 0.1
    ry = max(ys) if ys else 0.1
    n = len(ring)
    out = []
    for i, point in enumerate(ring):
        ang = 2.0 * math.pi * i / n
        ellipse = Vector((
            center.x + math.cos(ang) * rx,
            center.y + math.sin(ang) * ry,
            point.z,
        ))
        out.append(point.lerp(ellipse, amount))
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
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


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


def _select_sleeve_verts(obj, side, z_mid):
    """Select upper-side verts for a connected sleeve extrude."""
    worlds = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = [w.x for w in worlds]
    extreme = min(xs) if side < 0 else max(xs)
    for vert, world in zip(obj.data.vertices, worlds):
        vert.select = (
            abs(world.z - z_mid) <= 0.07
            and abs(world.x - extreme) <= 0.05
        )


def _add_sleeves(shirt, marks, clearance):
    """Extrude short sleeves from the torso so they stay welded."""
    length = 0.09 + clearance
    z_mid = marks["shoulders"].z
    for side in (-1.0, 1.0):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        shirt.select_set(True)
        bpy.context.view_layer.objects.active = shirt
        for vert in shirt.data.vertices:
            vert.select = False
        _select_sleeve_verts(shirt, side, z_mid)
        if sum(1 for v in shirt.data.vertices if v.select) < 2:
            continue
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.extrude_region_move(
            TRANSFORM_OT_translate={
                "value": (side * length, 0.0, -0.015),
            },
        )
        bpy.ops.object.mode_set(mode="OBJECT")
    return shirt


def loft_garment(body, marks):
    """Build the cloth surface from cleared body loops."""
    cfg = _garment_cfg()
    clearance = float(cfg.get("clearance") or 0.012)
    kind = cfg.get("kind") or "shirt"
    amount = float(cfg.get("stylization") or 0.7)
    neck_w = float(cfg.get("neck") or 0.14)
    n = 16
    zs = [
        marks["hem"].z,
        marks["hips"].z,
        marks["belly"].z,
        marks["chest"].z,
        marks["shoulders"].z,
        marks["neck"].z,
    ]
    if kind == "tunic":
        zs[0] = min(zs[0], marks["hem"].z - 0.06)
    rings = []
    for z in zs:
        ring = slice_ring(body, z, n, clearance)
        rings.append(_clamp_ring(_stylize_ring(ring, amount), 1.3))
    rings[-1] = _fit_ring_width(rings[-1], neck_w)
    if kind == "vest":
        rings[-2] = _stylize_ring(
            slice_ring(body, marks["shoulders"].z, n, clearance + 0.01),
            amount,
        )
    shirt = loft_rings(rings, kind)
    if cfg.get("sleeve") == "short" and kind != "vest":
        _add_sleeves(shirt, marks, clearance)
    mins, maxs = body_bounds(shirt)
    shirt.location.x -= (mins.x + maxs.x) * 0.5
    bpy.ops.object.select_all(action="DESELECT")
    shirt.select_set(True)
    bpy.context.view_layer.objects.active = shirt
    bpy.ops.object.transform_apply(location=True)
    shade_smooth(shirt)
    return shirt
'''
