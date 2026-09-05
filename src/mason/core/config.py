"""Machine-local and project configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from mason.errors import MasonError

TOOL_IDS = ("blender", "krita", "aseprite", "imagemagick")


class ToolPathConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = None


class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blender: ToolPathConfig = Field(default_factory=ToolPathConfig)
    krita: ToolPathConfig = Field(default_factory=ToolPathConfig)
    aseprite: ToolPathConfig = Field(default_factory=ToolPathConfig)
    imagemagick: ToolPathConfig = Field(default_factory=ToolPathConfig)


class MachineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tools: ToolsConfig = Field(default_factory=ToolsConfig)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "mason-project"
    default_style: str = "default"


def machine_config_path() -> Path:
    """Return the platform-specific machine config path."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise MasonError(
                "APPDATA is not set; cannot locate Mason config.",
                code="config_path",
            )
        return Path(appdata) / "Mason" / "config.yaml"
    return Path.home() / ".config" / "mason" / "config.yaml"


def load_machine_config() -> MachineConfig:
    """Load machine config, or empty defaults if missing."""
    path = machine_config_path()
    if not path.is_file():
        return MachineConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return MachineConfig.model_validate(data)


def save_machine_config(config: MachineConfig) -> Path:
    """Write machine config. Returns the path."""
    path = machine_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    return path


def override_path(config: MachineConfig, tool_id: str) -> Path | None:
    """Return a configured executable path for a tool, if any."""
    tool = getattr(config.tools, tool_id, None)
    if tool is None or not tool.path:
        return None
    return Path(tool.path)


def set_dotted(config: MachineConfig, key: str, value: str) -> MachineConfig:
    """Set a dotted config key like tools.blender.path."""
    parts = key.split(".")
    if parts != ["tools", parts[1] if len(parts) > 1 else "", "path"]:
        raise MasonError(
            f"Unsupported config key '{key}'.",
            code="invalid_config_key",
            hint="Use tools.<name>.path",
        )
    tool_id = parts[1]
    if tool_id not in TOOL_IDS:
        raise MasonError(
            f"Unknown tool '{tool_id}'.",
            code="unknown_tool",
            context={"tools": list(TOOL_IDS)},
        )
    data = config.model_dump()
    data["tools"][tool_id]["path"] = value or None
    return MachineConfig.model_validate(data)


def get_dotted(config: MachineConfig, key: str) -> Any:
    """Read a dotted config key."""
    cur: Any = config.model_dump()
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise MasonError(
                f"Unknown config key '{key}'.",
                code="invalid_config_key",
            )
        cur = cur[part]
    return cur


def load_project_config(root: Path) -> ProjectConfig:
    """Load mason.yaml from a project root."""
    path = root / "mason.yaml"
    if not path.is_file():
        raise MasonError(
            f"No mason.yaml in {root}.",
            code="not_a_project",
            hint="Run mason init in the project directory.",
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ProjectConfig.model_validate(data)


def save_project_config(root: Path, config: ProjectConfig) -> Path:
    """Write mason.yaml. Returns the path."""
    path = root / "mason.yaml"
    path.write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    return path
