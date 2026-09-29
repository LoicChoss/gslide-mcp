"""Assets: named images in a shared Drive folder, uploaded once, tinted on demand.

``createImage`` only takes URLs, so pictos and logos live in one Drive
folder (``GSLIDES_MCP_ASSETS_FOLDER``, the *Assets folder* field of the
Desktop bundle). ``ensure_asset("bolt")`` finds ``bolt.png`` there;
``ensure_asset("/path/logo.png")`` uploads it there the first time;
``tint="#002B3C"`` produces and stores a recolored variant
(``bolt__002b3c.png``, transparency kept) — that is how one picto serves
every theme. Resolved ids are cached in ``~/.gslides-mcp/assets.json``.
"""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from .auth import drive_service

ENV_FOLDER = "GSLIDES_MCP_ASSETS_FOLDER"
CACHE = Path.home() / ".gslides-mcp" / "assets.json"
_EXTS = (".png", ".jpg", ".jpeg", ".gif")
_FOLDER_URL = re.compile(r"/folders/([A-Za-z0-9_-]+)")


# The team's shared folder of pictos and logos; GSLIDES_MCP_ASSETS_FOLDER overrides it.
DEFAULT_FOLDER = "1a47ILzByssFMQHy9-UH0ELXpOwFISu5X"


def folder_id() -> str:
    raw = os.environ.get(ENV_FOLDER, "").strip() or DEFAULT_FOLDER
    m = _FOLDER_URL.search(raw)
    return m.group(1) if m else raw


def _cache_read() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_write(data: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _list_folder(drv, folder: str) -> dict[str, str]:
    """name → file id for every non-trashed file in the folder."""
    out: dict[str, str] = {}
    token = None
    while True:
        resp = drv.files().list(
            q=f"'{folder}' in parents and trashed = false",
            fields="nextPageToken,files(id,name,mimeType)", pageSize=1000,
            supportsAllDrives=True, includeItemsFromAllDrives=True, pageToken=token,
        ).execute()
        for f in resp.get("files", []):
            out.setdefault(f["name"], f["id"])
        token = resp.get("nextPageToken")
        if not token:
            return out


def _upload(drv, folder: str, path: str, name: str) -> str:
    fid = drv.files().create(
        body={"name": name, "parents": [folder]},
        media_body=MediaFileUpload(path, resumable=False),
        fields="id", supportsAllDrives=True,
    ).execute()["id"]
    try:
        drv.permissions().create(
            fileId=fid, body={"type": "anyone", "role": "reader"}, fields="id", supportsAllDrives=True,
        ).execute()
    except Exception as exc:
        raise RuntimeError(
            f"uploaded {name} to the assets folder but could not share it publicly ({exc}); "
            "Slides can only load images from URLs it can fetch — allow link sharing on that shared drive"
        ) from None
    return fid


def _norm_hex(color: str) -> str:
    c = color.strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", c):
        raise ValueError(f"tint must be a #RRGGBB color, got {color!r}")
    return c.lower()


def tinted_name(name: str, hex6: str) -> str:
    return f"{Path(name).stem}__{hex6}.png"


def _tint(src_bytes: bytes, hex6: str, dst: Path) -> Path:
    """Recolor every pixel to the tint, keeping the alpha channel."""
    from PIL import Image

    im = Image.open(io.BytesIO(src_bytes)).convert("RGBA")
    rgb = tuple(int(hex6[i:i + 2], 16) for i in (0, 2, 4))
    solid = Image.new("RGBA", im.size, rgb + (255,))
    solid.putalpha(im.getchannel("A"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    solid.save(dst, "PNG")
    return dst


def ensure_asset(ref: str, tint: str | None = None) -> str:
    """Drive file id for an asset name, a local path or a ``drive:<id>`` ref, optionally tinted."""
    if ref.startswith("drive:"):
        fid = ref[6:].strip()
        if not fid:
            raise ValueError("empty drive: asset ref")
        if not tint:
            return fid
        return _tinted_copy(fid, _norm_hex(tint))
    folder = folder_id()
    is_path = os.path.isfile(ref)
    base = os.path.basename(ref) if is_path else ref
    if os.path.splitext(base)[1].lower() not in _EXTS:
        base += ".png"
    hex6 = _norm_hex(tint) if tint else None
    target = tinted_name(base, hex6) if hex6 else base
    key = f"{folder}/{target}"
    cache = _cache_read()
    if key in cache:
        return cache[key]

    drv = drive_service()
    listing = _list_folder(drv, folder)
    fid = listing.get(target)
    if fid is None:
        if hex6:
            if is_path:
                src = Path(ref).read_bytes()
            elif base in listing:
                src = drv.files().get_media(fileId=listing[base], supportsAllDrives=True).execute()
            else:
                raise ValueError(
                    f"asset {ref!r} not found in the Drive assets folder (files: "
                    f"{', '.join(sorted(listing)) or 'none'}); pass a local path to upload it"
                )
            tmp = _tint(src, hex6, CACHE.parent / "tinted" / target)
            fid = _upload(drv, folder, str(tmp), target)
        elif is_path:
            fid = _upload(drv, folder, ref, target)
        else:
            raise ValueError(
                f"asset {ref!r} not found in the Drive assets folder (files: "
                f"{', '.join(sorted(listing)) or 'none'}); pass a local path to upload it"
            )
    cache[key] = fid
    _cache_write(cache)
    return fid


def _tinted_copy(fid: str, hex6: str) -> str:
    """Tinted variant of a Drive file (harvested image), stored in the assets folder."""
    folder = folder_id()
    target = f"drive-{fid}__{hex6}.png"
    key = f"{folder}/{target}"
    cache = _cache_read()
    if key in cache:
        return cache[key]
    drv = drive_service()
    listing = _list_folder(drv, folder)
    out = listing.get(target)
    if out is None:
        src = drv.files().get_media(fileId=fid, supportsAllDrives=True).execute()
        tmp = _tint(src, hex6, CACHE.parent / "tinted" / target)
        out = _upload(drv, folder, str(tmp), target)
    cache[key] = out
    _cache_write(cache)
    return out


def _measure(data: bytes) -> tuple[int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as im:
        return im.size


def asset_size(ref: str, tint: str | None = None, fid: str | None = None) -> tuple[int, int]:
    """(width, height) in pixels of an asset, cached next to its id."""
    fid = fid or ensure_asset(ref, tint)
    cache = _cache_read()
    sizes = cache.setdefault("_sizes", {})
    if fid in sizes:
        return tuple(sizes[fid])
    if os.path.isfile(ref) and not tint:
        size = _measure(Path(ref).read_bytes())
    else:
        size = _measure(drive_service().files().get_media(fileId=fid, supportsAllDrives=True).execute())
    sizes[fid] = list(size)
    _cache_write(cache)
    return size


def list_assets() -> list[str]:
    """Names in the assets folder (for the catalogue / error messages)."""
    return sorted(_list_folder(drive_service(), folder_id()))
