"""Style loading and palette lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from mason.core.styles import (
    DEFAULT_STYLE_YAML,
    hex_rgba,
    load_style,
    resolve_style,
)
from mason.errors import MasonError


def test_load_default_style(tmp_path: Path) -> None:
    path = tmp_path / "default.yaml"
    path.write_text(DEFAULT_STYLE_YAML, encoding="utf-8")
    style = load_style(path)
    assert style.name == "default"
    assert style.color("wood_dark") == "#654936"
    assert style.color("label_green") == "#2E7D4F"
    assert style.color("charcoal") == "#3A3632"
    assert style.color("smoke") == "#5C5548"
    assert hex_rgba("#2E7D4F") == [46, 125, 79, 255]
    assert style.geometry.bevel_width == 0.02
    assert style.textures.tile_size == 1.0
    assert style.textures.wrap == "repeat"
    assert style.context_preview is None


def test_family_tile_size_optional(tmp_path: Path) -> None:
    path = tmp_path / "tiled.yaml"
    path.write_text(
        "name: tiled\npalette:\n  primary: '#111111'\n"
        "materials:\n  families:\n    masonry:\n"
        "      tile_size: 0.18\n",
        encoding="utf-8",
    )
    style = load_style(path)
    assert style.materials.families["masonry"].tile_size == 0.18


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


def test_resolve_builtin_default(tmp_path: Path) -> None:
    style = resolve_style(tmp_path, "default")
    assert style.name == "default"
    assert style.color("wood_dark") == "#654936"


def test_project_style_overrides_builtin(tmp_path: Path) -> None:
    styles = tmp_path / "styles"
    styles.mkdir()
    (styles / "default.yaml").write_text(
        "name: default\npalette:\n  wood_dark: '#000000'\n",
        encoding="utf-8",
    )
    style = resolve_style(tmp_path, "default")
    assert style.color("wood_dark") == "#000000"


def test_resolve_missing_named_style(tmp_path: Path) -> None:
    with pytest.raises(MasonError) as exc:
        resolve_style(tmp_path, "cafe")
    assert exc.value.code == "style_not_found"
