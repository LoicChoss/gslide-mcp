"""insert_image_local: put a local PNG/JPEG/GIF on a slide.

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

from ..app import ADDITIVE, mcp
from ..auth import drive_service, remote_mode, slide_service
from ..util import PT_TO_EMU, parse_pres_id, resolve_slide_ids, validate_object_id

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
