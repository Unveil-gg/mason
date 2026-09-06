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


def setup_studio_lights(center, distance, preset="neutral_studio"):
    """Three-point lights around the asset."""
    scale = 1.6 if preset == "high_key" else 1.0

    def add_light(name, energy, loc):
        light = bpy.data.lights.new(name=name, type="AREA")
        light.energy = energy * scale
        light.size = max(distance * 0.4, 0.5)
        obj = bpy.data.objects.new(name, light)
        obj.location = loc
        bpy.context.scene.collection.objects.link(obj)
        return obj

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
        size=max(radius * 10.0, 4.0),
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
    """Neutral gray Principled on every non-studio mesh."""
    mat = bpy.data.materials.new(name="_mason_clay")
    mat.use_nodes = True
    bsdf = next(
        n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    color_in.default_value = (0.55, 0.55, 0.55, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Metallic"].default_value = 0.0
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


def render_previews(preview_dir, resolution, samples, engine="eevee"):
    """Render beauty, clay, and silhouette views."""
    clear_non_mesh()
    used = setup_renderer(resolution, samples, engine, transparent=False)
    mins, maxs = scene_bounds()
    center = (mins + maxs) * 0.5
    size = maxs - mins
    radius = max(size.x, size.y, size.z, 0.1)
    dist = radius * 2.4
    clip_end = dist * 8.0
    preset = CONFIG.get("lighting_preset") or "neutral_studio"
    set_world((0.62, 0.62, 0.65), 0.35)
    setup_studio_plate(center, mins, radius)
    setup_studio_lights(center, dist, preset)
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
