"""Assets: named images in a shared Drive folder, uploaded once, tinted on demand.

``createImage`` only takes URLs, so pictos and logos live in one Drive
folder (``GSLIDES_MCP_ASSETS_FOLDER``, the *Assets folder* field of the
Desktop bundle). ``ensure_asset("bolt")`` finds ``bolt.png`` there;
``ensure_asset("/path/logo.png")`` uploads it there the first time;
``tint="#002B3C"`` produces and stores a recolored variant
(``bolt__002b3c.png``, transparency kept) — that is how one picto serves
every theme. ``slot:<w>x<h>:<fill>:<line>`` refs (``slot_ref``) are empty-slot
placeholders generated at the box's aspect ratio, so an image slot keeps its
frame whatever picture replaces it later. Resolved ids are cached in
``~/.gslides-mcp/assets.json``.
"""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from .auth import drive_service, remote_mode

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


_SLOT = re.compile(r"^slot:(\d{1,4})x(\d{1,4}):([0-9a-f]{6}):([0-9a-f]{6})$")
SLOT_PX_PER_PT = 4
SLOT_MAX_PX = 1600


def slot_ref(w_pt: float, h_pt: float, fill_hex: str, line_hex: str) -> str:
    """Asset ref of an empty-slot placeholder with the box's aspect (4 px per pt, long side ≤ 1600 px)."""
    w, h = max(float(w_pt), 1.0) * SLOT_PX_PER_PT, max(float(h_pt), 1.0) * SLOT_PX_PER_PT
    k = min(1.0, SLOT_MAX_PX / max(w, h))
    return f"slot:{max(8, round(w * k))}x{max(8, round(h * k))}:{_norm_hex(fill_hex)}:{_norm_hex(line_hex)}"


def _slot_png(w: int, h: int, fill: str, line: str, dst: Path) -> Path:
    """Flat fill with a dashed 1 pt border (3 pt dashes, 2 pt gaps at 4 px per pt)."""
    from PIL import Image, ImageDraw

    rgb = lambda hx: tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))  # noqa: E731
    im = Image.new("RGBA", (w, h), rgb(fill) + (255,))
    d = ImageDraw.Draw(im)
    lw, dash, step = 4, 12, 20
    for x in range(0, w, step):
        d.rectangle([x, 0, min(x + dash, w) - 1, lw - 1], fill=rgb(line))
        d.rectangle([x, h - lw, min(x + dash, w) - 1, h - 1], fill=rgb(line))
    for y in range(0, h, step):
        d.rectangle([0, y, lw - 1, min(y + dash, h) - 1], fill=rgb(line))
        d.rectangle([w - lw, y, w - 1, min(y + dash, h) - 1], fill=rgb(line))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def _slot_file(w: str, h: str, fill: str, line: str) -> str:
    """Drive id of the slot placeholder, generated and uploaded to the assets folder the first time."""
    folder = folder_id()
    target = f"slot-{w}x{h}-{fill}-{line}.png"
    key = f"{folder}/{target}"
    cache = _cache_read()
    if key in cache:
        return cache[key]
    drv = drive_service()
    fid = _list_folder(drv, folder).get(target)
    if fid is None:
        tmp = _slot_png(int(w), int(h), fill, line, CACHE.parent / "slots" / target)
        fid = _upload(drv, folder, str(tmp), target)
    cache[key] = fid
    _cache_write(cache)
    return fid


def ensure_asset(ref: str, tint: str | None = None) -> str:
    """Drive file id for an asset name, a local path, a ``drive:<id>`` or ``slot:…`` ref, optionally tinted."""
    slot = _SLOT.match(ref)
    if slot:
        return _slot_file(*slot.groups())
    if ref.startswith("drive:"):
        fid = ref[6:].strip()
        if not fid:
            raise ValueError("empty drive: asset ref")
        if not tint:
            return fid
        return _tinted_copy(fid, _norm_hex(tint))
    folder = folder_id()
    # On the hosted server a path names a file on the server, not on the
    # caller's machine: never read one, or any user could publish server files.
    is_path = not remote_mode() and os.path.isfile(ref)
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
                    f"{', '.join(sorted(listing)) or 'none'}); {_upload_hint()}"
                )
            tmp = _tint(src, hex6, CACHE.parent / "tinted" / target)
            fid = _upload(drv, folder, str(tmp), target)
        elif is_path:
            fid = _upload(drv, folder, ref, target)
        else:
            raise ValueError(
                f"asset {ref!r} not found in the Drive assets folder (files: "
                f"{', '.join(sorted(listing)) or 'none'}); {_upload_hint()}"
            )
    cache[key] = fid
    _cache_write(cache)
    return fid


def _upload_hint() -> str:
    if remote_mode():
        return "add the file to the Drive assets folder, or pass drive:<file id>"
    return "pass a local path to upload it"


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
    slot = _SLOT.match(ref)
    if slot:
        return int(slot.group(1)), int(slot.group(2))
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
