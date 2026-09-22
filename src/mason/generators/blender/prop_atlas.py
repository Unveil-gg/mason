"""Bake a shared albedo and ORM atlas for prop export."""

PROP_ATLAS_SRC = r'''
def _base_color(mat):
    """Solid Principled base color, or mid grey."""
    if mat is None or not mat.use_nodes:
        return (0.6, 0.6, 0.6, 1.0)
    bsdf = next(
        (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
        None,
    )
    if bsdf is None:
        return (0.6, 0.6, 0.6, 1.0)
    color = _read_base_color(bsdf)
    if color is None:
        return (0.6, 0.6, 0.6, 1.0)
    return color


def _socket_value(bsdf, name, default):
    """Unlinked Principled socket, or default."""
    sock = bsdf.inputs.get(name) if bsdf else None
    if sock is None or sock.is_linked:
        return default
    return float(sock.default_value)


def _surface_factors(mat):
    """(roughness, metallic) from a flattened Principled node."""
    if mat is None or not mat.use_nodes:
        return 0.5, 0.0
    bsdf = next(
        (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
        None,
    )
    return (
        _socket_value(bsdf, "Roughness", 0.5),
        _socket_value(bsdf, "Metallic", 0.0),
    )


def _vertex_ao(obj, samples=12):
    """Self-occlusion per vertex, 0.45..1. Falls back to 1."""
    mesh = obj.data
    count = len(mesh.vertices)
    if count == 0:
        return []
    try:
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        bvh = mathutils.bvhtree.BVHTree.FromObject(obj, deps)
    except Exception:
        return [1.0] * count
    golden = math.pi * (3.0 - math.sqrt(5.0))
    ao = []
    for vert in mesh.vertices:
        normal = (obj.matrix_world.to_3x3() @ vert.normal).normalized()
        if normal.length < 1e-6:
            normal = Vector((0.0, 0.0, 1.0))
        origin = obj.matrix_world @ vert.co + normal * 0.005
        hits = 0
        cast = 0
        for i in range(samples * 2):
            span = max(samples * 2 - 1, 1)
            y = 1.0 - (i / span) * 2.0
            radius = math.sqrt(max(0.0, 1.0 - y * y))
            theta = golden * i
            direction = Vector((
                math.cos(theta) * radius,
                y,
                math.sin(theta) * radius,
            ))
            if direction.dot(normal) <= 0.2:
                continue
            cast += 1
            hit, _, _, _ = bvh.ray_cast(origin, direction, 0.4)
            if hit is not None:
                hits += 1
            if cast >= samples:
                break
        shade = 1.0 if cast == 0 else 1.0 - hits / float(cast)
        ao.append(0.45 + 0.55 * shade)
    return ao


def _smart_uv(obj):
    """Unique islands in 0..1. Existing UVs stay if unwrap fails."""
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.03)
    except Exception:
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="OBJECT")


def _remap_uv(obj, u0, v0, u1, v1):
    """Scale the current 0..1 layout into a pixel-safe rect."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    layer = mesh.uv_layers.active.data
    for loop in layer:
        loop.uv.x = u0 + loop.uv.x * (u1 - u0)
        loop.uv.y = v0 + loop.uv.y * (v1 - v0)


def _raster_mesh(obj, albedo, orm, ao):
    """Paint this mesh's UV triangles into the shared atlas."""
    mesh = obj.data
    if not mesh.uv_layers:
        return
    size = albedo.shape[0]
    uvs = mesh.uv_layers.active.data
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        slot = tri.material_index
        mat = None
        if slot < len(obj.material_slots):
            mat = obj.material_slots[slot].material
        color = _base_color(mat)
        rough, metal = _surface_factors(mat)
        pts = []
        shades = []
        for loop_i, vert_i in zip(tri.loops, tri.vertices):
            uv = uvs[loop_i].uv
            pts.append((uv.x * (size - 1), uv.y * (size - 1)))
            if vert_i < len(ao):
                shades.append(ao[vert_i])
            else:
                shades.append(1.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        minx = max(int(min(xs)), 0)
        maxx = min(int(max(xs)) + 1, size - 1)
        miny = max(int(min(ys)), 0)
        maxy = min(int(max(ys)) + 1, size - 1)
        if maxx < minx or maxy < miny:
            continue
        gx, gy = np.meshgrid(
            np.arange(minx, maxx + 1) + 0.5,
            np.arange(miny, maxy + 1) + 0.5,
        )
        ax, ay = pts[0]
        bx, by = pts[1]
        cx, cy = pts[2]
        denom = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denom) < 1e-8:
            continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / denom
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / denom
        w2 = 1.0 - w0 - w1
        mask = (w0 >= -0.001) & (w1 >= -0.001) & (w2 >= -0.001)
        if not np.any(mask):
            continue
        shade = w0 * shades[0] + w1 * shades[1] + w2 * shades[2]
        yy, xx = np.nonzero(mask)
        rows = miny + yy
        cols = minx + xx
        tone = shade[yy, xx]
        for channel in range(3):
            albedo[rows, cols, channel] = color[channel] * tone
        albedo[rows, cols, 3] = 1.0
        orm[rows, cols, 0] = tone
        orm[rows, cols, 1] = rough
        orm[rows, cols, 2] = metal
        orm[rows, cols, 3] = 1.0


def _dilate(img, radius):
    """Bleed filled texels so mipmaps do not fringe. Returns image."""
    for _ in range(radius):
        filled = img[:, :, 3] > 0.5
        padded = np.pad(img, ((1, 1), (1, 1), (0, 0)), mode="edge")
        pfill = np.pad(filled, 1, mode="edge")
        acc = img.copy()
        known = filled.copy()
        for oy in range(3):
            for ox in range(3):
                shifted = padded[oy:oy + img.shape[0], ox:ox + img.shape[1]]
                src = pfill[oy:oy + img.shape[0], ox:ox + img.shape[1]]
                take = (~known) & src
                acc[take] = shifted[take]
                known |= take
        img = acc
    return img


def _image_from(name, img, colorspace):
    """Packed float image Mason's glTF export will embed."""
    size = img.shape[0]
    image = bpy.data.images.new(name, size, size, alpha=True)
    try:
        image.colorspace_settings.name = colorspace
    except TypeError:
        pass
    flat = np.ascontiguousarray(img, dtype=np.float32).ravel()
    image.pixels.foreach_set(flat)
    image.pack()
    image.update()
    return image


def _link_separate(nodes, links, image, bsdf):
    """G -> roughness, B -> metallic. glTF reads that as ORM."""
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Smart"
    try:
        sep = nodes.new("ShaderNodeSeparateColor")
        green, blue = "Green", "Blue"
    except Exception:
        sep = nodes.new("ShaderNodeSeparateRGB")
        green, blue = "G", "B"
    links.new(tex.outputs["Color"], sep.inputs[0])
    links.new(sep.outputs[green], bsdf.inputs["Roughness"])
    links.new(sep.outputs[blue], bsdf.inputs["Metallic"])


def _assign_atlas(meshes, albedo_img, orm_img):
    """Replace every slot with one textured material."""
    mat = bpy.data.materials.new("mason_prop")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    color_tex = nodes.new("ShaderNodeTexImage")
    color_tex.image = albedo_img
    color_tex.interpolation = "Smart"
    color_in = _principled_input(bsdf, "Base Color", "Color")
    links.new(color_tex.outputs["Color"], color_in)
    _link_separate(nodes, links, orm_img, bsdf)
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    keep = {mat}
    for old in list(bpy.data.materials):
        if old not in keep and not old.name.startswith("_mason_"):
            bpy.data.materials.remove(old)


def _save_atlas(image, filename):
    """Sidecar PNG next to the job GLB."""
    job = CONFIG.get("job_dir") or ""
    if not job:
        return
    out = os.path.join(job, "output")
    os.makedirs(out, exist_ok=True)
    image.filepath_raw = os.path.join(out, filename)
    image.file_format = "PNG"
    image.save()
    image.pack()


def _bake_prop_atlas():
    """One albedo (color * AO) and one ORM for every export mesh."""
    meshes = _mesh_objects()
    if not meshes:
        return
    size = int(CONFIG.get("export_atlas_size") or 1024)
    size = max(64, min(size, 2048))
    bands = len(meshes)
    for index, obj in enumerate(meshes):
        _smart_uv(obj)
        pad = 2.0 / size
        v0 = index / bands + pad
        v1 = (index + 1) / bands - pad
        _remap_uv(obj, pad, v0, 1.0 - pad, v1)
    albedo = np.zeros((size, size, 4), dtype=np.float32)
    orm = np.zeros((size, size, 4), dtype=np.float32)
    for obj in meshes:
        _raster_mesh(obj, albedo, orm, _vertex_ao(obj))
    albedo = _dilate(albedo, 2)
    orm = _dilate(orm, 2)
    albedo_img = _image_from("mason_albedo", albedo, "sRGB")
    orm_img = _image_from("mason_orm", orm, "Non-Color")
    _assign_atlas(meshes, albedo_img, orm_img)
    _save_atlas(albedo_img, "atlas_albedo.png")
    _save_atlas(orm_img, "atlas_orm.png")
'''
