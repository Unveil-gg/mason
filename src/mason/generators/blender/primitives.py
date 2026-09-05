"""Blender source snippets for box primitives."""

CREATE_BOX_SRC = r'''
def create_box(name, size, location, rotation=(0.0, 0.0, 0.0)):
    """Add a cube sized and placed in world space. Returns the object."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def apply_bevel(obj, width, segments):
    """Apply a Bevel modifier and keep it applied."""
    if width <= 0 or segments < 1:
        return
    mod = obj.modifiers.new(name="Bevel", type="BEVEL")
    mod.width = float(width)
    mod.segments = int(segments)
    mod.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
'''
