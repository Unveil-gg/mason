"""Bone and mesh landmarks for non-human characters."""

CREATE_GARMENT_ANATOMY_SRC = r'''
_BONE_ALIASES = {
    "head": ("head.x", "c_head.x", "head", "Head"),
    "neck": ("neck.x", "c_neck.x", "neck", "Neck"),
    "chest": ("spine_03.x", "spine_02.x", "spine.003", "chest"),
    "belly": ("spine_02.x", "spine_01.x", "spine.002"),
    "waist": ("spine_01.x", "c_root.x", "spine.001"),
    "hips": ("c_root.x", "root.x", "hips", "Hips"),
    "shoulder_l": ("shoulder.l", "c_shoulder.l", "shoulder.L"),
    "shoulder_r": ("shoulder.r", "c_shoulder.r", "shoulder.R"),
    "arm_l": ("arm.l", "c_arm_fk.l", "upper_arm.L"),
    "arm_r": ("arm.r", "c_arm_fk.r", "upper_arm.R"),
    "forearm_l": ("forearm.l", "c_forearm_fk.l", "forearm.L"),
    "forearm_r": ("forearm.r", "c_forearm_fk.r", "forearm.R"),
    "wrist_l": ("hand.l", "c_hand_fk.l", "hand.L", "hand_ref.l"),
    "wrist_r": ("hand.r", "c_hand_fk.r", "hand.R", "hand_ref.r"),
    "thigh_l": ("thigh.l", "c_thigh_fk.l", "thigh.L"),
    "thigh_r": ("thigh.r", "c_thigh_fk.r", "thigh.R"),
    "knee_l": ("leg.l", "c_leg_fk.l", "shin.L"),
    "knee_r": ("leg.r", "c_leg_fk.r", "shin.R"),
    "ankle_l": ("foot.l", "c_foot_fk.l", "foot.L", "foot_ref.l"),
    "ankle_r": ("foot.r", "c_foot_fk.r", "foot.R", "foot_ref.r"),
    "tail": ("tail.x", "c_tail.x", "tail", "Tail"),
}


def _find_armature():
    """First armature in the scene, or None."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def analyze_anatomy(obj):
    """Landmarks from bones when present, else the body AABB.

    Does not assume human proportions. Returns a dict of Vectors.
    """
    mins, maxs = body_bounds(obj)
    mid = (mins + maxs) * 0.5
    h = max(maxs.z - mins.z, 0.001)
    def at(t):
        return mins.z + h * t
    width = maxs.x - mins.x
    marks = {
        "head": Vector((mid.x, mid.y, at(0.88))),
        "neck": Vector((mid.x, mid.y, at(0.72))),
        "shoulders": Vector((mid.x, mid.y, at(0.62))),
        "shoulder_l": Vector((mins.x + width * 0.28, mid.y, at(0.60))),
        "shoulder_r": Vector((maxs.x - width * 0.28, mid.y, at(0.60))),
        "chest": Vector((mid.x, mid.y, at(0.52))),
        "belly": Vector((mid.x, mid.y, at(0.40))),
        "waist": Vector((mid.x, mid.y, at(0.34))),
        "hips": Vector((mid.x, mid.y, at(0.28))),
        "hem": Vector((mid.x, mid.y, at(0.18))),
        "wrist_l": Vector((mins.x + width * 0.08, mid.y, at(0.48))),
        "wrist_r": Vector((maxs.x - width * 0.08, mid.y, at(0.48))),
        "ankle_l": Vector((mid.x - width * 0.12, mid.y, at(0.04))),
        "ankle_r": Vector((mid.x + width * 0.12, mid.y, at(0.04))),
        "tail": Vector((mid.x, maxs.y, at(0.30))),
    }
    arm = _find_armature()
    if arm is None:
        return marks
    found = {}
    for key, names in _BONE_ALIASES.items():
        point = _bone_head(arm, names)
        if point is not None:
            found[key] = point
            marks[key] = point
    if "shoulder_l" in found and "shoulder_r" in found:
        marks["shoulders"] = (found["shoulder_l"] + found["shoulder_r"]) * 0.5
    if "hips" in found and "belly" in found:
        marks["waist"] = (found["hips"] + found["belly"]) * 0.5
    return marks
'''
