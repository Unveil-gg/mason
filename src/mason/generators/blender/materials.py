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


def create_material(
    name, hex_color, roughness, metallic, variation=0.0, wear=0.0,
    noise_scale=0.0,
):
    """Create a Principled BSDF material. Returns the material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(
        n for n in nodes if n.type == "BSDF_PRINCIPLED"
    )
    rgb = hex_to_rgb(hex_color)
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    base = (rgb[0], rgb[1], rgb[2], 1.0)
    vary = max(float(variation), float(wear) * 0.25)
    if vary > 0.001:
        noise = nodes.new("ShaderNodeTexNoise")
        scale = float(noise_scale) if noise_scale else 24.0
        noise.inputs["Scale"].default_value = scale + float(wear) * 8.0
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MIX"
        mix.inputs["Fac"].default_value = min(vary, 0.45)
        mix.inputs["Color1"].default_value = base
        mix.inputs["Color2"].default_value = (
            rgb[0] * 0.65, rgb[1] * 0.65, rgb[2] * 0.65, 1.0,
        )
        links.new(noise.outputs["Fac"], mix.inputs["Fac"])
        links.new(mix.outputs["Color"], color_in)
    else:
        color_in.default_value = base
    rough = min(1.0, float(roughness) + float(wear) * 0.2)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = float(metallic)
    return mat


def _socket(bsdf, *names):
    """First matching Principled input, or None."""
    for name in names:
        if name in bsdf.inputs:
            return bsdf.inputs[name]
    return None


def apply_shader(mat, shader, params=None):
    """Tune a Principled tree for a named shader. fabric adds sheen."""
    params = params or {}
    if shader != "fabric":
        return
    bsdf = next(
        n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    sheen = _socket(bsdf, "Sheen Weight", "Sheen")
    if sheen is not None:
        sheen.default_value = float(params.get("sheen", 0.35))
    tint = _socket(bsdf, "Sheen Tint")
    if tint is not None and tint.type == "VALUE":
        tint.default_value = float(params.get("sheen_tint", 0.5))


def apply_bump_and_normal(
    mat, wrap, bump_path=None, normal_path=None, bump_strength=0.04,
):
    """Wire bump (height) and/or a normal map into Principled."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    normal_out = None
    ext = "REPEAT" if wrap == "repeat" else "EXTEND"
    if normal_path:
        ntex = nodes.new("ShaderNodeTexImage")
        ntex.image = bpy.data.images.load(normal_path)
        ntex.image.colorspace_settings.name = "Non-Color"
        ntex.extension = ext
        nmap = nodes.new("ShaderNodeNormalMap")
        links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        normal_out = nmap.outputs["Normal"]
    if bump_path:
        btex = nodes.new("ShaderNodeTexImage")
        btex.image = bpy.data.images.load(bump_path)
        btex.image.colorspace_settings.name = "Non-Color"
        btex.extension = ext
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = float(bump_strength)
        links.new(btex.outputs["Color"], bump.inputs["Height"])
        if normal_out is not None:
            links.new(normal_out, bump.inputs["Normal"])
        normal_out = bump.outputs["Normal"]
    if normal_out is not None:
        links.new(normal_out, bsdf.inputs["Normal"])


def create_textured_material(
    name, image_path, roughness, metallic, wrap, roughness_path=None,
    bump_path=None, normal_path=None, bump_strength=0.04,
    shader="principled", shader_params=None,
):
    """Create a Principled BSDF material with an Image Texture as its
    Base Color, loaded from a previously-built 2D asset's PNG."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(
        n for n in nodes if n.type == "BSDF_PRINCIPLED"
    )
    bsdf.inputs["Roughness"].default_value = float(roughness)
    bsdf.inputs["Metallic"].default_value = float(metallic)
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(image_path)
    tex_node.extension = "REPEAT" if wrap == "repeat" else "EXTEND"
    color_in = bsdf.inputs.get("Base Color") or bsdf.inputs.get("Color")
    links.new(tex_node.outputs["Color"], color_in)
    if roughness_path:
        rough_tex = nodes.new("ShaderNodeTexImage")
        rough_tex.image = bpy.data.images.load(roughness_path)
        rough_tex.image.colorspace_settings.name = "Non-Color"
        rough_tex.extension = (
            "REPEAT" if wrap == "repeat" else "EXTEND"
        )
        links.new(rough_tex.outputs["Color"], bsdf.inputs["Roughness"])
    apply_shader(mat, shader, shader_params)
    apply_bump_and_normal(
        mat, wrap, bump_path, normal_path, bump_strength,
    )
    return mat


def assign_material(obj, mat):
    """Assign a material to a mesh object."""
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
'''
