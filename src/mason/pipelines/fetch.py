"""Download a reference image into a job-scoped cache."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from mason.errors import MasonError

_MAX_BYTES = 20 * 1024 * 1024
_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/tiff": ".tif",
    "image/tif": ".tif",
}
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}


def fetch_reference(url: str, dest_dir: Path) -> Path:
    """Download an http(s) image into dest_dir. Writes a .source.json
    sidecar with source_url and fetched_at. Returns the image path.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MasonError(
            "ingest --fetch only accepts http(s) URLs.",
            code="fetch_bad_url",
            context={"url": url},
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "mason-ingest/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:
            ctype = ""
            if hasattr(resp, "headers") and resp.headers:
                ctype = resp.headers.get_content_type() or ""
            data = resp.read(_MAX_BYTES + 1)
    except MasonError:
        raise
    except Exception as exc:
        raise MasonError(
            f"Could not fetch reference: {exc}",
            code="fetch_failed",
            hint="Check the URL and try again.",
            context={"url": url},
        ) from exc
    if len(data) > _MAX_BYTES:
        raise MasonError(
            "Fetched image is larger than 20MB.",
            code="fetch_too_large",
            context={"url": url},
        )
    if not _looks_like_image(parsed.path, ctype):
        raise MasonError(
            "Fetched URL is not an image.",
            code="fetch_not_image",
            context={"url": url, "content_type": ctype},
        )
    ext = _extension(parsed.path, ctype)
    stem = Path(parsed.path).stem or "reference"
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    dest = dest_dir / f"{stem}{ext}"
    dest.write_bytes(data)
    sidecar = dest_dir / f"{stem}.source.json"
    sidecar.write_text(
        json.dumps({
            "source_url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content_type": ctype or None,
            "bytes": len(data),
        }, indent=2),
        encoding="utf-8",
    )
    return dest


def _looks_like_image(path: str, ctype: str) -> bool:
    if ctype.startswith("image/"):
        return True
    return Path(path).suffix.lower() in _ALLOWED_EXT


def _extension(path: str, ctype: str) -> str:
    mapped = _EXT.get(ctype.lower())
    if mapped:
        return mapped
    suffix = Path(path).suffix.lower()
    if suffix in _ALLOWED_EXT:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"
