"""Blender source snippets for Principled materials."""

CREATE_MATERIAL_SRC = r'''
def srgb_to_linear(channel):
    """Convert one sRGB 0-1 channel to linear."""
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def hex_to_rgb(value):
    """Convert #RRGGBB to linear RGB 0-1. Returns (r, g, b)."""
    text = value.strip().lstrip("#")
    raw = (
        int(text[0:2], 16) / 255.0,
        int(text[2:4], 16) / 255.0,
        int(text[4:6], 16) / 255.0,
    )
    return tuple(srgb_to_linear(c) for c in raw)


def create_material(name, hex_color, roughness, metallic):
    """Create a Principled BSDF material. Returns the material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = next(
        n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    rgb = hex_to_rgb(hex_color)
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    color_in.default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = float(roughness)
    bsdf.inputs["Metallic"].default_value = float(metallic)
    return mat


def assign_material(obj, mat):
    """Assign a material to a mesh object."""
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
'''
