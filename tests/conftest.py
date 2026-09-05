"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mason.core.styles import DEFAULT_STYLE_YAML
from mason.core.workspace import init_project


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Initialized Mason project in a temp directory."""
    init_project(tmp_path, name="test")
    (tmp_path / "styles" / "default.yaml").write_text(
        DEFAULT_STYLE_YAML,
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def crate_yaml(project: Path) -> Path:
    spec = {
        "type": "static_prop",
        "id": "simple_crate",
        "name": "Simple Crate",
        "dimensions": {"width": 0.6, "depth": 0.6, "height": 0.6},
        "style": "default",
        "geometry": {"recipe": "crate", "bevel": True},
        "materials": {"primary": "wood_dark"},
        "export": {"format": "glb", "save_blend": True},
    }
    path = project / "crate.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return path
