"""Curve and outline snippets compiled into build.py."""

CREATE_CURVE_SRC = r'''
def create_curve(name, size, location, rotation=(0.0, 0.0, 0.0),
                 curve=None, helper=False):
    """Bezier path with bevel. Points are local to location."""
    spec = curve or {}
    points = spec.get("points") or []
    if len(points) < 2:
        return create_cylinder(name, size, location, rotation)
    cu = bpy.data.curves.new("_mason_curve_" + name, "CURVE")
    cu.dimensions = "3D"
    fill = (spec.get("fill") or "full").upper()
    if fill == "NONE":
        cu.fill_mode = "HALF"
        cu.bevel_depth = 0.0
    else:
        cu.fill_mode = fill if fill in ("FULL", "HALF") else "FULL"
        cu.bevel_depth = float(spec.get("bevel_depth") or 0.01)
    cu.bevel_resolution = int(spec.get("bevel_resolution") or 4)
    cu.resolution_u = int(spec.get("resolution_u") or 12)
    spline = cu.splines.new("BEZIER")
    spline.use_cyclic_u = bool(spec.get("cyclic"))
    spline.bezier_points.add(len(points) - 1)
    taper = spec.get("taper")
    n = len(points)
    for i, pt in enumerate(points):
        bp = spline.bezier_points[i]
        at = pt.get("at") or (0.0, 0.0, 0.0)
        bp.co = Vector(at)
        hl = pt.get("handle_left")
        hr = pt.get("handle_right")
        if hl:
            bp.handle_left_type = "FREE"
            bp.handle_left = Vector(hl)
        else:
            bp.handle_left_type = "AUTO"
        if hr:
            bp.handle_right_type = "FREE"
            bp.handle_right = Vector(hr)
        else:
            bp.handle_right_type = "AUTO"
        radius = float(pt.get("radius") if pt.get("radius") is not None else 1.0)
        if taper is not None and n > 1:
            t = i / (n - 1)
            radius *= 1.0 + (float(taper) - 1.0) * t
        bp.radius = radius
        bp.tilt = float(pt.get("tilt") or 0.0)
    profile = spec.get("bevel_profile")
    if profile:
        bevel = _bevel_profile_object(name, profile)
        if hasattr(cu, "bevel_mode"):
            cu.bevel_mode = "OBJECT"
        cu.bevel_object = bevel
    curve_obj = bpy.data.objects.new("_mason_curve_" + name, cu)
    bpy.context.collection.objects.link(curve_obj)
    curve_obj.location = location
    curve_obj.rotation_euler = rotation
    if helper or cu.bevel_depth <= 0.0:
        return curve_obj
    bpy.ops.object.select_all(action="DESELECT")
    curve_obj.select_set(True)
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.duplicate()
    mesh_obj = bpy.context.active_object
    bpy.ops.object.convert(target="MESH")
    mesh_obj.name = name
    shade_smooth(mesh_obj)
    return mesh_obj


def _bevel_profile_object(name, pts):
    """2D poly curve used as a custom bevel cross-section."""
    cu = bpy.data.curves.new("_mason_bevel_" + name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "NONE"
    spline = cu.splines.new("POLY")
    spline.use_cyclic_u = True
    spline.points.add(max(len(pts) - 1, 0))
    for i, pair in enumerate(pts):
        spline.points[i].co = (float(pair[0]), float(pair[1]), 0.0, 1.0)
    obj = bpy.data.objects.new("_mason_bevel_" + name, cu)
    bpy.context.collection.objects.link(obj)
    return obj


def apply_follow(obj, spec):
    """Curve-deform obj along a named curve part."""
    if not spec:
        return
    name = spec.get("curve")
    if not name:
        return
    curve = bpy.data.objects.get("_mason_curve_" + name)
    if curve is None:
        curve = bpy.data.objects.get(name)
    if curve is None:
        return
    if spec.get("stretch") and hasattr(curve.data, "use_stretch"):
        curve.data.use_stretch = True
        curve.data.use_deform_bounds = True
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="Follow", type="CURVE")
    mod.object = curve
    if hasattr(mod, "deform_axis"):
        mod.deform_axis = "POS_Z"
    bpy.ops.object.modifier_apply(modifier=mod.name)


def create_outline(name, size, location, rotation=(0.0, 0.0, 0.0),
                   outline=None):
    """Extrude a closed XZ silhouette along local Y."""
    spec = outline or {}
    pts = spec.get("points") or []
    depth = float(spec.get("depth") or 0.01)
    if len(pts) < 3:
        return create_box(name, size, location, rotation)
    n = len(pts)
    half = depth * 0.5
    verts = [(float(p[0]), -half, float(p[1])) for p in pts]
    verts += [(float(p[0]), half, float(p[1])) for p in pts]
    faces = []
    for i in range(n):
        a = i
        b = (i + 1) % n
        faces.append((a, b, b + n, a + n))
    faces.append(tuple(range(n)))
    faces.append(tuple(reversed(range(n, 2 * n))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    shade_smooth(obj)
    return obj
'''
