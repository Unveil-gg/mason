"""Blender source snippets for studio lighting and cameras."""

PREVIEW_SCENE_SRC = r'''
def clear_non_mesh():
    """Remove cameras, lights, and prior studio plates."""
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"} or obj.name.startswith("_mason_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def setup_film(resolution, transparent):
    """Shared resolution and PNG settings."""
    scene = bpy.context.scene
    scene.render.film_transparent = bool(transparent)
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 15
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass


def _hex_luma(value):
    """Rec. 709 luma of a #RRGGBB string, or 0."""
    text = str(value or "").lstrip("#")
    if len(text) == 3:
        text = "".join(c + c for c in text)
    if len(text) != 6:
        return 0.0
    try:
        r = int(text[0:2], 16) / 255.0
        g = int(text[2:4], 16) / 255.0
        b = int(text[4:6], 16) / 255.0
    except ValueError:
        return 0.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _pale_preview():
    """True when a garment hero would vanish on a light studio."""
    if not CONFIG.get("garment"):
        return False
    pal = CONFIG.get("palette") or {}
    for value in pal.values():
        if _hex_luma(value) >= 0.62:
            return True
    return True


def _tint_plate(rgb):
    """Set the studio ground albedo."""
    plate = bpy.data.objects.get("_mason_ground")
    if plate is None or not plate.data.materials:
        return
    pmat = plate.data.materials[0]
    if not pmat or not pmat.use_nodes:
        return
    pbsdf = next(
        n for n in pmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    pin = pbsdf.inputs.get("Base Color") or pbsdf.inputs.get("Color")
    pin.default_value = (rgb[0], rgb[1], rgb[2], 1.0)


def set_world(color, strength):
    """Solid world background so dark props read against a plate."""
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("MasonWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is None:
        bg = scene.world.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (
        color[0], color[1], color[2], 1.0,
    )
    bg.inputs[1].default_value = float(strength)


def setup_cycles(resolution, samples, transparent=False):
    """Configure Cycles CPU."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(samples)
    scene.cycles.use_denoising = False
    setup_film(resolution, transparent)


def setup_eevee(resolution, samples, transparent=False):
    """Try EEVEE Next, then EEVEE. Returns True if set."""
    scene = bpy.context.scene
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = name
            setup_film(resolution, transparent)
            eevee = getattr(scene, "eevee", None)
            if eevee is not None and hasattr(eevee, "taa_render_samples"):
                eevee.taa_render_samples = max(int(samples), 8)
            return True
        except TypeError:
            continue
    return False


def setup_renderer(resolution, samples, preferred, transparent=False):
    """Prefer EEVEE; fall back to Cycles. Returns engine label."""
    want = (preferred or "eevee").lower()
    if want == "eevee" and setup_eevee(resolution, samples, transparent):
        return "eevee"
    setup_cycles(resolution, samples, transparent)
    return "cycles"


def boost_shadow_quality():
    """EEVEE's area-light shadows are raytraced with 1 ray/sample by
    default; at the low TAA sample counts styles use for fast builds,
    that noise gets denoised away to nothing and shadows vanish.
    Demo-lighting renders can afford to pay for a few more rays and
    samples so the cast shadow actually shows up."""
    eevee = getattr(bpy.context.scene, "eevee", None)
    if eevee is None:
        return
    if hasattr(eevee, "shadow_ray_count"):
        eevee.shadow_ray_count = 3
    if hasattr(eevee, "shadow_step_count"):
        eevee.shadow_step_count = 8
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = max(eevee.taa_render_samples, 32)


def setup_studio_lights(
    center, distance, preset="neutral_studio", demo=False,
):
    """Three-point lights around the asset. `demo` swaps in a
    warmer/higher-contrast rig for one-off demo screenshots."""
    scale = 1.6 if preset == "high_key" else 1.0

    def add_light(name, energy, loc, color=(1.0, 1.0, 1.0), size=None):
        light = bpy.data.lights.new(name=name, type="AREA")
        light.energy = energy * scale
        light.size = size if size is not None else max(
            distance * 0.4, min(0.5, distance * 2.0),
        )
        light.color = color
        obj = bpy.data.objects.new(name, light)
        obj.location = loc
        bpy.context.scene.collection.objects.link(obj)
        return obj

    if demo:
        # Preview cameras (front/side/three_quarter) all sit in the
        # +X/-Y (southeast) arc around the asset. A key light on that
        # same side is a flattering front-lit look, but its shadow
        # falls straight back, away from every camera, so it never
        # reads in the render. Putting the key on the opposite
        # (-X/+Y) side instead throws its shadow toward the cameras,
        # and a small light size keeps the shadow's edge crisp
        # instead of a huge soft area light washing it out.
        #
        # Area-light energy is total emitted power, so it must scale
        # with distance^2 (inverse-square) to keep irradiance, and
        # thus the key/world contrast that actually makes a shadow
        # visible, roughly constant across small props and big
        # builds alike. A flat wattage looked fine on small assets
        # and invisible on a mansion-scale build.
        d2 = distance * distance
        add_light(
            "key", 40.0 * d2,
            center + Vector((-distance, distance, distance * 1.2)),
            color=(1.0, 0.93, 0.82),
            size=max(distance * 0.08, 0.2),
        )
        add_light(
            "fill", 6.0 * d2,
            center + Vector((distance * 0.7, -distance * 0.7, distance * 0.5)),
            color=(0.85, 0.9, 1.0),
        )
        add_light(
            "rim", 9.0 * d2,
            center + Vector((distance * 0.2, distance, distance * 0.7)),
            color=(0.8, 0.88, 1.0),
            size=max(distance * 0.2, 0.4),
        )
        return

    add_light("key", 40.0, center + Vector((distance, -distance, distance)))
    add_light(
        "fill", 12.0,
        center + Vector((-distance, -distance * 0.4, distance * 0.6)),
    )
    add_light("rim", 18.0, center + Vector((0.0, distance, distance * 0.8)))


def setup_studio_plate(center, mins, radius):
    """Ground and backdrop that catch shadows. Prefixed _mason_."""
    ground = bpy.data.meshes.new("_mason_ground")
    ground_obj = bpy.data.objects.new("_mason_ground", ground)
    bpy.context.scene.collection.objects.link(ground_obj)
    bpy.ops.mesh.primitive_plane_add(
        size=max(radius * 10.0, min(4.0, radius * 12.0)),
        location=(center.x, center.y, mins.z - 0.002),
    )
    plate = bpy.context.active_object
    plate.name = "_mason_ground"
    mat = bpy.data.materials.new(name="_mason_studio")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    color_in.default_value = (0.55, 0.55, 0.58, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    if plate.data.materials:
        plate.data.materials[0] = mat
    else:
        plate.data.materials.append(mat)
    bpy.data.objects.remove(ground_obj, do_unlink=True)
    if ground.users == 0:
        bpy.data.meshes.remove(ground)


def look_at(camera, target):
    """Point a camera object at a world location."""
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(center, location, clip_end):
    """Create or replace the scene camera."""
    cam_data = bpy.data.cameras.new("MasonCamera")
    cam_data.lens = 50
    cam_data.clip_start = 0.01
    cam_data.clip_end = max(clip_end, 10.0)
    camera = bpy.data.objects.new("MasonCamera", cam_data)
    camera.location = location
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    look_at(camera, center)
    return camera


def _render_view(preview_dir, name, center, loc, clip_end):
    if bpy.context.scene.camera:
        bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)
    setup_camera(center, loc, clip_end)
    out = os.path.join(preview_dir, name + ".png")
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    if not os.path.isfile(out) or os.path.getsize(out) < 32:
        raise RuntimeError("empty preview " + name)


def apply_clay_override():
    """Neutral clay on every non-studio mesh, plus a darker studio
    so the form does not disappear into a matching floor/world.
    Beauty lights stay; they are dimmed so mid-gray clay does not
    blow out to white on small props."""
    set_world((0.16, 0.17, 0.19), 0.28)
    plate = bpy.data.objects.get("_mason_ground")
    if plate is not None:
        plate.hide_render = True
        if plate.data.materials:
            pmat = plate.data.materials[0]
            if pmat and pmat.use_nodes:
                pbsdf = next(
                    n for n in pmat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED"
                )
                pin = (
                    pbsdf.inputs.get("Base Color")
                    or pbsdf.inputs.get("Color")
                )
                pin.default_value = (0.08, 0.08, 0.09, 1.0)
    for obj in bpy.data.objects:
        if obj.type == "LIGHT" and hasattr(obj.data, "energy"):
            obj.data.energy *= 0.1
    mat = bpy.data.materials.new(name="_mason_clay")
    mat.use_nodes = True
    bsdf = next(
        n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    color_in.default_value = (0.74, 0.72, 0.68, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Metallic"].default_value = 0.0
    for spec_name in ("Specular IOR Level", "Specular"):
        if spec_name in bsdf.inputs:
            bsdf.inputs[spec_name].default_value = 0.0
            break
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.startswith("_mason_"):
            continue
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def apply_silhouette_override():
    """Black emission on every non-studio mesh."""
    mat = bpy.data.materials.new(name="_mason_silhouette")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    emit.inputs[1].default_value = 1.0
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs[0], out.inputs[0])
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.name.startswith("_mason_"):
            if obj.name.startswith("_mason_") and obj.type == "MESH":
                obj.hide_render = True
            continue
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def _worn_bounds():
    """AABB of the garment plus the fit body."""
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name.startswith("_mason_") and obj.name != "_mason_body":
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


def _add_area_light(name, energy, loc, size, color):
    """One area light. Energy is Watts."""
    light = bpy.data.lights.new(name=name, type="AREA")
    light.energy = energy
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    return obj


def render_worn_preview(preview_dir, resolution, samples, engine, demo):
    """One three-quarter of the character wearing the garment."""
    body = bpy.data.objects.get("_mason_body")
    if body is None:
        return
    body.hide_set(False)
    body.hide_render = False
    for obj in bpy.data.objects:
        if obj.name.startswith("_mason_body_"):
            obj.hide_render = True
    used = setup_renderer(resolution, samples, engine, transparent=False)
    mins, maxs = _worn_bounds()
    center = (mins + maxs) * 0.5
    size = maxs - mins
    radius = max(size.x, size.y, size.z, 0.02)
    dist = radius * 2.2
    clip_end = dist * 8.0
    set_world((0.22, 0.23, 0.26), 0.16)
    setup_studio_plate(center, mins, radius)
    plate = bpy.data.objects.get("_mason_ground")
    if plate is not None and plate.data.materials:
        pmat = plate.data.materials[0]
        if pmat and pmat.use_nodes:
            pbsdf = next(
                n for n in pmat.node_tree.nodes
                if n.type == "BSDF_PRINCIPLED"
            )
            pin = (
                pbsdf.inputs.get("Base Color")
                or pbsdf.inputs.get("Color")
            )
            pin.default_value = (0.30, 0.30, 0.33, 1.0)
    key_size = max(dist * 0.3, 0.04)
    _add_area_light(
        "worn_key", 3.4,
        center + Vector((-dist * 0.85, dist * 0.35, dist * 0.95)),
        key_size, (1.0, 0.96, 0.90),
    )
    _add_area_light(
        "worn_fill", 0.85,
        center + Vector((dist * 0.55, -dist * 0.75, dist * 0.4)),
        key_size * 1.6, (0.82, 0.86, 1.0),
    )
    os.makedirs(preview_dir, exist_ok=True)
    views = {
        "worn": center + Vector((dist * 0.7, -dist * 0.85, dist * 0.4)),
        "worn_front": center + Vector((0.0, -dist, size.z * 0.1)),
        "worn_side": center + Vector((dist, 0.0, size.z * 0.1)),
    }
    for name, loc in views.items():
        _render_view(preview_dir, name, center, loc, clip_end)
    body.hide_render = True
    return used


def render_previews(
    preview_dir, resolution, samples, engine="eevee", demo_lighting=False,
):
    """Render beauty, clay, and silhouette views. `demo_lighting` is
    an opt-in, prettier rig for one-off demo/comparison screenshots;
    it does not change the stored spec or style, only this render."""
    if CONFIG.get("garment"):
        render_worn_preview(
            preview_dir, resolution, samples, engine, demo_lighting,
        )
    clear_non_mesh()
    used = setup_renderer(resolution, samples, engine, transparent=False)
    if demo_lighting and used == "eevee":
        boost_shadow_quality()
    mins, maxs = scene_bounds()
    center = (mins + maxs) * 0.5
    size = maxs - mins
    radius = max(size.x, size.y, size.z, 0.02)
    dist = radius * 2.4
    clip_end = dist * 8.0
    preset = CONFIG.get("lighting_preset") or "neutral_studio"
    pale = _pale_preview()
    if demo_lighting:
        # Much lower than neutral on purpose: the world background is
        # an unoccluded ambient dome, so even a modest strength was
        # out-illuminating the key light and erasing its cast shadow
        # entirely (uniform ambient wins over a single area light
        # unless it's kept this dim).
        set_world((0.45, 0.5, 0.58), 0.05)
    elif pale:
        set_world((0.12, 0.13, 0.15), 0.06)
    else:
        world_s = 0.16 if CONFIG.get("garment") else 0.35
        set_world((0.62, 0.62, 0.65), world_s)
    setup_studio_plate(center, mins, radius)
    setup_studio_lights(center, dist, preset, demo=demo_lighting)
    if pale:
        _tint_plate((0.08, 0.08, 0.09))
        plate = bpy.data.objects.get("_mason_ground")
        if plate is not None:
            plate.hide_render = True
        for obj in bpy.data.objects:
            if obj.type == "LIGHT" and hasattr(obj.data, "energy"):
                obj.data.energy *= 0.10
    elif CONFIG.get("garment"):
        for obj in bpy.data.objects:
            if obj.type == "LIGHT" and hasattr(obj.data, "energy"):
                obj.data.energy *= 0.22
    views = {
        "front": center + Vector((0.0, -dist, size.z * 0.15)),
        "side": center + Vector((dist, 0.0, size.z * 0.15)),
        "top": center + Vector((0.0, 0.0, dist)),
        "three_quarter": center + Vector(
            (dist * 0.75, -dist * 0.75, dist * 0.55),
        ),
        "detail": center + Vector(
            (dist * 0.42, -dist * 0.42, dist * 0.28),
        ),
    }
    os.makedirs(preview_dir, exist_ok=True)

    def render_beauty():
        for name, loc in views.items():
            _render_view(preview_dir, name, center, loc, clip_end)

    try:
        render_beauty()
    except Exception:
        if used != "cycles":
            used = "cycles"
            setup_cycles(resolution, samples, transparent=False)
            render_beauty()
        else:
            raise

    apply_clay_override()
    _render_view(
        preview_dir, "clay_three_quarter",
        center, views["three_quarter"], clip_end,
    )

    apply_silhouette_override()
    set_world((1.0, 1.0, 1.0), 1.0)
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    silhouettes = {
        "silhouette_front": views["front"],
        "silhouette_side": views["side"],
        "silhouette_three_quarter": views["three_quarter"],
    }
    for name, loc in silhouettes.items():
        _render_view(preview_dir, name, center, loc, clip_end)
    clear_non_mesh()
    CONFIG["preview_engine"] = used
'''
