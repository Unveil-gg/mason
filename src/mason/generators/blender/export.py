"""Blender source snippets for export and metadata."""

EXPORT_SRC = r'''
def _principled_input(bsdf, *names):
    """First matching Principled input, or None."""
    for name in names:
        if name in bsdf.inputs:
            return bsdf.inputs[name]
    return None


def _read_base_color(bsdf):
    """Best solid base color from a Principled tree."""
    color_in = _principled_input(bsdf, "Base Color", "Color")
    if color_in is None:
        return None
    if not color_in.is_linked:
        return tuple(color_in.default_value)
    from_node = color_in.links[0].from_node
    if from_node.type == "TEX_IMAGE":
        return None
    if from_node.type in ("MIX_RGB", "MIX"):
        c1 = _principled_input(from_node, "Color1", "A")
        if c1 is not None and not c1.is_linked:
            return tuple(c1.default_value)
    return None


def flatten_materials_for_gltf():
    """Collapse procedural color trees so glTF gets baseColorFactor.

    Mason's family variation uses noise->mix on Base Color. The glTF
    exporter skips that and ships grey materials unless we simplify.
    Image-textured materials are left unchanged.
    """
    for mat in list(bpy.data.materials):
        if mat.name.startswith("_mason_") or not mat.use_nodes:
            continue
        bsdf = next(
            (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
            None,
        )
        if bsdf is None:
            continue
        base = _read_base_color(bsdf)
        if base is None:
            continue
        rough_in = bsdf.inputs.get("Roughness")
        metal_in = bsdf.inputs.get("Metallic")
        rough = (
            float(rough_in.default_value)
            if rough_in is not None and not rough_in.is_linked
            else 0.5
        )
        metal = (
            float(metal_in.default_value)
            if metal_in is not None and not metal_in.is_linked
            else 0.0
        )
        mat.node_tree.nodes.clear()
        out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        new_bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(
            new_bsdf.outputs["BSDF"], out.inputs["Surface"],
        )
        color_in = _principled_input(new_bsdf, "Base Color", "Color")
        color_in.default_value = base
        new_bsdf.inputs["Roughness"].default_value = rough
        new_bsdf.inputs["Metallic"].default_value = metal


def export_glb(path):
    """Export meshes and attach empties. Skip _mason_ helpers.

    profile=prop merges statics and bakes one atlas first. The
    .blend was already saved, so the kit graph stays editable.
    """
    if CONFIG.get("export_profile") == "prop":
        pack_prop_for_export()
    else:
        flatten_materials_for_gltf()
        if CONFIG.get("export_volumes"):
            emit_export_volumes()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.name.startswith("_mason_"):
            continue
        if obj.type == "ARMATURE" and CONFIG.get("garment"):
            obj.hide_set(False)
            obj.select_set(True)
            continue
        if obj.type not in ("MESH", "EMPTY"):
            continue
        obj.hide_set(False)
        obj.select_set(True)
    kwargs = {
        "filepath": path,
        "export_format": "GLB",
        "use_selection": True,
        "export_extras": True,
    }
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        kwargs.pop("export_extras", None)
        bpy.ops.export_scene.gltf(**kwargs)


def create_attachments():
    """EMPTY sockets from CONFIG.attachments. Names attach_<id>."""
    for sock in CONFIG.get("attachments") or []:
        name = "attach_" + str(sock.get("name") or "socket")
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.04
        loc = sock.get("location") or (0.0, 0.0, 0.0)
        empty.location = loc
        empty.rotation_euler = sock.get("rotation") or (0.0, 0.0, 0.0)
        bpy.context.collection.objects.link(empty)
        parent = sock.get("parent")
        if parent:
            target = bpy.data.objects.get(parent)
            if target is not None:
                empty.parent = target
                empty.matrix_parent_inverse = (
                    target.matrix_world.inverted()
                )


def save_blend(path):
    """Save the current file as a .blend, replacing any previous file.

    Blender saves via a `<path>@` temp file then renames it; a stale
    leftover (from an interrupted save, or a locking AV/indexer) makes
    the rename fail with "Cannot change old file". Clear both before
    saving.
    """
    def _clear():
        for candidate in (path, path + "@"):
            if os.path.isfile(candidate):
                os.remove(candidate)

    _clear()
    try:
        bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
    except RuntimeError:
        _clear()
        bpy.ops.wm.save_as_mainfile(
            filepath=path, check_existing=False,
        )


def scene_bounds():
    """World-space AABB of all mesh objects. Returns (mins, maxs)."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.startswith("_mason_"):
            continue
        count += 1
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, world.x)
            mins.y = min(mins.y, world.y)
            mins.z = min(mins.z, world.z)
            maxs.x = max(maxs.x, world.x)
            maxs.y = max(maxs.y, world.y)
            maxs.z = max(maxs.z, world.z)
    if count == 0:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return mins, maxs


def export_uv_layout(path):
    """Export the first mesh UV layout for the Krita paint desk."""
    if bpy.app.background:
        return
    mesh = next(
        (
            o for o in bpy.data.objects
            if o.type == "MESH" and not o.name.startswith("_mason_")
        ),
        None,
    )
    if mesh is None:
        return
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    try:
        bpy.ops.uv.export_layout(
            filepath=path, export_all=False, modified=False,
            mode="PNG", size=(1024, 1024), opacity=0.25,
        )
    except Exception:
        pass


def write_metadata(path):
    """Write mesh stats JSON next to outputs."""
    meshes = [
        o for o in bpy.data.objects
        if o.type == "MESH" and not o.name.startswith("_mason_")
    ]
    triangles = 0
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
    mins, maxs = scene_bounds()
    size = maxs - mins
    object_bounds = {}
    for obj in meshes:
        omins = Vector((1e9, 1e9, 1e9))
        omaxs = Vector((-1e9, -1e9, -1e9))
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            omins.x = min(omins.x, world.x)
            omins.y = min(omins.y, world.y)
            omins.z = min(omins.z, world.z)
            omaxs.x = max(omaxs.x, world.x)
            omaxs.y = max(omaxs.y, world.y)
            omaxs.z = max(omaxs.z, world.z)
        object_bounds[obj.name] = {
            "min": [float(omins.x), float(omins.y), float(omins.z)],
            "max": [float(omaxs.x), float(omaxs.y), float(omaxs.z)],
        }
    saved = globals().get("PART_BOUNDS")
    if saved:
        object_bounds = saved
    payload = {
        "objects": [o.name for o in meshes],
        "mesh_count": len(meshes),
        "material_count": len(bpy.data.materials),
        "triangles": triangles,
        "bounds": {
            "x": float(size.x),
            "y": float(size.y),
            "z": float(size.z),
            "min": [float(mins.x), float(mins.y), float(mins.z)],
            "max": [float(maxs.x), float(maxs.y), float(maxs.z)],
        },
        "object_bounds": object_bounds,
        "scales": {
            o.name: [float(s) for s in o.scale] for o in meshes
        },
        "preview_engine": CONFIG.get("preview_engine"),
        "attachments": [
            {
                "name": o.name.replace("attach_", "", 1),
                "location": [float(v) for v in o.matrix_world.translation],
                "rotation": [float(v) for v in o.rotation_euler],
            }
            for o in bpy.data.objects
            if o.type == "EMPTY" and o.name.startswith("attach_")
        ],
        "volumes": [
            {
                "name": o.name,
                "kind": o.get("mason_kind") or "box",
                "min": [float(v) for v in o["mason_min"]],
                "max": [float(v) for v in o["mason_max"]],
            }
            for o in bpy.data.objects
            if o.type == "EMPTY" and "mason_min" in o.keys()
        ],
    }
    fit = globals().get("FIT_METRICS")
    if fit:
        payload["fit"] = fit
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
'''
