"""Pack image-textured prop UVs onto one shared tile."""

PROP_ATLAS_PACK_SRC = r'''
def _poly_material_name(obj, poly):
    """Material name for a polygon, or empty."""
    slots = obj.material_slots
    index = poly.material_index
    if index < 0 or index >= len(slots):
        return ""
    mat = slots[index].material
    if mat is None:
        return ""
    return mat.name


def _write_uv(layer, loop_index, u, v):
    """Set one loop UV."""
    layer[loop_index].uv.x = u
    layer[loop_index].uv.y = v


def _map_face_tile(src, dest, loops, u0, v0, u1, v1):
    """Stretch a face across the tile and sample the whole image."""
    us = [src[i].uv.x for i in loops]
    vs = [src[i].uv.y for i in loops]
    du = max(us) - min(us)
    dv = max(vs) - min(vs)
    if du < 1e-8 or dv < 1e-8:
        return
    min_u = min(us)
    min_v = min(vs)
    span_u = u1 - u0
    span_v = v1 - v0
    for i in loops:
        su = (src[i].uv.x - min_u) / du
        sv = (src[i].uv.y - min_v) / dv
        _write_uv(src, i, su, sv)
        _write_uv(dest, i, u0 + su * span_u, v0 + sv * span_v)


def _map_face_rect(dest, loops, u0, v0, u1, v1):
    """Cover a swatch with this face. Leaves source UVs alone."""
    corners = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    for index, loop_i in enumerate(loops):
        corner = corners[index % 4]
        _write_uv(dest, loop_i, corner[0], corner[1])


def _swatch_rects(names, size):
    """Right-hand column of swatches. Returns name to (u0,v0,u1,v1)."""
    gap = 6.0 / float(size)
    swatch_w = 8.0 / float(size)
    rects = {}
    count = max(len(names), 1)
    band_h = (1.0 - gap * 2.0) / count
    for index, name in enumerate(names):
        y0 = gap + index * band_h
        y1 = max(y0 + gap, y0 + band_h - gap)
        x0 = 1.0 - swatch_w - gap
        rects[name] = (x0, y0, 1.0 - gap, y1)
    return rects, gap


def _pack_textured_uvs(obj, textures, size):
    """One tile for image faces. Flat colors share a swatch column.

    Returns True when at least one image face was packed. Faces
    smaller than a quarter of the largest (bevels) use an edge
    swatch so they cannot overwrite the shared tile.
    """
    mesh = obj.data
    src_layer = mesh.uv_layers.get("mason_src")
    if src_layer is None or not mesh.polygons:
        return False
    dest = mesh.uv_layers.active.data
    src = src_layer.data
    textured = []
    solid_names = []
    for poly in mesh.polygons:
        name = _poly_material_name(obj, poly)
        if name in textures:
            textured.append(poly)
        elif name not in solid_names:
            solid_names.append(name)
    if not textured:
        return False
    largest = max(poly.area for poly in textured)
    cutoff = largest * 0.25
    small = any(poly.area < cutoff for poly in textured)
    names = list(solid_names)
    if small:
        names.append("__edge__")
    rects, gap = _swatch_rects(names, size) if names else ({}, 6.0 / float(size))
    right = 1.0 - gap
    if names:
        right = rects[names[0]][0] - gap
    tile = (gap, gap, max(right, gap + 0.05), 1.0 - gap)
    for poly in textured:
        loops = list(poly.loop_indices)
        if poly.area < cutoff:
            _map_face_rect(dest, loops, *rects["__edge__"])
        else:
            _map_face_tile(src, dest, loops, *tile)
    for poly in mesh.polygons:
        name = _poly_material_name(obj, poly)
        if name in textures or name not in rects:
            continue
        _map_face_rect(dest, list(poly.loop_indices), *rects[name])
    return True
'''
