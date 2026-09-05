"""Adapter registry, doctor scan, and capability roll-up."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mason.core.config import (
    MachineConfig,
    load_machine_config,
    override_path,
    save_machine_config,
)
from mason.tools.aseprite.adapter import AsepriteAdapter
from mason.tools.base import ToolAdapter, ToolInfo
from mason.tools.blender.adapter import BlenderAdapter
from mason.tools.imagemagick.adapter import ImageMagickAdapter
from mason.tools.krita.adapter import KritaAdapter

ADAPTERS: dict[str, ToolAdapter] = {
    "blender": BlenderAdapter(),
    "krita": KritaAdapter(),
    "aseprite": AsepriteAdapter(),
    "imagemagick": ImageMagickAdapter(),
}

# Human doctor groups
TOOL_GROUPS = {
    "3D": ["blender"],
    "Raster": ["krita", "imagemagick"],
    "Sprites": ["aseprite"],
}

ALL_CAPABILITIES = [
    "procedural_3d",
    "render_preview",
    "glb_export",
    "raster_document",
    "layered_raster",
    "image_export",
    "raster_processing",
    "sprite_animation",
]


def get_adapter(tool_id: str) -> ToolAdapter:
    return ADAPTERS[tool_id]


def detect_all(config: MachineConfig | None = None) -> dict[str, ToolInfo]:
    """Detect every registered tool using machine overrides."""
    config = config or load_machine_config()
    results: dict[str, ToolInfo] = {}
    for tool_id, adapter in ADAPTERS.items():
        results[tool_id] = adapter.detect(override_path(config, tool_id))
    return results


def capabilities_from(tools: dict[str, ToolInfo]) -> list[str]:
    """Capabilities provided by currently available tools."""
    caps: list[str] = []
    for tool_id, info in tools.items():
        if not info.available:
            continue
        caps.extend(ADAPTERS[tool_id].capabilities())
    # stable unique
    seen: set[str] = set()
    ordered: list[str] = []
    for cap in ALL_CAPABILITIES:
        if cap in caps and cap not in seen:
            seen.add(cap)
            ordered.append(cap)
    return ordered


def doctor_payload(tools: dict[str, ToolInfo]) -> dict[str, Any]:
    """JSON document for mason doctor --json."""
    caps = capabilities_from(tools)
    ready = bool(tools.get("blender") and tools["blender"].available)
    tool_json = {}
    for tool_id, info in tools.items():
        entry: dict[str, Any] = {"available": info.available}
        if info.path:
            entry["path"] = info.path
        if info.version:
            entry["version"] = info.version
        if info.extras:
            entry["extras"] = info.extras
        tool_json[tool_id] = entry
    return {
        "ready": ready,
        "tools": tool_json,
        "capabilities": caps,
    }


def scan_and_store(config: MachineConfig | None = None) -> dict[str, ToolInfo]:
    """Detect tools and write found paths without clobbering overrides."""
    config = config or load_machine_config()
    tools = detect_all(config)
    dirty = False
    for tool_id, info in tools.items():
        current = getattr(config.tools, tool_id)
        if current.path or not info.available or not info.path:
            continue
        current.path = info.path
        dirty = True
    if dirty:
        save_machine_config(config)
    return tools


def require_tool(tool_id: str) -> ToolInfo:
    """Detect a tool and raise if it cannot run."""
    config = load_machine_config()
    adapter = get_adapter(tool_id)
    info = adapter.detect(override_path(config, tool_id))
    adapter.validate_installation(info)
    return info
