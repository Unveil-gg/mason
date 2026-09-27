"""Sample part color and height into the prop atlas."""

PROP_ATLAS_SAMPLE_SRC = r'''
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


'''
