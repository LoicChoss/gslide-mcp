"""insert_image_local (a local PNG/JPEG/GIF on a slide) and replace_images (swap pictures in place).

The Slides API only takes images by URL, so the file makes a short trip
through Drive: upload, share read-only to anyone-with-the-link, createImage
from the sharing URL, then delete the Drive file — in a ``finally``, so a
failed createImage never leaves a public file behind. Google copies the
bytes into the presentation at createImage time; the Drive file is not
needed afterwards.
"""

from __future__ import annotations

import base64
import binascii
import os
import tempfile

from googleapiclient.http import MediaFileUpload

from .. import assets
from ..app import ADDITIVE, IDEMPOTENT, mcp
from ..auth import drive_service, remote_mode, slide_service
from ..util import PT_TO_EMU, find_element, parse_pres_id, resolve_slide_ids, validate_object_id
from .semantic import _image_url_is_raster

_MAX_BYTES = 50 * 1024 * 1024  # Slides API limit for image sources

_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def _sniff(path: str) -> str:
    """MIME type from the file's magic bytes; extension is not trusted."""
    if not os.path.isfile(path):
        raise ValueError(f"file not found: {path!r}")
    size = os.path.getsize(path)
    if size > _MAX_BYTES:
        raise ValueError(f"{path!r} is {size / 1e6:.1f} MB; Slides accepts images up to 50 MB")
    with open(path, "rb") as fh:
        head = fh.read(8)
    for magic, mime in _MAGIC:
        if head.startswith(magic):
            return mime
    raise ValueError(
        f"{path!r} is not a PNG, JPEG or GIF (checked the file's magic bytes, not its extension)"
    )


@mcp.tool(annotations=ADDITIVE)
def insert_image_local(
    presentation: str,
    slide: str,
    path: str = "",
    x_pt: float = 0,
    y_pt: float = 0,
    width_pt: float = 100,
    height_pt: float = 100,
    object_id: str | None = None,
    image_base64: str | None = None,
) -> dict:
    """Insert a local image file (PNG, JPEG, GIF; ≤ 50 MB) on a slide.

    Goes through a temporary Drive upload shared to anyone-with-the-link,
    which is deleted again whether or not the insert succeeds. If that
    deletion fails, ``drive_file_id`` and ``warning`` say exactly what was
    left behind and whether it is still public.

    Args:
        slide: 1-based index or objectId.
        path: local file path (not available on the hosted server).
        image_base64: the image bytes, base64-encoded, instead of ``path``;
            the only way to send a file to the hosted server.
        x_pt, y_pt, width_pt, height_pt: geometry in points.
        object_id: optional custom element objectId (5–50 chars).

    Returns: ``{object_id, slide_id, mime_type, drive_file_id, warning}`` —
    the last two are ``None`` on a clean run.

    Example: ``insert_image_local(deck, 2, "~/Downloads/logo.png", 40, 40, 120, 60)``
    """
    validate_object_id(object_id)
    if image_base64:
        tmp = _write_base64(image_base64)
        try:
            return _insert_file(presentation, slide, tmp, x_pt, y_pt, width_pt, height_pt, object_id)
        finally:
            os.unlink(tmp)
    if remote_mode():
        # A path would name a file on the server, not on the caller's machine.
        raise ValueError("on the hosted server, send the image as image_base64 (path is not accepted)")
    if not path:
        raise ValueError("pass path or image_base64")
    return _insert_file(
        presentation, slide, os.path.expanduser(path), x_pt, y_pt, width_pt, height_pt, object_id
    )


