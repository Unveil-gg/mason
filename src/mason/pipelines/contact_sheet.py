"""Build a 2x2 contact sheet from preview PNGs."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from mason.tools.blender.preview import PREVIEW_VIEWS


def write_contact_sheet(preview_dir: Path) -> Path | None:
    """Compose front/side/top/three_quarter into contact_sheet.png."""
    images = []
    for view in PREVIEW_VIEWS:
        path = preview_dir / f"{view}.png"
        if not path.is_file():
            return None
        images.append(Image.open(path).convert("RGBA"))
    width, height = images[0].size
    sheet = Image.new("RGBA", (width * 2, height * 2), (0, 0, 0, 0))
    for index, img in enumerate(images):
        if img.size != (width, height):
            img = img.resize((width, height))
        col, row = index % 2, index // 2
        sheet.paste(img, (col * width, row * height), img)
    dest = preview_dir / "contact_sheet.png"
    sheet.save(dest)
    for img in images:
        img.close()
    return dest


WORN_SHEET_VIEWS = ("worn_front", "worn", "worn_side")


def write_worn_sheet(preview_dir: Path) -> Path | None:
    """Compose worn front / 3/4 / side into worn_sheet.png."""
    images = []
    for view in WORN_SHEET_VIEWS:
        path = preview_dir / f"{view}.png"
        if not path.is_file():
            return None
        images.append(Image.open(path).convert("RGBA"))
    width, height = images[0].size
    sheet = Image.new("RGBA", (width * 3, height), (0, 0, 0, 0))
    for index, img in enumerate(images):
        if img.size != (width, height):
            img = img.resize((width, height))
        sheet.paste(img, (index * width, 0), img)
    dest = preview_dir / "worn_sheet.png"
    sheet.save(dest)
    for img in images:
        img.close()
    return dest
