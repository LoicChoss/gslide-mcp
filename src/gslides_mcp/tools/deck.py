"""Deck-level tools: create, list, inspect, find, export, raw batch escape."""

from __future__ import annotations

from googleapiclient.errors import HttpError

from ..app import ADDITIVE, DESTRUCTIVE, IDEMPOTENT, READ_ONLY, mcp
from ..auth import remote_mode, slide_service, drive_service
from ..util import parse_drive_id, parse_pres_id, emu_to_pt

_SLIDES_MIME = "application/vnd.google-apps.presentation"
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _folder_name(drv, folder_id: str | None) -> str | None:
    """The folder's title, or None when it cannot be read (not worth failing a copy over)."""
    if not folder_id:
        return None
    try:
        return drv.files().get(fileId=folder_id, fields="name", supportsAllDrives=True).execute().get("name")
    except HttpError:
        return None


def _check_folder(drv, folder_id: str) -> str | None:
    """Refuse early, with a clear message, a folder id that is not a folder."""
    try:
        meta = drv.files().get(fileId=folder_id, fields="id,name,mimeType", supportsAllDrives=True).execute()
    except HttpError as exc:
        raise ValueError(f"folder {folder_id!r} not found or not shared with you (HTTP {exc.resp.status})") from exc
    if meta.get("mimeType") != _FOLDER_MIME:
        raise ValueError(f"{folder_id!r} is not a folder ({meta.get('mimeType')}): pass a Drive folder id or URL")
    return meta.get("name")


@mcp.tool(annotations=ADDITIVE)
def create_presentation(title: str, folder: str | None = None) -> dict:
    """Create a new blank Google Slides presentation.

    Not for a PowerPoint (.pptx) the user asked for: that file is made with the
    usual PowerPoint tooling, not in Google Slides.

    Args:
        folder: Drive folder id or URL (``drive.google.com/drive/folders/<id>``)
            to create it in. Default: the root of the user's My Drive.

    Returns:
        {presentation_id, url, folder_id, folder_name}
    """
    if not folder:
        pres = slide_service().presentations().create(body={"title": title}).execute()
        pid = pres["presentationId"]
        return {
            "presentation_id": pid,
            "url": f"https://docs.google.com/presentation/d/{pid}/edit",
            "folder_id": None, "folder_name": None,
        }
    drv = drive_service()
    folder_id = parse_drive_id(folder)
    folder_name = _check_folder(drv, folder_id)
    out = drv.files().create(
        body={"name": title, "mimeType": _SLIDES_MIME, "parents": [folder_id]},
        fields="id", supportsAllDrives=True,
    ).execute()
    pid = out["id"]
    return {
        "presentation_id": pid,
        "url": f"https://docs.google.com/presentation/d/{pid}/edit",
        "folder_id": folder_id, "folder_name": folder_name,
    }


@mcp.tool(annotations=ADDITIVE)
def clone_deck(src: str, name: str, parent_folder_id: str | None = None) -> dict:
    """Clone an existing Slides deck via Drive ``files.copy``, next to the source by default.

    The canonical way to start from a known-good source — copy a deck and edit
    in place. Always passes ``supportsAllDrives=True`` so source decks living
    in Shared Drives copy cleanly. Without that flag the API returns a
    misleading 404 even when the caller has full Drive scope.

    Where the copy lands: ``parent_folder_id`` when given; otherwise the
    source deck's own folder. When that folder cannot take the copy (the
    source is shared with you read-only, or sits in a folder you cannot
    see), the copy goes to the root of My Drive and ``folder_note`` says so:
    tell the user, and offer ``move_to_folder``.

    Args:
        src: source presentation ID or full Slides URL.
        name: title for the new copy.
        parent_folder_id: Drive folder id or URL to place the copy in.

    Returns:
        {presentation_id, url, folder_id, folder_name, placed: "given" |
        "source_folder" | "my_drive", folder_note?}
    """
    src_id = parse_pres_id(src)
    drv = drive_service()
    body: dict = {"name": name}
    placed = "my_drive"
    if parent_folder_id:
        body["parents"] = [parse_drive_id(parent_folder_id)]
        placed = "given"
    else:
        try:
            parents = drv.files().get(fileId=src_id, fields="parents", supportsAllDrives=True).execute().get("parents") or []
        except HttpError:
            parents = []  # the copy below reports a missing source properly
        if parents:
            body["parents"] = parents[:1]
            placed = "source_folder"
    note = None
    try:
        out = drv.files().copy(fileId=src_id, body=body, fields="id,parents", supportsAllDrives=True).execute()
    except HttpError as exc:
        if placed != "source_folder" or exc.resp.status not in (403, 404):
            raise
        # the source folder refuses the copy (read-only share): fall back to My Drive
        body.pop("parents")
        out = drv.files().copy(fileId=src_id, body=body, fields="id,parents", supportsAllDrives=True).execute()
        placed = "my_drive"
        note = ("the source deck's folder does not accept new files from you (HTTP "
                f"{exc.resp.status}): the copy is in My Drive; move it with move_to_folder")
    if placed == "my_drive" and note is None and not parent_folder_id:
        note = "the source deck's folder is not visible to you: the copy is in My Drive; move it with move_to_folder"
    pid = out["id"]
    folder_id = (out.get("parents") or body.get("parents") or [None])[0]
    result = {
        "presentation_id": pid,
        "url": f"https://docs.google.com/presentation/d/{pid}/edit",
        "folder_id": folder_id,
        "folder_name": _folder_name(drv, folder_id),
        "placed": placed,
    }
    if note:
        result["folder_note"] = note
    return result


