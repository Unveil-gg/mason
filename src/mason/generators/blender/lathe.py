"""Lathe and bend snippets compiled into build.py."""

CREATE_LATHE_SRC = r'''
def create_lathe(name, size, location, rotation=(0.0, 0.0, 0.0),
                 profile=None, segments=24):
    """Revolve a (radius, z) profile around +Z. size is snap AABB."""
    import math
    pts = [(float(p[0]), float(p[1])) for p in (profile or [])]
    if len(pts) < 2:
        return create_cylinder(name, size, location, rotation)
    segs = max(int(segments), 8)
    zs = [p[1] for p in pts]
    z_mid = (min(zs) + max(zs)) * 0.5
    verts = []
    for radius, z in pts:
        radius = max(radius, 0.0)
        for s in range(segs):
            ang = (2.0 * math.pi * s) / segs
            verts.append((
                radius * math.cos(ang),
                radius * math.sin(ang),
                z - z_mid,
            ))
    faces = []
    n = len(pts)
    for i in range(n - 1):
        if pts[i][0] <= 1e-8 and pts[i + 1][0] <= 1e-8:
            continue
        for s in range(segs):
            a = i * segs + s
            b = i * segs + (s + 1) % segs
            c = (i + 1) * segs + (s + 1) % segs
            d = (i + 1) * segs + s
            faces.append((a, b, c, d))
    if pts[0][0] > 1e-8:
        faces.append(tuple(reversed(range(segs))))
    if pts[-1][0] > 1e-8:
        top = [(n - 1) * segs + s for s in range(segs)]
        faces.append(tuple(top))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj


def apply_bend(obj, spec):
    """Simple Deform bend. origin=base plants the min-Z end."""
    if not spec:
        return
    angle = float(spec.get("angle") or 0.0)
    if abs(angle) < 1e-6:
        return
    axis = (spec.get("axis") or "x").upper()
    if spec.get("origin") == "base" and obj.data.vertices:
        zs = [v.co.z for v in obj.data.vertices]
        zmin = min(zs)
        for vert in obj.data.vertices:
            vert.co.z -= zmin
        obj.data.update()
        obj.location.z += zmin
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="Bend", type="SIMPLE_DEFORM")
    mod.deform_method = "BEND"
    if hasattr(mod, "deform_axis"):
        mod.deform_axis = axis
    mod.angle = angle
    bpy.ops.object.modifier_apply(modifier=mod.name)


def apply_drape(obj, spec):
    """Hem flare via Simple Deform. origin=top plants max-Z."""
    if not spec:
        return
    amount = float(spec.get("amount") or 0.0)
    if abs(amount) < 1e-6:
        return
    axis = (spec.get("axis") or "x").upper()
    origin = spec.get("origin") or "top"
    if origin != "center" and obj.data.vertices:
        zs = [v.co.z for v in obj.data.vertices]
        pivot = max(zs) if origin == "top" else min(zs)
        for vert in obj.data.vertices:
            vert.co.z -= pivot
        obj.data.update()
        obj.location.z += pivot
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="Drape", type="SIMPLE_DEFORM")
    mod.deform_method = "BEND"
    if hasattr(mod, "deform_axis"):
        mod.deform_axis = axis
    mod.angle = amount
    bpy.ops.object.modifier_apply(modifier=mod.name)
'''
