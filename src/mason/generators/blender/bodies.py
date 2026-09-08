"""Volume-union and remesh snippets compiled into build.py."""

CREATE_BODIES_SRC = r'''
def apply_bodies(created, bodies):
    """Union member parts, optional voxel remesh, then smooth."""
    for body in bodies or []:
        names = _body_member_names(body, created)
        objs = []
        for name in names:
            obj = created.get(name)
            if obj is not None and obj.type == "MESH":
                objs.append((name, obj))
        if not objs:
            continue
        target_name, target = objs[0]
        method = body.get("method") or "remesh"
        bpy.ops.object.select_all(action="DESELECT")
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        for other_name, other in objs[1:]:
            _reparent_children(other, target)
            if method == "union":
                _boolean_union(target, other)
                bpy.data.objects.remove(other, do_unlink=True)
            else:
                _join_other(target, other)
            created.pop(other_name, None)
        inflate = float(body.get("inflate") or 0.0)
        if inflate > 0:
            sol = target.modifiers.new(name="Inflate", type="SOLIDIFY")
            sol.thickness = inflate
            sol.offset = 1.0
            bpy.ops.object.modifier_apply(modifier=sol.name)
        remesh = body.get("remesh") or {}
        if method == "remesh" or remesh:
            voxel = float(remesh.get("voxel_size") or 0.01)
            adapt = float(remesh.get("adaptivity") or 0.0)
            rm = target.modifiers.new(name="Remesh", type="REMESH")
            rm.mode = "VOXEL"
            rm.voxel_size = max(voxel, 1e-5)
            rm.adaptivity = adapt
            rm.use_smooth_shade = True
            bpy.ops.object.modifier_apply(modifier=rm.name)
        smooth_n = int(body.get("smooth") or 0)
        if smooth_n > 0:
            sm = target.modifiers.new(name="Smooth", type="SMOOTH")
            sm.iterations = smooth_n
            sm.factor = 0.5
            bpy.ops.object.modifier_apply(modifier=sm.name)
        subdiv = int(body.get("subdivide") or 0)
        if subdiv > 0:
            sub = target.modifiers.new(name="Subsurf", type="SUBSURF")
            sub.levels = subdiv
            sub.render_levels = subdiv
            bpy.ops.object.modifier_apply(modifier=sub.name)
        target.name = body["name"]
        created.pop(target_name, None)
        created[body["name"]] = target
        shade_smooth(target)


def _boolean_union(target, other):
    """CSG union other into target, leaving other in the scene."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(name="mason_union", type="BOOLEAN")
    mod.operation = "UNION"
    mod.object = other
    if hasattr(mod, "solver"):
        mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _join_other(target, other):
    """Bake transforms and join other into target."""
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


def _body_member_names(body, created):
    """Exact members plus array/mirror copies (name_ / name_m)."""
    out = []
    for name in body.get("members") or []:
        if name in created and name not in out:
            out.append(name)
        prefix = name + "_"
        for key in created:
            if key.startswith(prefix) and key not in out:
                out.append(key)
    return out


def _reparent_children(old, new):
    """Move children of a consumed member onto the joined body."""
    for obj in list(bpy.data.objects):
        if obj.parent != old:
            continue
        world = obj.matrix_world.copy()
        obj.parent = new
        obj.matrix_parent_inverse = new.matrix_world.inverted()
        obj.matrix_world = world


def finish_geometry(created):
    """Follow, parent, cutouts, bodies, then decimate."""
    for part in CONFIG["parts"]:
        obj = created.get(part["name"])
        if obj is not None and part.get("follow") and obj.type == "MESH":
            apply_follow(obj, part["follow"])
    for part in CONFIG["parts"]:
        parent_name = part.get("parent")
        child = created.get(part["name"])
        parent = created.get(parent_name) if parent_name else None
        if child is not None and parent is not None:
            world = child.matrix_world.copy()
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()
            child.matrix_world = world
    apply_cutouts(created)
    apply_bodies(created, CONFIG.get("bodies") or [])
    apply_decimate(CONFIG.get("decimate"))
'''
