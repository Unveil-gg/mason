"""Blender source snippets for studio lighting and cameras."""

PREVIEW_SCENE_SRC = r'''
def clear_non_mesh():
    """Remove cameras and lights so previews are deterministic."""
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def setup_cycles(resolution, samples):
    """Configure Cycles CPU and transparent film."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(samples)
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 15
    scene.view_settings.view_transform = "Standard"


def setup_studio_lights(center, distance):
    """Three-point lights around the asset."""
    def add_light(name, energy, loc):
        light = bpy.data.lights.new(name=name, type="AREA")
        light.energy = energy
        light.size = max(distance * 0.4, 0.5)
        obj = bpy.data.objects.new(name, light)
        obj.location = loc
        bpy.context.scene.collection.objects.link(obj)
        return obj

    add_light("key", 40.0, center + Vector((distance, -distance, distance)))
    add_light("fill", 12.0, center + Vector((-distance, -distance * 0.4, distance * 0.6)))
    add_light("rim", 18.0, center + Vector((0.0, distance, distance * 0.8)))


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


def render_previews(preview_dir, resolution, samples):
    """Render front/side/top/three_quarter PNGs."""
    clear_non_mesh()
    setup_cycles(resolution, samples)
    mins, maxs = scene_bounds()
    center = (mins + maxs) * 0.5
    size = maxs - mins
    radius = max(size.x, size.y, size.z, 0.1)
    dist = radius * 2.4
    clip_end = dist * 8.0
    setup_studio_lights(center, dist)
    views = {
        "front": center + Vector((0.0, -dist, size.z * 0.15)),
        "side": center + Vector((dist, 0.0, size.z * 0.15)),
        "top": center + Vector((0.0, 0.0, dist)),
        "three_quarter": center + Vector((dist * 0.75, -dist * 0.75, dist * 0.55)),
    }
    os.makedirs(preview_dir, exist_ok=True)
    for name, loc in views.items():
        if bpy.context.scene.camera:
            bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)
        setup_camera(center, loc, clip_end)
        out = os.path.join(preview_dir, name + ".png")
        bpy.context.scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
'''