@mcp.tool(annotations=IDEMPOTENT)
def move_to_folder(file: str, folder: str) -> dict:
    """Move a Drive file (deck, spreadsheet, doc…) into another folder.

    The file leaves its current folder(s) and lands in ``folder`` only: same
    as dragging it in Drive, links and sharing unchanged. Works on any file
    the user can edit, so a spreadsheet created for a deck's charts can be
    put next to the deck (``folder`` = the deck's ``folder_id`` from
    ``clone_deck`` / ``create_presentation``). Calling it again is harmless.

    Args:
        file: file id or URL (Slides, Sheets, Docs or Drive link).
        folder: target Drive folder id or URL (``drive.google.com/drive/folders/<id>``).

    Returns: ``{file_id, name, folder_id, folder_name, previous_folders}``.
    """
    drv = drive_service()
    file_id = parse_drive_id(file)
    folder_id = parse_drive_id(folder)
    folder_name = _check_folder(drv, folder_id)
    try:
        meta = drv.files().get(fileId=file_id, fields="id,name,parents", supportsAllDrives=True).execute()
    except HttpError as exc:
        raise ValueError(f"file {file_id!r} not found or not shared with you (HTTP {exc.resp.status})") from exc
    previous = meta.get("parents") or []
    remove = ",".join(p for p in previous if p != folder_id)
    if folder_id not in previous or remove:
        kwargs: dict = {"fileId": file_id, "fields": "id,parents", "supportsAllDrives": True, "body": {}}
        if folder_id not in previous:
            kwargs["addParents"] = folder_id
        if remove:
            kwargs["removeParents"] = remove
        drv.files().update(**kwargs).execute()
    return {"file_id": file_id, "name": meta.get("name"), "folder_id": folder_id,
            "folder_name": folder_name, "previous_folders": previous}


@mcp.tool(annotations=READ_ONLY)
def list_slides(presentation: str, range_start: int | None = None, range_end: int | None = None) -> list[dict]:
    """One-line summary of every slide. Optionally restrict to a 1-based inclusive range.

    Returns list of {index, object_id, summary[, hidden]} where summary is
    concatenated text. ``hidden: true`` marks a slide skipped in
    presentation mode (the Slides "Skip slide" toggle): it is still in the
    deck, still counted in indexes, but not shown to the audience — often a
    stale or discarded version. Treat its content as unreliable unless the
    user says otherwise; ``set_slide_hidden`` toggles the flag.
    """
    pid = parse_pres_id(presentation)
    pres = slide_service().presentations().get(presentationId=pid).execute()
    out = []
    for i, slide in enumerate(pres["slides"], 1):
        if range_start is not None and i < range_start:
            continue
        if range_end is not None and i > range_end:
            continue
        chunks: list[str] = []
        for el in slide.get("pageElements", []):
            for te in el.get("shape", {}).get("text", {}).get("textElements", []):
                run = te.get("textRun", {}).get("content", "").strip()
                if run:
                    chunks.append(run)
        row = {"index": i, "object_id": slide["objectId"], "summary": " | ".join(chunks)[:200]}
        if slide.get("slideProperties", {}).get("isSkipped"):
            row["hidden"] = True
        out.append(row)
    return out


def _resolve_slide(pres: dict, slide: str) -> dict:
    """Look up a slide by 1-based index or objectId. Raises ValueError if missing."""
    by_idx = {str(i): s for i, s in enumerate(pres["slides"], 1)}
    by_id = {s["objectId"]: s for s in pres["slides"]}
    sl = by_idx.get(str(slide).strip()) or by_id.get(str(slide).strip())
    if sl is None:
        raise ValueError(f"slide not found: {slide!r}")
    return sl


