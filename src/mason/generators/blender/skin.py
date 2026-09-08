"""Skin-modifier snippets compiled into build.py."""

CREATE_SKIN_SRC = r'''
def create_skin(name, size, location, rotation=(0.0, 0.0, 0.0),
                skin=None):
    """Skeleton graph thickened with the Skin modifier."""
    spec = skin or {}
    if (spec.get("mode") or "skeleton") == "blob":
        return create_blob(name, size, location, rotation, spec)
    nodes = spec.get("nodes") or []
    edges_spec = spec.get("edges") or []
    if len(nodes) < 2 or not edges_spec:
        return create_sphere(name, size, location, rotation)
    id_to_i = {n["id"]: i for i, n in enumerate(nodes)}
    verts = [tuple(n["at"]) for n in nodes]
    edges = []
    for pair in edges_spec:
        a, b = pair[0], pair[1]
        if a in id_to_i and b in id_to_i:
            edges.append((id_to_i[a], id_to_i[b]))
    if not edges:
        return create_sphere(name, size, location, rotation)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="Skin", type="SKIN")
    mod.use_smooth_shade = True
    if hasattr(mod, "branch_smoothing"):
        mod.branch_smoothing = 0.4
    layer = obj.data.skin_vertices[0].data
    for i, node in enumerate(nodes):
        radius = float(node.get("radius") or 0.01)
        layer[i].radius = (radius, radius)
        layer[i].use_root = i == 0
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for node in nodes:
        group = obj.vertex_groups.new(name=node["id"])
        at = Vector(node["at"])
        radius = float(node.get("radius") or 0.01)
        falloff = max(radius * 4.0, 0.001)
        for vert in obj.data.vertices:
            dist = (vert.co - at).length
            if dist <= falloff:
                weight = 1.0 - (dist / falloff)
                group.add([vert.index], weight, "REPLACE")
    levels = int(spec.get("subdivide") or 0)
    if levels > 0:
        sub = obj.modifiers.new(name="Subsurf", type="SUBSURF")
        sub.levels = levels
        sub.render_levels = levels
        bpy.ops.object.modifier_apply(modifier=sub.name)
    if spec.get("smooth", True):
        sm = obj.modifiers.new(name="Smooth", type="SMOOTH")
        sm.iterations = 8
        sm.factor = 0.5
        bpy.ops.object.modifier_apply(modifier=sm.name)
    shade_smooth(obj)
    return obj


def create_blob(name, size, location, rotation=(0.0, 0.0, 0.0),
                spec=None):
    """Node spheres plus optional edge capsules. No Skin modifier."""
    spec = spec or {}
    nodes = spec.get("nodes") or []
    if not nodes:
        return create_sphere(name, size, location, rotation)
    pieces = []
    by_id = {}
    for i, node in enumerate(nodes):
        nid = node.get("id") or ("n%d" % i)
        at = tuple(node.get("at") or (0.0, 0.0, 0.0))
        radius = float(node.get("radius") or 0.01)
        diam = max(radius * 2.0, 0.001)
        obj = create_sphere(
            "%s_%s" % (name, nid), (diam, diam, diam), at,
        )
        pieces.append(obj)
        by_id[nid] = (at, radius)
    for pair in spec.get("edges") or []:
        a, b = pair[0], pair[1]
        if a not in by_id or b not in by_id:
            continue
        cap = _blob_capsule(
            "%s_%s_%s" % (name, a, b),
            by_id[a][0], by_id[b][0],
            min(by_id[a][1], by_id[b][1]),
        )
        if cap is not None:
            pieces.append(cap)
    target = pieces[0]
    for other in pieces[1:]:
        _join_blob(target, other)
    target.name = name
    target.location = location
    target.rotation_euler = rotation
    shade_smooth(target)
    return target


def _blob_capsule(name, p0, p1, radius):
    """Cylinder from p0 to p1. Returns None if the span is tiny."""
    import math
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    dz = p1[2] - p0[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-6:
        return None
    mid = (
        (p0[0] + p1[0]) * 0.5,
        (p0[1] + p1[1]) * 0.5,
        (p0[2] + p1[2]) * 0.5,
    )
    diam = max(radius * 2.0, 0.001)
    obj = create_cylinder(name, (diam, diam, length), mid)
    vec = Vector((dx, dy, dz))
    obj.rotation_euler = vec.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(
        location=False, rotation=True, scale=True,
    )
    obj.location = mid
    return obj


def _join_blob(target, other):
    """Bake and join a blob piece into target."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.transform_apply(
        location=True, rotation=True, scale=True,
    )
    other.select_set(True)
    bpy.context.view_layer.objects.active = other
    bpy.ops.object.transform_apply(
        location=True, rotation=True, scale=True,
    )
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    other.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
'''
