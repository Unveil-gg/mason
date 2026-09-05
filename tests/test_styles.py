"""Style loading and palette lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from mason.core.styles import DEFAULT_STYLE_YAML, load_style
from mason.errors import MasonError


def test_load_default_style(tmp_path: Path) -> None:
    path = tmp_path / "default.yaml"
    path.write_text(DEFAULT_STYLE_YAML, encoding="utf-8")
    style = load_style(path)
    assert style.name == "default"
    assert style.color("wood_dark") == "#654936"
    assert style.geometry.bevel_width == 0.02
    assert style.textures.tile_size == 1.0
    assert style.textures.wrap == "repeat"


def test_missing_palette_key(tmp_path: Path) -> None:
    path = tmp_path / "default.yaml"
    path.write_text(DEFAULT_STYLE_YAML, encoding="utf-8")
    style = load_style(path)
    with pytest.raises(MasonError) as exc:
        style.color("neon")
    assert exc.value.code == "unknown_palette_key"


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MasonError) as exc:
        load_style(tmp_path / "missing.yaml")
    assert exc.value.code == "style_not_found"
