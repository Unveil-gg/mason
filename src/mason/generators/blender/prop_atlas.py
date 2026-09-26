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


def _tex_image(mat):
    """Texel array for a linked base-color image, or None."""
    if mat is None or not mat.use_nodes:
        return None
    bsdf = next(
        (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
        None,
    )
    color_in = _principled_input(bsdf, "Base Color", "Color")
    if color_in is None or not color_in.is_linked:
        return None
    node = color_in.links[0].from_node
    if node.type != "TEX_IMAGE" or node.image is None:
        return None
    image = node.image
    width, height = int(image.size[0]), int(image.size[1])
    if width < 1 or height < 1:
        return None
    flat = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(flat)
    return flat.reshape((height, width, 4))


def _sample_wrap(image, u, v):
    """Repeat-sample an image. u and v are flat arrays."""
    height, width, _channels = image.shape
    cols = np.mod(u, 1.0) * (width - 1)
    rows = np.mod(v, 1.0) * (height - 1)
    cols = np.clip(cols.astype(np.int32), 0, width - 1)
    rows = np.clip(rows.astype(np.int32), 0, height - 1)
    return image[rows, cols]


def _stash_src_uv(obj):
    """Copy authoring UVs before the atlas unwrap replaces them."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    author = mesh.uv_layers.active
    src = mesh.uv_layers.get("mason_src")
    if src is None:
        src = mesh.uv_layers.new(name="mason_src")
    for index, loop in enumerate(author.data):
        src.data[index].uv = loop.uv
    mesh.uv_layers.active = author


def _bump_image(mat):
    """Height texels from a Bump node, or None."""
    if mat is None or not mat.use_nodes:
        return None
    bump = next(
        (
            n for n in mat.node_tree.nodes
            if n.type in ("BUMP", "ShaderNodeBump")
            or getattr(n, "bl_idname", "") == "ShaderNodeBump"
        ),
        None,
    )
    if bump is None:
        return None
    sock = bump.inputs.get("Height")
    if sock is None or not sock.is_linked:
        return None
    node = sock.links[0].from_node
    if node.type != "TEX_IMAGE" or node.image is None:
        return None
    image = node.image
    width, height = int(image.size[0]), int(image.size[1])
    if width < 1 or height < 1:
        return None
    if len(image.pixels) < 4:
        return None
    flat = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(flat)
    arr = flat.reshape((height, width, 4))
    if float(np.max(arr[:, :, 0])) >= 0.02:
        return arr
    path = bpy.path.abspath(image.filepath or "")
    if not path or not os.path.isfile(path):
        return None
    fresh = bpy.data.images.load(path, check_existing=False)
    fw, fh = int(fresh.size[0]), int(fresh.size[1])
    if fw < 1 or fh < 1 or len(fresh.pixels) < 4:
        bpy.data.images.remove(fresh)
        return None
    buf = np.empty(fw * fh * 4, dtype=np.float32)
    fresh.pixels.foreach_get(buf)
    bpy.data.images.remove(fresh)
    return buf.reshape((fh, fw, 4))


def _collect_bumps(meshes):
    """Map material name to its height image, if any."""
    found = {}
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or mat.name in found:
                continue
            image = _bump_image(mat)
            if image is not None:
                found[mat.name] = image
    return found


def _collect_textures(meshes):
    """Map material name to its base-color image, if any."""
    found = {}
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or mat.name in found:
                continue
            image = _tex_image(mat)
            if image is not None:
                found[mat.name] = image
    return found


def _raster_mesh(obj, albedo, orm, ao, textures, bumps=None, height=None):
    """Paint this mesh's UV triangles into the shared atlas."""
    mesh = obj.data
    if not mesh.uv_layers:
        return
    size = albedo.shape[0]
    uvs = mesh.uv_layers.active.data
    src_layer = mesh.uv_layers.get("mason_src")
    src_uvs = src_layer.data if src_layer is not None else None
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        slot = tri.material_index
        mat = None
        if slot < len(obj.material_slots):
            mat = obj.material_slots[slot].material
        color = _base_color(mat)
        rough, metal = _surface_factors(mat)
        tex = textures.get(mat.name) if mat is not None else None
        bump = None
        if bumps is not None and mat is not None:
            bump = bumps.get(mat.name)
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
        rgb = None
        uu = vv = None
        if src_uvs is not None and (tex is not None or bump is not None):
            s0 = src_uvs[tri.loops[0]].uv
            s1 = src_uvs[tri.loops[1]].uv
            s2 = src_uvs[tri.loops[2]].uv
            uu = w0 * s0.x + w1 * s1.x + w2 * s2.x
            vv = w0 * s0.y + w1 * s1.y + w2 * s2.y
        if tex is not None and uu is not None:
            rgb = _sample_wrap(tex, uu[mask], vv[mask])[:, :3]
        if bump is not None and height is not None and uu is not None:
            sampled = _sample_wrap(bump, uu[mask], vv[mask])
            height[rows, cols, 0] = sampled[:, 0]
            height[rows, cols, 3] = 1.0
        if rgb is None:
            # Contact AO turns thin metal bands black. Keep a light silver.
            shade = tone
            base = color
            if metal >= 0.55:
                shade = np.ones_like(tone)
                base = tuple(min(1.0, float(c) * 2.6) for c in color[:3])
            for channel in range(3):
                albedo[rows, cols, channel] = base[channel] * shade
        else:
            for channel in range(3):
                albedo[rows, cols, channel] = rgb[:, channel]
        albedo[rows, cols, 3] = 1.0
        orm[rows, cols, 0] = tone
        band = min(float(rough), 0.06) if metal >= 0.55 else rough
        orm[rows, cols, 1] = band
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


def _normals_from_height(height, strength):
    """Tangent normals from an atlas height buffer. Returns RGBA."""
    filled = _dilate(height, 2)
    field = filled[:, :, 0]
    known = filled[:, :, 3] > 0.5
    field = np.where(known, field, 0.5)
    dx = np.zeros_like(field)
    dy = np.zeros_like(field)
    dx[:, 1:-1] = (field[:, 2:] - field[:, :-2]) * 0.5
    dy[1:-1, :] = (field[2:, :] - field[:-2, :]) * 0.5
    nx = np.where(known, -dx * strength, 0.0)
    ny = np.where(known, -dy * strength, 0.0)
    nz = np.ones_like(field)
    stacked = np.stack((nx, ny, nz), axis=-1)
    norm = np.linalg.norm(stacked, axis=-1, keepdims=True)
    stacked = stacked / np.clip(norm, 1e-6, None)
    out = np.zeros_like(filled)
    out[:, :, :3] = stacked * 0.5 + 0.5
    out[:, :, 3] = 1.0
    return out


def _link_normal(nodes, links, image, bsdf):
    """Packed normal map on the shared prop material."""
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Smart"
    try:
        tex.image.colorspace_settings.name = "Non-Color"
    except TypeError:
        pass
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(tex.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


def _assign_atlas(meshes, albedo_img, orm_img, normal_img=None):
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
    if normal_img is not None:
        _link_normal(nodes, links, normal_img, bsdf)
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


def _soft_height(albedo, blocks=16):
    """Chunky height from atlas albedo when the bump read is flat."""
    lum = (
        0.2126 * albedo[:, :, 0]
        + 0.7152 * albedo[:, :, 1]
        + 0.0722 * albedo[:, :, 2]
    )
    known = (albedo[:, :, 3] > 0.5).astype(np.float32)
    height, width = lum.shape
    bh, bw = height // blocks, width // blocks
    if bh < 2 or bw < 2:
        return None
    crop_h, crop_w = bh * blocks, bw * blocks
    pix = lum[:crop_h, :crop_w].reshape(bh, blocks, bw, blocks)
    wt = known[:crop_h, :crop_w].reshape(bh, blocks, bw, blocks)
    pix = pix.mean(axis=(1, 3))
    wt = wt.mean(axis=(1, 3))
    vals = pix[wt > 0.2]
    if vals.size == 0:
        return None
    lo, hi = float(vals.min()), float(vals.max())
    if hi - lo < 1e-4:
        return None
    pix = np.clip((pix - lo) / (hi - lo), 0.0, 1.0)
    big = np.repeat(np.repeat(pix, blocks, axis=0), blocks, axis=1)
    out = np.zeros_like(albedo)
    out[:big.shape[0], :big.shape[1], 0] = big
    out[:crop_h, :crop_w, 3] = known[:crop_h, :crop_w]
    return out


def _bake_prop_atlas():
    """One albedo (color * AO) and one ORM for every export mesh."""
    meshes = _mesh_objects()
    if not meshes:
        return
    size = int(CONFIG.get("export_atlas_size") or 1024)
    size = max(64, min(size, 2048))
    textures = _collect_textures(meshes)
    bumps = _collect_bumps(meshes)
    bands = len(meshes)
    for index, obj in enumerate(meshes):
        _stash_src_uv(obj)
        _smart_uv(obj)
        pad = 2.0 / size
        v0 = index / bands + pad
        v1 = (index + 1) / bands - pad
        _remap_uv(obj, pad, v0, 1.0 - pad, v1)
    albedo = np.zeros((size, size, 4), dtype=np.float32)
    orm = np.zeros((size, size, 4), dtype=np.float32)
    height = None
    if bumps:
        height = np.zeros((size, size, 4), dtype=np.float32)
    for obj in meshes:
        _raster_mesh(
            obj, albedo, orm, _vertex_ao(obj), textures, bumps, height,
        )
    albedo = _dilate(albedo, 2)
    orm = _dilate(orm, 2)
    albedo_img = _image_from("albedo", albedo, "sRGB")
    orm_img = _image_from("orm", orm, "Non-Color")
    normal_img = None
    span = 0.0
    if height is not None:
        mask = height[:, :, 3] > 0.5
        if np.any(mask):
            span = float(np.ptp(height[:, :, 0][mask]))
    if span < 0.08:
        height = _soft_height(albedo)
    if height is not None and np.any(height[:, :, 3] > 0.5):
        normal = _normals_from_height(height, 36.0)
        normal_img = _image_from("normal", normal, "Non-Color")
    _assign_atlas(meshes, albedo_img, orm_img, normal_img)
    _save_atlas(albedo_img, "albedo.png")
    _save_atlas(orm_img, "orm.png")
    if normal_img is not None:
        _save_atlas(normal_img, "normal.png")
'''