def _write_base64(data: str) -> str:
    """Decode base64 image bytes into a temporary file; returns its path."""
    if len(data) > _MAX_BYTES * 4 // 3 + 4:
        raise ValueError("image_base64 is over 50 MB; Slides accepts images up to 50 MB")
    try:
        raw = base64.b64decode(data.split(",", 1)[-1] if data.startswith("data:") else data, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("image_base64 is not valid base64") from None
    fd, tmp = tempfile.mkstemp(prefix="gslides_upload_")
    with os.fdopen(fd, "wb") as fh:
        fh.write(raw)
    return tmp


def _insert_file(
    presentation: str,
    slide: str,
    path: str,
    x_pt: float,
    y_pt: float,
    width_pt: float,
    height_pt: float,
    object_id: str | None,
) -> dict:
    mime = _sniff(path)
    pid = parse_pres_id(presentation)
    svc = slide_service()
    sid = resolve_slide_ids(svc, pid, [slide])[0]
    drv = drive_service()

    file_id: str | None = None
    leftover: str | None = None
    warning: str | None = None
    try:
        media = MediaFileUpload(path, mimetype=mime, resumable=False)
        file_id = drv.files().create(
            body={"name": f"gslides-mcp upload {os.path.basename(path)}", "mimeType": mime},
            media_body=media,
            fields="id",
        ).execute()["id"]
        drv.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}, fields="id"
        ).execute()

        req: dict = {"createImage": {
            "url": f"https://drive.google.com/uc?export=view&id={file_id}",
            "elementProperties": {
                "pageObjectId": sid,
                "size": {
                    "width": {"magnitude": int(width_pt * PT_TO_EMU), "unit": "EMU"},
                    "height": {"magnitude": int(height_pt * PT_TO_EMU), "unit": "EMU"},
                },
                "transform": {
                    "scaleX": 1, "scaleY": 1,
                    "translateX": int(x_pt * PT_TO_EMU),
                    "translateY": int(y_pt * PT_TO_EMU),
                    "unit": "EMU",
                },
            },
        }}
        if object_id:
            req["createImage"]["objectId"] = object_id
        resp = svc.presentations().batchUpdate(
            presentationId=pid, body={"requests": [req]}
        ).execute()
        new_id = resp["replies"][0]["createImage"]["objectId"]
    finally:
        if file_id:
            try:
                drv.files().delete(fileId=file_id).execute()
            except Exception as exc:
                leftover = file_id
                try:
                    drv.permissions().delete(fileId=file_id, permissionId="anyoneWithLink").execute()
                    warning = (
                        f"Drive file {file_id} could not be deleted ({exc}); its sharing "
                        "link was revoked so it is no longer public, but it remains in "
                        "your Drive — delete it by hand."
                    )
                except Exception:
                    warning = (
                        f"Drive file {file_id} could not be deleted ({exc}) and is still "
                        "publicly accessible to anyone with the link. Delete it or revoke "
                        "its sharing by hand."
                    )
    return {
        "object_id": new_id, "slide_id": sid, "mime_type": mime,
        "drive_file_id": leftover, "warning": warning,
    }


# --- replace_images ----------------------------------------------------------------------

_METHODS = {"inside": "CENTER_INSIDE", "crop": "CENTER_CROP"}
_MAX_URL = 2048  # Slides API limit for an image URL
_DEFAULT_THEME = os.environ.get("GSLIDES_MCP_THEME", "periscope")


def _box_pt(el: dict) -> tuple[tuple[float, float, float, float], bool]:
    """Displayed (x, y, w, h) of an element in points, in its own transform space, and whether it is sheared."""
    t = el.get("transform", {})
    size = el.get("size", {})
    w = size.get("width", {}).get("magnitude", 0) * t.get("scaleX", 1) / PT_TO_EMU
    h = size.get("height", {}).get("magnitude", 0) * t.get("scaleY", 1) / PT_TO_EMU
    x, y = t.get("translateX", 0) / PT_TO_EMU, t.get("translateY", 0) / PT_TO_EMU
    return (x, y, w, h), bool(t.get("shearX") or t.get("shearY"))


def _inside(box, frame, tol: float = 0.5) -> bool:
    x, y, w, h = box
    fx, fy, fw, fh = frame
    return x >= fx - tol and y >= fy - tol and x + w <= fx + fw + tol and y + h <= fy + fh + tol


def _hex6(theme, value) -> str:
    c = theme.color(value)
    return "{:02x}{:02x}{:02x}".format(*(round(c[k] * 255) for k in ("red", "green", "blue")))


def _drive_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=view&id={file_id}"


