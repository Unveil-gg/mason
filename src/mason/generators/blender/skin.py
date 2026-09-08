"""Skin-modifier snippets compiled into build.py."""

CREATE_SKIN_SRC = r'''
def create_skin(name, size, location, rotation=(0.0, 0.0, 0.0),
                skin=None):
    """Skeleton graph thickened with the Skin modifier."""
    spec = skin or {}
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
'''