def _summarize_element(el: dict, parent_tx: float = 0, parent_ty: float = 0,
                       parent_sx: float = 1, parent_sy: float = 1,
                       parent_id: str | None = None) -> tuple[dict, float, float, float, float]:
    """Flatten a Slides API pageElement into the inspect/find output shape.

    Composes parent transform with own transform so reported geometry is the
    final on-canvas position (group children otherwise report local coords).
    """
    t = el.get("transform", {})
    s = el.get("size", {})
    sx = t.get("scaleX", 1) * parent_sx
    sy = t.get("scaleY", 1) * parent_sy
    tx = parent_tx + t.get("translateX", 0) * parent_sx
    ty = parent_ty + t.get("translateY", 0) * parent_sy
    w_emu = s.get("width", {}).get("magnitude", 0) * sx
    h_emu = s.get("height", {}).get("magnitude", 0) * sy
    text_chunks: list[str] = []
    for te in el.get("shape", {}).get("text", {}).get("textElements", []):
        r = te.get("textRun", {}).get("content", "")
        if r:
            text_chunks.append(r)
    kind = "shape"
    if "image" in el:
        kind = "image"
    elif "table" in el:
        kind = "table"
    elif "sheetsChart" in el:
        kind = "chart"
    elif "elementGroup" in el:
        kind = "group"
    elif "shape" in el:
        kind = el["shape"].get("shapeType", "shape")
    alt_title = el.get("title", "") or el.get("description", "")
    out = {
        "id": el["objectId"],
        "type": kind,
        "x": round(emu_to_pt(tx), 1),
        "y": round(emu_to_pt(ty), 1),
        "w": round(emu_to_pt(w_emu), 1),
        "h": round(emu_to_pt(h_emu), 1),
        "text": "".join(text_chunks).strip()[:300],
    }
    if alt_title:
        out["alt_title"] = alt_title
    if parent_id:
        out["parent_id"] = parent_id
    if kind == "image":
        img = el["image"]
        if img.get("contentUrl"):
            out["image_url"] = img["contentUrl"]  # temporary (~30 min): harvest_deck_assets stores a copy
        if img.get("sourceUrl"):
            out["source_url"] = img["sourceUrl"]
    elif kind == "table":
        out["rows"] = _table_cells(el["table"])
    else:
        ph = el.get("shape", {}).get("placeholder", {}).get("type")
        if ph:
            out["placeholder"] = ph
        paras = _paragraphs(el.get("shape", {}).get("text", {}).get("textElements", []))
        if len(paras) > 1 or any(p["bullet"] for p in paras):
            out["paragraphs"] = paras
    return out, tx, ty, sx, sy


def _table_cells(table: dict, max_rows: int = 40, max_cols: int = 12) -> list[list[str]]:
    """Cell texts of a table element, row by row (for reuse in a `table` component)."""
    rows: list[list[str]] = []
    for tr in table.get("tableRows", [])[:max_rows]:
        cells: list[str] = []
        for tc in tr.get("tableCells", [])[:max_cols]:
            chunks = [te.get("textRun", {}).get("content", "") for te in tc.get("text", {}).get("textElements", [])]
            cells.append("".join(chunks).strip())
        rows.append(cells)
    return rows


def _paragraphs(text_elements: list) -> list[dict]:
    """[{text, level, bullet}] per paragraph of a shape's text, markdown-ready."""
    out: list[dict] = []
    current: dict | None = None
    for te in text_elements:
        pm = te.get("paragraphMarker")
        if pm is not None:
            current = {"text": "", "level": pm.get("bullet", {}).get("nestingLevel", 0), "bullet": "bullet" in pm}
            out.append(current)
            continue
        run = te.get("textRun", {}).get("content", "")
        if run and current is not None:
            current["text"] += run
    cleaned = []
    for p in out:
        p["text"] = p["text"].strip()[:300]
        if p["text"]:
            cleaned.append(p)
    return cleaned


def _walk_elements(elements: list, recursive: bool, out: list,
                   parent_tx: float = 0, parent_ty: float = 0,
                   parent_sx: float = 1, parent_sy: float = 1,
                   parent_id: str | None = None) -> None:
    for el in elements:
        summary, tx, ty, sx, sy = _summarize_element(
            el, parent_tx, parent_ty, parent_sx, parent_sy, parent_id,
        )
        out.append(summary)
        if recursive:
            children = el.get("elementGroup", {}).get("children", [])
            if children:
                _walk_elements(children, recursive, out, tx, ty, sx, sy, el["objectId"])