@mcp.tool(annotations=IDEMPOTENT)
def replace_images(presentation: str, images: list[dict]) -> dict:
    """Swap the picture of existing image elements — one batch, each keeps its id, frame and z-order.

    For visuals that change from one month to the next (top ads, captures,
    logos) in a deck that stays: the element is the same object before and
    after, so bindings and layout survive. Each image has a frame — the
    box it must fit — recorded in its alt text (``slot:x,y,w,h``) by image
    slots and, for any other image, taken from its current box the first
    time. The frame is put back before every swap, because Google's
    CENTER_INSIDE shrinks the element to the picture it receives, and
    written again after it, because replaceImage clears the alt text.

    Args:
        images: ``[{element, source, fit?}]``.
            ``source``: an image URL (http/https, 2 kB max, must serve PNG,
            JPEG or GIF: checked before writing), a name of the assets
            folder (``list_assets``) or ``drive:<file id>``; empty or null
            puts the empty-slot placeholder back.
            ``fit``: ``inside`` (default: the whole picture, centred, the
            frame's edges may stay empty) or ``crop`` (fills the frame,
            the picture is cut to its aspect).

    Everything is checked before the batch: an element that is not an
    image (a shape, a table: insert it again as an image slot), an element
    listed twice, an unknown asset, a URL that does not serve a picture.
    A rotated or sheared image is swapped without restoring its frame
    (``note``).

    Returns: ``{replaced: [{element, source, fit, frame, frame_recorded,
    frame_restored, note?}]}``.

    Example::

        replace_images(deck, [
            {"element": "yt_top_slot_1", "source": "https://…/creative.jpg"},
            {"element": "yt_top_slot_2", "source": "drive:1AbC…", "fit": "crop"},
            {"element": "yt_top_slot_3", "source": ""},
        ])
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    reqs, out = plan_replace_images(pres, images)
    svc.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute()
    return out


def plan_replace_images(pres: dict, images: list[dict]) -> tuple[list[dict], dict]:
    """``replace_images``'s requests and result on a presentation already read; nothing is sent.

    Every image is checked (element, source, URL probe) before any request
    is built. ``sync_deck`` plans its visuals through here.
    """
    from .. import themes
    from ..draw import parse_slot_frame, slot_frame_text

    if not images:
        raise ValueError("images is empty: give [{element, source, fit?}]")
    theme = None

    planned = []
    seen: set[str] = set()
    for n, item in enumerate(images, 1):
        oid = item.get("element")
        if not oid:
            raise ValueError(f"image #{n} needs 'element' (and 'source'): {item!r}")
        if oid in seen:
            raise ValueError(f"image #{n}: {oid!r} is listed twice")
        seen.add(oid)
        el, _slide = find_element(pres, oid)
        if el is None:
            raise ValueError(f"image #{n}: element not found: {oid!r}")
        if "image" not in el:
            raise ValueError(f"image #{n}: {oid!r} is not an image (a shape or a table): a picture can only be "
                             "swapped into an image; insert an image slot there instead")
        fit = item.get("fit") or "inside"
        if fit not in _METHODS:
            raise ValueError(f"image #{n}: fit must be 'inside' or 'crop', got {fit!r}")
        box, sheared = _box_pt(el)
        stored = parse_slot_frame(el.get("description"))
        frame = stored if stored and _inside(box, stored) else box
        source = item.get("source")
        if not source:
            if theme is None:
                theme = themes.load(_DEFAULT_THEME)
            ref = assets.slot_ref(frame[2], frame[3], _hex6(theme, "surface"), _hex6(theme, "divider"))
            url, method, shown = _drive_url(assets.ensure_asset(ref)), "CENTER_CROP", "slot"
        elif str(source).startswith(("http://", "https://")):
            if len(source) > _MAX_URL:
                raise ValueError(f"image #{n} ({oid}): the URL is {len(source)} characters, over the 2 kB Slides accepts")
            ok, ctype = _image_url_is_raster(source)
            if not ok:
                raise ValueError(f"image #{n} ({oid}): {source} does not serve a PNG, JPEG or GIF ({ctype}); "
                                 "platform links expire: put the visual in Drive and pass drive:<id>")
            url, method, shown = source, _METHODS[fit], source
        else:
            try:
                url = _drive_url(assets.ensure_asset(str(source)))
            except ValueError as exc:
                raise ValueError(f"image #{n} ({oid}): {exc}") from None
            method, shown = _METHODS[fit], str(source)
        planned.append((oid, el, box, sheared, stored, frame, url, method, shown))

    reqs: list[dict] = []
    report = []
    for oid, el, box, sheared, stored, frame, url, method, shown in planned:
        entry = {"element": oid, "source": shown, "fit": "crop" if method == "CENTER_CROP" else "inside",
                 "frame": [round(v, 1) for v in frame], "frame_recorded": False, "frame_restored": False}
        entry["frame_recorded"] = stored != frame
        if sheared:
            entry["note"] = "rotated or sheared image: swapped without restoring its frame"
        elif any(abs(a - b) > 0.05 for a, b in zip(box, frame)):
            size = el["size"]
            reqs.append({"updatePageElementTransform": {"objectId": oid, "applyMode": "ABSOLUTE", "transform": {
                "scaleX": frame[2] * PT_TO_EMU / size["width"]["magnitude"],
                "scaleY": frame[3] * PT_TO_EMU / size["height"]["magnitude"],
                "translateX": frame[0] * PT_TO_EMU, "translateY": frame[1] * PT_TO_EMU, "unit": "EMU",
            }}})
            entry["frame_restored"] = True
        reqs.append({"replaceImage": {"imageObjectId": oid, "url": url, "imageReplaceMethod": method}})
        # replaceImage clears the alt text (verified live): the frame is written again after it
        reqs.append({"updatePageElementAltText": {"objectId": oid, "description": slot_frame_text(*frame)}})
        report.append(entry)
    return reqs, {"replaced": report}
