"""Fit measurements the agent should read before eyeballing PNGs."""

CREATE_GARMENT_METRICS_SRC = r'''
def _band_half_x(obj, mid, zmin, zmax, marks=None, height=None):
    """Max |x-mid| of torso verts in a world-Z band."""
    xs = []
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if world.z < zmin or world.z > zmax:
            continue
        if marks is not None and height is not None:
            if _is_arm_flesh(world, marks, height):
                continue
            if _is_sleeve_vert(world, marks, height):
                continue
        xs.append(abs(world.x - mid))
    return max(xs) if xs else 0.0


def _near_arm(world, marks, side, height):
    """(t, radius, drop) along shoulder-wrist, or None."""
    sh, wr = _sleeve_axis(marks, side)
    if sh is None or wr is None:
        return None
    span = wr - sh
    denom = max(span.length_squared, 1e-8)
    t = (world - sh).dot(span) / denom
    axis = sh + span * max(0.0, min(1.0, t))
    rad = (world - axis).length
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    if abs(world.x - mid) < height * 0.12:
        return None
    if rad > height * 0.18 or t < -0.08 or t > 1.08:
        return None
    return t, rad, max(0.0, axis.z - world.z)


def _arm_stats(obj, marks, side, height):
    """along / median radius / hang-below-axis for one arm."""
    alongs, rads, drops = [], [], []
    for vert in obj.data.vertices:
        hit = _near_arm(obj.matrix_world @ vert.co, marks, side, height)
        if hit is None or hit[0] < 0.05:
            continue
        alongs.append(hit[0])
        rads.append(hit[1])
        drops.append(hit[2])
    mid = sorted(rads)[len(rads) // 2] if rads else 0.0
    return {
        "along": float(max(alongs) if alongs else 0.0),
        "radius": float(mid),
        "radius_max": float(max(rads) if rads else 0.0),
        "drop": float(max(drops) if drops else 0.0),
    }


def _flap_stats(obj, marks, side, height):
    """Off-axis cape verts the tube sample ignores."""
    sh, wr = _sleeve_axis(marks, side)
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    sign = 1.0 if side == "l" else -1.0
    torso = float(marks.get("torso_half_x") or height * 0.18)
    far = 0
    off_max = 0.0
    extent = 0.0
    if sh is None or wr is None:
        return {"off_axis": 0, "off_max": 0.0, "extent": 0.0}
    span = wr - sh
    denom = max(span.length_squared, 1e-8)
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        dx = (world.x - mid) * sign
        if dx < torso * 0.45:
            continue
        extent = max(extent, dx)
        t = (world - sh).dot(span) / denom
        axis = sh + span * max(0.0, min(1.0, t))
        rad = (world - axis).length
        if t < -0.1 or t > 1.15:
            continue
        hang = max(0.0, axis.z - world.z)
        if rad > height * 0.055 or hang > height * 0.06:
            far += 1
            off_max = max(off_max, rad, hang)
    return {
        "off_axis": int(far),
        "off_max": float(off_max),
        "extent": float(extent),
    }


def _side_face_span(obj, marks, side):
    """Max world span of an outboard face. Paper flaps are long."""
    chest = marks.get("chest")
    mid = chest.x if chest is not None else 0.0
    sign = 1.0 if side == "l" else -1.0
    torso = float(marks.get("torso_half_x") or 0.02)
    mw = obj.matrix_world
    best = 0.0
    for poly in obj.data.polygons:
        pts = [mw @ obj.data.vertices[i].co for i in poly.vertices]
        if len(pts) < 3:
            continue
        acc = Vector((0.0, 0.0, 0.0))
        for point in pts:
            acc += point
        center = acc / float(len(pts))
        if (center.x - mid) * sign < torso * 0.35:
            continue
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        zs = [p.z for p in pts]
        span = max(
            max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
        )
        best = max(best, float(span))
    return best


def _neck_opening(obj, marks):
    """Hole vs brim at the neck plane. Span is shoulder width."""
    neck = marks["neck"]
    mins, maxs = body_bounds(obj)
    band = max((maxs.z - mins.z) * 0.05, 0.0015)
    rot = obj.matrix_world.to_3x3()
    ring, up = [], []
    for vert in obj.data.vertices:
        world = obj.matrix_world @ vert.co
        if abs(world.z - neck.z) > band:
            continue
        r = (world - neck).xy.length
        nrm = (rot @ vert.normal).normalized()
        if nrm.z > 0.35:
            up.append(r)
        if abs(nrm.z) < 0.60 and r > band:
            ring.append(r)
    ring.sort()
    hole = ring[int(len(ring) * 0.70)] if ring else 0.0
    brim = max(up) if up else hole
    span = _opening_width(obj, neck.z)
    ratio = brim / hole if hole > 1e-6 else 0.0
    return {
        "hole": float(hole),
        "brim": float(brim),
        "brim_ratio": float(ratio),
        "span": float(span),
    }


def _sleeve_report(shirt, body, marks):
    """Shirt vs arm tube. Ratio ~1.2 is fitted; along=0 is a vest."""
    bmins, bmaxs = body_bounds(body)
    height = max(bmaxs.z - bmins.z, 0.01)
    mid = marks["chest"].x
    body_w = _band_half_x(
        body, mid, marks["hem"].z, marks["chest"].z, marks, height,
    )
    shirt_w = _band_half_x(
        shirt, mid, marks["hem"].z, marks["chest"].z, marks, height,
    )
    out = {
        "underarm_flare": float(
            shirt_w / body_w if body_w > 1e-6 else 0.0
        ),
    }
    for side in ("l", "r"):
        s_st = _arm_stats(shirt, marks, side, height)
        a_st = _arm_stats(body, marks, side, height)
        ratio = (
            s_st["radius"] / a_st["radius"]
            if a_st["radius"] > 1e-6 else 0.0
        )
        fat = (
            s_st["radius_max"] / a_st["radius"]
            if a_st["radius"] > 1e-6 else 0.0
        )
        flap = _flap_stats(shirt, marks, side, height)
        out[side] = {
            "shirt": s_st["radius"],
            "arm": a_st["radius"],
            "ratio": float(ratio),
            "fat": float(fat),
            "along": s_st["along"],
            "drop": s_st["drop"],
            "off_axis": flap["off_axis"],
            "off_max": flap["off_max"],
            "extent": flap["extent"],
            "side_span": float(_side_face_span(shirt, marks, side)),
        }
    ext_l = float((out.get("l") or {}).get("extent") or 0.0)
    ext_r = float((out.get("r") or {}).get("extent") or 0.0)
    out["asymmetry"] = float(
        abs(ext_l - ext_r) / max(ext_l, ext_r, 1e-6)
    )
    return out


def _clip_regions(shirt, body, marks):
    """Outer-shell penetrations grouped by landmark region."""
    bmins, bmaxs = body_bounds(body)
    height = max(bmaxs.z - bmins.z, 0.01)
    mid = marks["chest"].x
    dg = bpy.context.evaluated_depsgraph_get()
    ev = shirt.evaluated_get(dg)
    mesh = ev.to_mesh()
    mesh.transform(ev.matrix_world)
    tree = BVHTree.FromObject(body, dg)
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for vert in mesh.vertices:
        mins.x = min(mins.x, vert.co.x)
        mins.y = min(mins.y, vert.co.y)
        mins.z = min(mins.z, vert.co.z)
        maxs.x = max(maxs.x, vert.co.x)
        maxs.y = max(maxs.y, vert.co.y)
        maxs.z = max(maxs.z, vert.co.z)
    center = (mins + maxs) * 0.5
    dists = [(v.co - center).length for v in mesh.vertices]
    dists.sort()
    cutoff = dists[int(len(dists) * 0.45)] if dists else 0.0
    buckets = {}
    for vert in mesh.vertices:
        if (vert.co - center).length < cutoff:
            continue
        loc, nrm, _i, _d = tree.find_nearest(vert.co)
        if loc is None or nrm is None:
            continue
        gap = (vert.co - loc).dot(nrm.normalized())
        if gap >= -0.001:
            continue
        p = vert.co
        if _is_sleeve_vert(p, marks, height):
            name = "sleeve_l" if p.x >= mid else "sleeve_r"
        elif p.z < marks["hem"].z + height * 0.10:
            name = "hem"
        elif abs(p.x - mid) > height * 0.14 and p.z > marks["chest"].z:
            name = "armpit"
        elif p.z > marks["chest"].z:
            name = "chest"
        else:
            name = "torso"
        slot = buckets.setdefault(name, {"count": 0, "min": 0.0})
        slot["count"] += 1
        slot["min"] = min(slot["min"], float(gap))
    ev.to_mesh_clear()
    return buckets
'''