@mcp.tool(annotations=READ_ONLY)
def inspect_slide(presentation: str, slide: str, recursive: bool = False) -> dict:
    """Dump every element on a slide: id, type, geometry (in pt), text content.

    Args:
        slide: 1-based index or slide objectId.
        recursive: when True, drill into groups. Group children gain a
            ``parent_id`` field; their reported x/y/w/h are composed with the
            parent's transform (so positions are final on-canvas coords, not
            local). Use this to address group-nested elements directly via
            write_text_markdown / set_text.

    Returns: ``{slide_id, elements: [{id, type, x, y, w, h, text, alt_title?, parent_id?,
    placeholder?, paragraphs?: [{text, level, bullet}], rows? (table cells),
    image_url? (temporary), source_url?}]}`` — enough to rebuild the content
    with components elsewhere; ``harvest_deck_assets`` stores the images first.
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    sl = _resolve_slide(pres, slide)

    elements: list = []
    _walk_elements(sl.get("pageElements", []), recursive, elements)
    out = {"slide_id": sl["objectId"], "elements": elements}
    if sl.get("slideProperties", {}).get("isSkipped"):
        out["hidden"] = True  # skipped in presentation mode: content often stale
    return out


@mcp.tool(annotations=READ_ONLY)
def find_elements(
    presentation: str,
    slide: str | None = None,
    type: str | None = None,
    alt_title: str | None = None,
    contains: str | None = None,
    recursive: bool = True,
) -> dict:
    """Semantic element search across the deck or a single slide.

    Replaces the inspect-and-eyeball pattern when you know what you want by
    name / type / text but not by objectId.

    Args:
        slide: optional slide ref (1-based index or objectId). None = whole deck.
        type: filter by element type — 'image', 'table', 'group', 'TEXT_BOX',
            'RECTANGLE', 'ROUND_RECTANGLE', 'ELLIPSE', etc. (case-insensitive)
        alt_title: substring match on the page-element alt-title (set via
            ``alt_title=`` on create_shape). Case-insensitive.
        contains: substring match on the element's text content. Case-insensitive.
        recursive: drill into groups (default True). Group children reported
            with ``parent_id``.

    Returns: ``{matches: [{slide_id, slide_index, ...element fields...}]}``.
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()

    if slide is not None:
        target_slides = [(_resolve_slide_index(pres, slide), _resolve_slide(pres, slide))]
    else:
        target_slides = list(enumerate(pres["slides"], 1))

    type_filter = type.lower() if type else None
    alt_filter = alt_title.lower() if alt_title else None
    text_filter = contains.lower() if contains else None

    matches: list = []
    for idx, sl in target_slides:
        flat: list = []
        _walk_elements(sl.get("pageElements", []), recursive, flat)
        for el in flat:
            if type_filter and el["type"].lower() != type_filter:
                continue
            if alt_filter and alt_filter not in el.get("alt_title", "").lower():
                continue
            if text_filter and text_filter not in el.get("text", "").lower():
                continue
            matches.append({
                "slide_id": sl["objectId"],
                "slide_index": idx,
                **el,
            })
    return {"matches": matches}


def _resolve_slide_index(pres: dict, slide: str) -> int:
    """1-based index of the slide, by either index-string or objectId."""
    s = str(slide).strip()
    for i, sl in enumerate(pres["slides"], 1):
        if str(i) == s or sl["objectId"] == s:
            return i
    raise ValueError(f"slide not found: {slide!r}")


@mcp.tool(annotations=READ_ONLY)
def export_pres(presentation: str, format: str = "pptx") -> dict:
    """Download an existing Google Slides deck as .pptx or .pdf. Returns local file path.

    Only when the user asks to download or send a deck that lives in Google
    Slides. Not a way to make a PowerPoint: a PowerPoint the user asks for is
    not built in Google Slides to be exported here.

    On the hosted server the file would land on the server, so this returns
    ``url`` instead: a Google download link that works for anyone who can
    open the deck, signed in to their browser.

    Args:
        format: 'pptx' or 'pdf'.
    """
    import os
    import tempfile

    pid = parse_pres_id(presentation)
    mime = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    }
    if format not in mime:
        raise ValueError(f"format must be pptx or pdf, got {format!r}")
    if remote_mode():
        return {"url": f"https://docs.google.com/presentation/d/{pid}/export/{format}", "format": format}

    drv = drive_service()
    req = drv.files().export_media(fileId=pid, mimeType=mime[format])
    fd, path = tempfile.mkstemp(suffix=f".{format}", prefix="gslides_export_")
    os.close(fd)
    from googleapiclient.http import MediaIoBaseDownload
    with open(path, "wb") as f:
        downloader = MediaIoBaseDownload(f, req)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    return {"path": path, "format": format}


@mcp.tool(annotations=DESTRUCTIVE)
def batch_apply(presentation: str, requests: list[dict]) -> dict:
    """Raw escape hatch: send a Slides API batchUpdate request list verbatim.

    Use this when an existing tool doesn't cover what you need (e.g. exotic
    request types). Prefer the typed tools first — they encode the gotchas.

    Args:
        requests: a list of Slides API request objects (e.g. [{"createSlide": {...}}, ...])

    Returns: the API replies array.
    """
    pid = parse_pres_id(presentation)
    resp = slide_service().presentations().batchUpdate(
        presentationId=pid, body={"requests": requests}
    ).execute()
    return {"replies": resp.get("replies", [])}
