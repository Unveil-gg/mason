"""Asset-type router: declared production method, not a new generator."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

WorkflowKind = Literal[
    "prop",
    "building",
    "turned",
    "sculptural",
    "clothing_fitted",
    "clothing_loose",
    "character",
    "illustrated",
    "texture",
    "pixel",
    "import",
]

WORKFLOWS: tuple[str, ...] = (
    "prop",
    "building",
    "turned",
    "sculptural",
    "clothing_fitted",
    "clothing_loose",
    "character",
    "illustrated",
    "texture",
    "pixel",
    "import",
)

# Keyword hints for mason route. First matching group wins.
_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pixel", ("sprite", "pixel art", "aseprite", "pixel character")),
    ("texture", ("texture", "albedo", "normal map", "uv paint", "fabric pattern")),
    ("illustrated", (
        "cover", "poster", "menu", "card", "sticker", "sign",
        "decal", "label", "billboard",
    )),
    ("clothing_loose", (
        "loose shirt", "hoodie", "tunic", "oversized", "coat",
        "drape", "cloth sim",
    )),
    ("clothing_fitted", (
        "shirt", "garment", "clothing", "clothes", "fitted", "dress",
    )),
    ("character", ("character", "humanoid", "customer", "barista", "npc")),
    ("turned", (
        "pawn", "rook", "bishop", "queen", "king", "lathe", "vase",
        "column", "goblet", "stem",
    )),
    ("building", (
        "house", "townhouse", "mansion", "building", "facade",
        "storefront",
    )),
    ("sculptural", (
        "knight", "animal", "sculpture", "organic", "creature",
        "statue",
    )),
    ("import", ("import", "custom mesh", "licensed", "bought mesh")),
    ("prop", ("shelf", "crate", "table", "cart", "hydrant", "furniture")),
)

_CARDS: dict[str, dict[str, Any]] = {
    "prop": {
        "type": "static_prop",
        "summary": "Procedural parts + snap for furniture and simple props.",
        "required_refs": [],
        "operations": (
            "box", "cylinder", "snap", "array", "mirror", "cutout",
            "component",
        ),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": (
            "shapes", "snap", "cutout", "components", "recipes_note",
            "modeling", "inspect", "critique", "iteration",
        ),
        "shapes": (
            "box", "cylinder", "plane", "tapered_box", "instance",
        ),
    },
    "building": {
        "type": "static_prop",
        "summary": "Modular parts + ornaments; decompose when masses > 2.",
        "required_refs": ["front", "three_quarter"],
        "operations": (
            "box", "snap", "flush", "component", "decal", "decompose",
        ),
        "examples": (),
        "decompose": True,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": (
            "shapes", "snap", "decal_face", "components", "decompose",
            "texture", "taste", "inspect", "critique",
        ),
        "shapes": ("box", "tapered_box", "plane", "instance"),
    },
    "turned": {
        "type": "static_prop",
        "summary": "2D side profile then lathe; add identifying attachments.",
        "required_refs": ["side"],
        "operations": ("lathe", "profile", "attachments"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": (
            "lathe", "attachments", "geometric_plan", "reference",
            "inspect", "critique", "iteration",
        ),
        "shapes": ("lathe", "cylinder", "instance"),
    },
    "sculptural": {
        "type": "static_prop",
        "summary": "Decompose or import; do not force primitives.",
        "required_refs": ["three_quarter", "side"],
        "operations": ("decompose", "instance", "skin", "outline", "import"),
        "examples": (),
        "decompose": True,
        "prefer_import": True,
        "painterly": False,
        "vocab_keys": (
            "shapes", "skin", "outline", "bodies", "decompose",
            "inspect", "critique", "iteration",
        ),
        "shapes": (
            "sphere", "skin", "outline", "curve", "instance",
        ),
    },
    "clothing_fitted": {
        "type": "static_prop",
        "summary": (
            "Second-skin extract from the body; paint details. "
            "No cloth sim."
        ),
        "required_refs": ["worn"],
        "operations": ("garment", "fit", "weight_transfer"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": (
            "garment", "inspect", "critique", "iteration", "texture",
        ),
        "shapes": (),
    },
    "clothing_loose": {
        "type": "static_prop",
        "summary": (
            "Later drape path. Same extract unless "
            "pipeline is drape."
        ),
        "required_refs": ["worn"],
        "operations": ("garment", "fit", "drape", "weight_transfer"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": (
            "garment", "drape", "inspect", "critique", "iteration",
        ),
        "shapes": (),
    },
    "character": {
        "type": "static_prop",
        "summary": "Instance an approved body/rig; Mason does not invent one.",
        "required_refs": ["three_quarter"],
        "operations": ("instance", "import"),
        "examples": (),
        "decompose": True,
        "prefer_import": True,
        "painterly": False,
        "vocab_keys": ("decompose", "inspect", "critique", "iteration"),
        "shapes": ("instance",),
    },
    "illustrated": {
        "type": "layered_raster",
        "summary": "Krita painting desk for covers, cards, posters, signs.",
        "required_refs": [],
        "operations": ("layered_raster", "paint", "stamps", "text"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": True,
        "vocab_keys": (
            "raster", "geometric_plan", "inspect", "critique", "iteration",
        ),
        "shapes": (),
    },
    "texture": {
        "type": "layered_raster",
        "summary": "UV layout to Krita paint, then back onto the mesh.",
        "required_refs": [],
        "operations": ("uv_layout", "paint", "image_process"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": True,
        "vocab_keys": ("raster", "texture", "inspect", "critique"),
        "shapes": (),
    },
    "pixel": {
        "type": "sprite_sheet",
        "summary": "Approve one still, then animate in Aseprite.",
        "required_refs": [],
        "operations": ("pixels", "master_frame", "anchors"),
        "examples": (),
        "decompose": False,
        "prefer_import": False,
        "painterly": False,
        "vocab_keys": ("sprites", "inspect", "critique", "iteration"),
        "shapes": (),
    },
    "import": {
        "type": "static_prop",
        "summary": "Use a custom/licensed GLB; assemble, shade, validate.",
        "required_refs": [],
        "operations": ("instance", "materials", "validate", "export"),
        "examples": (),
        "decompose": False,
        "prefer_import": True,
        "painterly": False,
        "vocab_keys": ("inspect", "iteration", "variants"),
        "shapes": ("instance",),
    },
}


class RouteCard(BaseModel):
    """Recommendation returned by mason route."""

    model_config = ConfigDict(extra="forbid")

    workflow: str
    type: str
    summary: str
    required_refs: list[str]
    operations: list[str]
    examples: list[str]
    decompose: bool
    prefer_import: bool
    painterly: bool
    subject: str = ""
    masters: list[str] = []


def infer_workflow(subject: str, spec: Any = None) -> str:
    """Pick a workflow from subject text and an optional spec."""
    from_spec = _workflow_from_spec(spec)
    if from_spec:
        return from_spec
    text = (subject or "").strip().lower()
    for kind, words in _HINTS:
        if any(word in text for word in words):
            return kind
    return "prop"


def route_card(
    subject: str,
    spec: Any = None,
    masters: list[str] | None = None,
) -> RouteCard:
    """Build the JSON card for mason route."""
    kind = infer_workflow(subject, spec)
    raw = _CARDS[kind]
    return RouteCard(
        workflow=kind,
        type=raw["type"],
        summary=raw["summary"],
        required_refs=list(raw["required_refs"]),
        operations=list(raw["operations"]),
        examples=list(raw["examples"]),
        decompose=bool(raw["decompose"]),
        prefer_import=bool(raw["prefer_import"]),
        painterly=bool(raw["painterly"]),
        subject=subject,
        masters=list(masters or []),
    )


def scope_vocab(payload: dict[str, Any], workflow: str) -> dict[str, Any]:
    """Return only the vocab keys and shapes for one workflow."""
    if workflow not in _CARDS:
        raise ValueError(f"unknown workflow: {workflow}")
    card = _CARDS[workflow]
    keep = set(card["vocab_keys"]) | {"workflows", "recipes_note"}
    scoped = {
        "workflow": workflow,
        "workflows": list(WORKFLOWS),
        "operations": list(card["operations"]),
        "examples": list(card["examples"]),
        "prefer_import": card["prefer_import"],
        "painterly": card["painterly"],
        "decompose": card["decompose"],
    }
    shapes = card["shapes"]
    if shapes:
        scoped["shapes"] = list(shapes)
    for key, value in payload.items():
        if key in keep:
            scoped[key] = value
    return scoped


def _workflow_from_spec(spec: Any) -> str | None:
    if spec is None:
        return None
    declared = getattr(spec, "workflow", None)
    if declared:
        return declared
    geom = getattr(spec, "geometry", None)
    garment = getattr(geom, "garment", None) if geom else None
    if garment is not None:
        pipeline = getattr(garment, "pipeline", "stylized")
        fit = getattr(garment, "fit", "fitted")
        if pipeline == "drape" or fit in ("loose", "oversized"):
            return "clothing_loose"
        return "clothing_fitted"
    spec_type = getattr(spec, "type", None)
    if spec_type == "sprite_sheet":
        return "pixel"
    if spec_type == "image_process":
        return "texture"
    if spec_type == "layered_raster":
        return "illustrated"
    return None
