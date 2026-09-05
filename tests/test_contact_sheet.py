"""Contact sheet composition."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from mason.pipelines.contact_sheet import write_contact_sheet


def test_contact_sheet_2x2(tmp_path: Path) -> None:
    for name in ("front", "side", "top", "three_quarter"):
        Image.new("RGBA", (32, 32), (10, 20, 30, 255)).save(
            tmp_path / f"{name}.png",
        )
    dest = write_contact_sheet(tmp_path)
    assert dest is not None and dest.is_file()
    with Image.open(dest) as img:
        assert img.size == (64, 64)
