"""Layout tools.

Two families share this module:

- element layout on a slide: transform, z-order, duplicate, delete;
- slide layouts (the theme's masters/layouts/placeholders): read them,
  screenshot them, build slides on them, rebuild a slide on another one.
"""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter

from googleapiclient.errors import HttpError
from fastmcp.utilities.types import Image

from ..app import ADDITIVE, DESTRUCTIVE, READ_ONLY, mcp
from ..auth import slide_service
from . import qa
from ..util import (
    PT_TO_EMU,
    find_element,
    md_requests,
    parse_pres_id,
    resolve_layout,
    validate_object_id,
)


@mcp.tool(annotations=ADDITIVE)
def transform_element(
    presentation: str,
    element: str,
    x_pt: float | None = None,
    y_pt: float | None = None,
    dx_pt: float | None = None,
    dy_pt: float | None = None,
    width_pt: float | None = None,
    height_pt: float | None = None,
) -> dict:
    """Move and / or resize an element (shape, image, table, group, linked Sheets chart).

    Move, axis by axis: absolute (x_pt, y_pt) or relative (dx_pt, dy_pt). Each axis
    stands alone: ``x_pt`` only moves horizontally and keeps the top edge, ``dy_pt``
    only nudges vertically, ``x_pt`` + ``dy_pt`` mixes both; only ``x_pt`` with
    ``dx_pt`` (or ``y_pt`` with ``dy_pt``) is refused. Resize: width_pt and / or
    height_pt, the displayed size in points. One dimension alone scales the element
    uniformly (the aspect is kept: a chart or an image is never squashed); pass both
    to set the aspect. Resizing alone keeps the position.

    Without a resize the element's existing scaleX/scaleY are preserved (critical —
    naive `applyMode: ABSOLUTE` with `scale: 1` silently resizes elements that had
    custom scales applied at create time).
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    el, _slide = find_element(pres, element)
    if el is None:
        raise ValueError(f"element not found: {element!r}")
    t = el.get("transform", {})
    cur_sx = t.get("scaleX", 1)
    cur_sy = t.get("scaleY", 1)
    cur_tx = t.get("translateX", 0)
    cur_ty = t.get("translateY", 0)

    if x_pt is not None and dx_pt is not None:
        raise ValueError("x_pt and dx_pt both move horizontally: give one of them")
    if y_pt is not None and dy_pt is not None:
        raise ValueError("y_pt and dy_pt both move vertically: give one of them")
    if all(v is None for v in (x_pt, y_pt, dx_pt, dy_pt, width_pt, height_pt)):
        raise ValueError("provide coordinates (x_pt / y_pt, dx_pt / dy_pt) or a size (width_pt / height_pt)")

    # an axis left out keeps its position
    new_tx = int(x_pt * PT_TO_EMU) if x_pt is not None else int(cur_tx + (dx_pt or 0) * PT_TO_EMU)
    new_ty = int(y_pt * PT_TO_EMU) if y_pt is not None else int(cur_ty + (dy_pt or 0) * PT_TO_EMU)
    if width_pt is not None or height_pt is not None:
        # displayed size = base size × scale: change the scale, never the base size
        size = el.get("size", {})
        base_w = size.get("width", {}).get("magnitude")
        base_h = size.get("height", {}).get("magnitude")
        if not base_w or not base_h:
            raise ValueError(f"element {element!r} has no size to scale (a line?)")
        if width_pt is not None and height_pt is not None:
            cur_sx = width_pt * PT_TO_EMU / base_w
            cur_sy = height_pt * PT_TO_EMU / base_h
        elif width_pt is not None:  # keep the aspect: both scales move by the same factor
            k = (width_pt * PT_TO_EMU / base_w) / (cur_sx or 1)
            cur_sx, cur_sy = cur_sx * k, cur_sy * k
        else:
            k = (height_pt * PT_TO_EMU / base_h) / (cur_sy or 1)
            cur_sx, cur_sy = cur_sx * k, cur_sy * k

    svc.presentations().batchUpdate(
        presentationId=pid,
        body={"requests": [{"updatePageElementTransform": {
            "objectId": element,
            "applyMode": "ABSOLUTE",
            "transform": {
                "scaleX": cur_sx, "scaleY": cur_sy,
                "translateX": new_tx, "translateY": new_ty,
                "unit": "EMU",
            },
        }}]},
    ).execute()
    return {"element": element, "x_emu": new_tx, "y_emu": new_ty, "scale_x": cur_sx, "scale_y": cur_sy}


@mcp.tool(annotations=ADDITIVE)
def zorder(presentation: str, elements: list[str], op: str) -> dict:
    """Z-order: BRING_TO_FRONT | SEND_TO_BACK | BRING_FORWARD | SEND_BACKWARD."""
    valid = {"BRING_TO_FRONT", "SEND_TO_BACK", "BRING_FORWARD", "SEND_BACKWARD"}
    if op not in valid:
        raise ValueError(f"op must be one of {valid}, got {op!r}")
    pid = parse_pres_id(presentation)
    slide_service().presentations().batchUpdate(
        presentationId=pid,
        body={"requests": [{"updatePageElementsZOrder": {
            "pageObjectIds": elements, "operation": op
        }}]},
    ).execute()
    return {"elements": elements, "op": op}


@mcp.tool(annotations=ADDITIVE)
def duplicate_element(
    presentation: str,
    element: str,
    new_id: str | None = None,
    dx_pt: float = 0.0,
    dy_pt: float = 0.0,
) -> dict:
    """Duplicate an element on the same slide, optionally offset by (dx, dy)."""
    pid = parse_pres_id(presentation)
    svc = slide_service()
    req: dict = {"duplicateObject": {"objectId": element}}
    if new_id:
        req["duplicateObject"]["objectIds"] = {element: new_id}
    resp = svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": [req]}
    ).execute()
    dup_id = resp["replies"][0]["duplicateObject"]["objectId"]

    if dx_pt or dy_pt:
        # Shift the dup by (dx, dy). Relative apply preserves the dup's scale.
        svc.presentations().batchUpdate(
            presentationId=pid,
            body={"requests": [{"updatePageElementTransform": {
                "objectId": dup_id,
                "applyMode": "RELATIVE",
                "transform": {
                    "scaleX": 1, "scaleY": 1,
                    "translateX": int(dx_pt * PT_TO_EMU),
                    "translateY": int(dy_pt * PT_TO_EMU),
                    "unit": "EMU",
                },
            }}]},
        ).execute()
    return {"original": element, "duplicate": dup_id, "dx_pt": dx_pt, "dy_pt": dy_pt}


@mcp.tool(annotations=DESTRUCTIVE)
def delete_elements(presentation: str, elements: list[str]) -> dict:
    """Delete one or more elements by objectId."""
    pid = parse_pres_id(presentation)
    reqs = [{"deleteObject": {"objectId": e}} for e in elements]
    slide_service().presentations().batchUpdate(
        presentationId=pid, body={"requests": reqs}
    ).execute()
    return {"deleted": elements}


# =============================================================================
# Slide layouts (masters / layouts / placeholders)
#
# What the Slides API allows: read layouts and masters, create a slide on a
# given layout, edit a layout's own elements. What it does NOT allow — and
# nothing below works around: creating a layout, changing an existing slide's
# layout (``slideProperties.layoutObjectId`` is read-only), importing a theme
# from another deck.
# =============================================================================

_RAW_LIMIT_BYTES = 200_000

_PAGE_KINDS = {
    "SLIDE": "slide",
    "LAYOUT": "layout",
    "MASTER": "master",
    "NOTES": "notes",
    "NOTES_MASTER": "notes_master",
}

# Everything list_layouts needs and nothing else — full decks run to MBs.
_LAYOUT_FIELDS = (
    "pageSize,"
    "masters(objectId,masterProperties(displayName)),"
    "layouts(objectId,layoutProperties(name,displayName,masterObjectId),"
    "pageElements(objectId,size,transform,shape(placeholder(type,index)))),"
    "slides(objectId,slideProperties(layoutObjectId,masterObjectId))"
)
_BODY_TYPES = {"BODY", "OBJECT", "PICTURE", "CHART", "TABLE", "DIAGRAM", "MEDIA", "CLIP_ART"}
_TITLE_TYPES = {"TITLE", "CENTERED_TITLE"}
_FOOTER_TYPES = {"FOOTER", "SLIDE_NUMBER", "DATE_AND_TIME", "HEADER"}


def _json_len(obj) -> int:
    return len(json.dumps(obj))


@mcp.tool(annotations=READ_ONLY)
def get_presentation(presentation: str, fields: str | None = None) -> dict:
    """Raw ``presentations.get`` passthrough.

    Use this when the typed tools don't expose what you need (theme colors,
    exact text styles, page size…). Prefer a ``fields`` mask; without one the
    full deck is returned, trimmed to whole slides so the JSON stays under
    200 kB.

    Args:
        fields: optional Google field mask, e.g.
            ``"slides(objectId,pageElements(objectId,shape(text)))"`` or
            ``"layouts(objectId,layoutProperties)"``.

    Returns: ``{presentation, truncated, size_bytes}``. When truncated (no
    ``fields`` and the deck exceeds 200 kB): ``slides_total``,
    ``slides_included`` (kept from the start of the deck) and a ``hint``.

    Example: ``get_presentation(deck, fields="pageSize,masters(objectId)")``
    """
    pid = parse_pres_id(presentation)
    kwargs: dict = {"presentationId": pid}
    if fields:
        kwargs["fields"] = fields
    pres = slide_service().presentations().get(**kwargs).execute()
    size = _json_len(pres)
    if fields or size <= _RAW_LIMIT_BYTES:
        return {"presentation": pres, "truncated": False, "size_bytes": size}

    slides = pres.get("slides", [])
    head = {k: v for k, v in pres.items() if k != "slides"}
    running = _json_len(head) + len('"slides": []')
    kept: list[dict] = []
    for slide in slides:
        cost = _json_len(slide) + 2
        if running + cost > _RAW_LIMIT_BYTES:
            break
        kept.append(slide)
        running += cost
    head["slides"] = kept
    return {
        "presentation": head,
        "truncated": True,
        "size_bytes": size,
        "limit_bytes": _RAW_LIMIT_BYTES,
        "slides_total": len(slides),
        "slides_included": len(kept),
        "hint": (
            "Response exceeded 200 kB; only the first slides are included. "
            "Pass fields= to narrow the mask, or get_page for a single page."
        ),
    }


def _page_kind(page: dict) -> str:
    kind = _PAGE_KINDS.get(page.get("pageType", ""))
    if kind:
        return kind
    for key, inferred in (
        ("slideProperties", "slide"),
        ("layoutProperties", "layout"),
        ("masterProperties", "master"),
        ("notesProperties", "notes"),
    ):
        if key in page:
            return inferred
    return "unknown"


@mcp.tool(annotations=READ_ONLY)
def get_page(presentation: str, page_id: str, compact: bool = False) -> dict:
    """Return one page — a slide, a layout, a master or a notes page.

    Layout and master pages carry the placeholders and theme-level elements
    that ``inspect_slide`` never shows. Notes page ids come from
    ``slideProperties.notesPage.objectId``.

    Args:
        page_id: objectId of any page kind (from list_layouts, list_slides or
            get_presentation).
        compact: when True, return one line per element (id, type, geometry
            in pt, text, ``placeholder`` {type, index} when inherited,
            ``parent_id`` inside groups) instead of Google's raw JSON with
            every text-style level. Use it to map a layout's placeholders;
            keep the raw form for debugging.

    Returns: ``{page_kind: "slide"|"layout"|"master"|"notes", page: {...}}``,
    or with ``compact=True`` ``{page_kind, page_id, elements: [...]}``.

    Example: ``get_page(deck, "p4", compact=True)["elements"]``
    """
    pid = parse_pres_id(presentation)
    try:
        page = slide_service().presentations().pages().get(
            presentationId=pid, pageObjectId=page_id
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            raise ValueError(
                f"page not found: {page_id!r} in presentation {pid}. "
                "Use list_slides or list_layouts to find page ids."
            ) from None
        raise
    kind = _page_kind(page)
    if not compact:
        return {"page_kind": kind, "page": page}

    from .deck import _walk_elements

    flat: list[dict] = []
    _walk_elements(page.get("pageElements", []), True, flat)
    placeholders: dict[str, dict] = {}

    def collect(elements: list) -> None:
        for el in elements:
            ph = el.get("shape", {}).get("placeholder")
            if ph is not None:
                placeholders[el["objectId"]] = {"type": ph.get("type", "NONE"), "index": ph.get("index", 0)}
            collect(el.get("elementGroup", {}).get("children", []))

    collect(page.get("pageElements", []))
    for entry in flat:
        if entry["id"] in placeholders:
            entry["placeholder"] = placeholders[entry["id"]]
    return {"page_kind": kind, "page_id": page_id, "elements": flat}


def _layout_placeholders(layout: dict) -> list[dict]:
    """Placeholders of a layout page, in page order, with their geometry in pt. Google omits index 0."""
    out = []
    for el in layout.get("pageElements", []):
        ph = el.get("shape", {}).get("placeholder")
        if ph is not None:
            row = {
                "type": ph.get("type", "NONE"),
                "index": ph.get("index", 0),
                "object_id": el["objectId"],
            }
            geo = _geometry(el)
            if geo:
                row.update(geo)
            out.append(row)
    return out


def _geometry(el: dict) -> dict | None:
    s, t = el.get("size"), el.get("transform")
    if not s or not t:
        return None
    sx, sy = t.get("scaleX", 1), t.get("scaleY", 1)
    return {"x": round(t.get("translateX", 0) / PT_TO_EMU, 1), "y": round(t.get("translateY", 0) / PT_TO_EMU, 1),
            "w": round(s.get("width", {}).get("magnitude", 0) * sx / PT_TO_EMU, 1),
            "h": round(s.get("height", {}).get("magnitude", 0) * sy / PT_TO_EMU, 1)}


def _content_area(placeholders: list[dict], page_w: float, page_h: float) -> dict | None:
    """Where components go on a slide of this layout: the body placeholders' box,
    else the band between the title and the footer. None without geometry."""
    with_geo = [p for p in placeholders if "x" in p]
    if not with_geo:
        return None
    bodies = [p for p in with_geo if p["type"] in _BODY_TYPES]
    if bodies:
        x0 = min(p["x"] for p in bodies)
        y0 = min(p["y"] for p in bodies)
        x1 = max(p["x"] + p["w"] for p in bodies)
        y1 = max(p["y"] + p["h"] for p in bodies)
        return {"x": round(x0, 1), "y": round(y0, 1), "w": round(x1 - x0, 1), "h": round(y1 - y0, 1), "from": "body placeholders"}
    titles = [p for p in with_geo if p["type"] in _TITLE_TYPES]
    footers = [p for p in with_geo if p["type"] in _FOOTER_TYPES]
    x0 = min((p["x"] for p in titles), default=30.0)
    x1 = max((p["x"] + p["w"] for p in titles), default=page_w - 30.0)
    y0 = max((p["y"] + p["h"] for p in titles), default=30.0) + 12
    footer_top = min((p["y"] for p in footers if p["y"] > y0), default=None)
    y1 = footer_top - 8 if footer_top is not None else page_h - 30.0
    if y1 - y0 < 60 or x1 - x0 < 120:  # the title fills the layout (« Argument principal »): the page, minus margins
        return {"x": 30.0, "y": 30.0, "w": round(page_w - 60, 1), "h": round(page_h - 60, 1), "from": "page (the title fills the layout)"}
    return {"x": round(x0, 1), "y": round(y0, 1), "w": round(x1 - x0, 1), "h": round(y1 - y0, 1), "from": "below the title"}


@mcp.tool(annotations=READ_ONLY)
def list_layouts(presentation: str, only_used_master: bool = True) -> dict:
    """List masters and layouts with their placeholders and usage counts.

    The starting point for template-driven builds: pick a layout here, then
    ``create_slide_from_layout`` / ``build_from_outline`` by display name.

    Args:
        only_used_master: when True (default) only layouts belonging to a
            master that at least one slide uses are returned. Copied decks
            accumulate orphan masters whose layouts you almost never want.

    Returns::

        {page: {w, h},
         masters: [{master_id, display_name, used_by_slides}],
         layouts: [{layout_id, display_name, name, master_id,
                    placeholders: [{type, index, object_id, x, y, w, h}],
                    content_area: {x, y, w, h, from} | null, used_by_slides}]}

    ``content_area`` (pt) is where components go on a slide of that layout:
    the body placeholders' box, else the band between the title and the
    footer — pass it as ``x_pt`` / ``y_pt`` / ``width_pt`` to
    ``insert_component`` when rebuilding a slide on another layout.

    Example: ``list_layouts(deck)["layouts"][0]["content_area"]``
    """
    pid = parse_pres_id(presentation)
    pres = slide_service().presentations().get(
        presentationId=pid, fields=_LAYOUT_FIELDS
    ).execute()
    size = pres.get("pageSize", {})
    page_w = size.get("width", {}).get("magnitude", 9144000) / PT_TO_EMU
    page_h = size.get("height", {}).get("magnitude", 5143500) / PT_TO_EMU

    layout_use, master_use = _usage_counts(pres)
    masters = [
        {
            "master_id": m["objectId"],
            "display_name": m.get("masterProperties", {}).get("displayName", ""),
            "used_by_slides": master_use[m["objectId"]],
        }
        for m in pres.get("masters", [])
        if not only_used_master or master_use[m["objectId"]] > 0
    ]
    kept_masters = {m["master_id"] for m in masters}
    layouts = [
        {
            "layout_id": l["objectId"],
            "display_name": l.get("layoutProperties", {}).get("displayName", ""),
            "name": l.get("layoutProperties", {}).get("name", ""),
            "master_id": l.get("layoutProperties", {}).get("masterObjectId"),
            "placeholders": (phs := _layout_placeholders(l)),
            "content_area": _content_area(phs, page_w, page_h),
            "used_by_slides": layout_use[l["objectId"]],
        }
        for l in pres.get("layouts", [])
        if l.get("layoutProperties", {}).get("masterObjectId") in kept_masters
    ]
    return {"page": {"w": round(page_w, 1), "h": round(page_h, 1)}, "masters": masters, "layouts": layouts}


def _usage_counts(pres: dict) -> tuple[Counter, Counter]:
    """(layout_id → slides using it, master_id → slides using it)."""
    layout_by_id = {l["objectId"]: l for l in pres.get("layouts", [])}
    layout_use: Counter = Counter()
    master_use: Counter = Counter()
    for slide in pres.get("slides", []):
        sp = slide.get("slideProperties", {})
        layout_id = sp.get("layoutObjectId")
        if layout_id:
            layout_use[layout_id] += 1
        master_id = sp.get("masterObjectId") or layout_by_id.get(layout_id, {}).get(
            "layoutProperties", {}
        ).get("masterObjectId")
        if master_id:
            master_use[master_id] += 1
    return layout_use, master_use


def _layouts_of_used_masters(pres: dict) -> list[dict]:
    _, master_use = _usage_counts(pres)
    return [
        l for l in pres.get("layouts", [])
        if master_use[l.get("layoutProperties", {}).get("masterObjectId")] > 0
    ]


def _display_name(layout: dict) -> str:
    return layout.get("layoutProperties", {}).get("displayName") or layout["objectId"]


# --- screenshots ---------------------------------------------------------------

@mcp.tool(annotations=READ_ONLY)
def screenshot_layout(
    presentation: str, layout: str, size: str = "MEDIUM", annotate: bool = False
) -> Image:
    """Render one layout page as an inline image.

    Route: ``presentations.pages.getThumbnail`` accepts a layout objectId
    directly (verified live — it also accepts masters), so this is a single
    read call: no temporary slide is created and nothing is written to the
    deck. The render shows the layout's placeholders with their prompt text
    on the master's background.

    Args:
        layout: layout_id or display name (exact, then case/accent-insensitive;
            ambiguous names raise — see list_layouts).
        size: SMALL (~200w) | MEDIUM (~800w) | LARGE (~1600w).
        annotate: render the **placeholder map** instead: a temporary slide is
            created on the layout with every text placeholder filled with its
            fill key (``TITLE``, ``BODY[0]``, ``SUBTITLE[3]``…), captured, and
            deleted again (in a ``finally``). Keys follow the layout's element
            order, which is often not the visual order — this is how you see
            which key lands where before calling ``create_slide_from_layout``.
            Picture/chart/table/slide-number placeholders take no text and
            stay blank.

    Example: ``screenshot_layout(deck, "Arborescence02", annotate=True)``
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid, fields=_LAYOUT_FIELDS).execute()
    target = resolve_layout(pres, layout)
    if not annotate:
        return qa._render_thumbnail(svc, pid, target["objectId"], size)

    temp_id = _new_id("tmp")
    mappings: list[dict] = []
    reqs: list[dict] = []
    for key, ph_id in _placeholder_slots(target).items():
        if key.split("[")[0] in _NO_TEXT_PLACEHOLDERS:
            continue
        new_id = f"{temp_id}_{re.sub(r'[^a-z0-9]', '', key.lower())}"
        mappings.append({"layoutPlaceholderObjectId": ph_id, "objectId": new_id})
        reqs.append({"insertText": {"objectId": new_id, "text": key, "insertionIndex": 0}})
    create: dict = {"objectId": temp_id, "slideLayoutReference": {"layoutId": target["objectId"]}}
    if mappings:
        create["placeholderIdMappings"] = mappings
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": [{"createSlide": create}, *reqs]}
    ).execute()
    try:
        return qa._render_thumbnail(svc, pid, temp_id, size)
    finally:
        svc.presentations().batchUpdate(
            presentationId=pid, body={"requests": [{"deleteObject": {"objectId": temp_id}}]}
        ).execute()


@mcp.tool(annotations=READ_ONLY)
def screenshot_layouts(
    presentation: str, layouts: list[str] | None = None, size: str = "SMALL"
) -> Image:
    """Render several layouts as one vertical strip, each captioned by name.

    The visual companion to ``list_layouts``: look at every layout of the
    deck's theme in one image before choosing which to build on.

    Args:
        layouts: layout ids or display names, rendered in the given order.
            Default: every layout of the masters actually used by slides
            (same filter as ``list_layouts(only_used_master=True)``).
        size: SMALL | MEDIUM | LARGE. Default SMALL — a theme easily has
            10-20 layouts.

    Returns: inline PNG strip, captions = layout display names.

    Example: ``screenshot_layouts(deck, layouts=["A_Retenir", "Titre et corps"])``
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid, fields=_LAYOUT_FIELDS).execute()
    if layouts is None:
        chosen = _layouts_of_used_masters(pres)
    else:
        chosen = [resolve_layout(pres, ref) for ref in layouts]  # all resolved before any fetch
    if not chosen:
        raise ValueError("no layouts to render — the deck has no slide using any master?")
    labeled = [(_display_name(l), l["objectId"]) for l in chosen]
    return Image(path=qa._fetch_strip(svc, pid, labeled, size))


# --- building slides on layouts ------------------------------------------------

_FILL_KEY_RE = re.compile(r"^([A-Z_]+)(?:\[(\d+)\])?$")

# Placeholder types that are not text shapes: insertText on them fails.
_NO_TEXT_PLACEHOLDERS = {
    "PICTURE", "CHART", "TABLE", "CLIP_ART", "DIAGRAM", "MEDIA", "SLIDE_IMAGE", "SLIDE_NUMBER",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _placeholder_slots(layout: dict) -> dict[str, str]:
    """Fill keys accepted for ``layout`` → layout placeholder objectId.

    A type present once is addressed by its bare name (``TITLE``); a type
    present N times by ``TYPE[0]``…``TYPE[N-1]`` in page order.
    """
    by_type: dict[str, list[str]] = {}
    for ph in _layout_placeholders(layout):
        by_type.setdefault(ph["type"], []).append(ph["object_id"])
    slots: dict[str, str] = {}
    for ptype, ids in by_type.items():
        if len(ids) == 1:
            slots[ptype] = ids[0]
        else:
            for k, oid in enumerate(ids):
                slots[f"{ptype}[{k}]"] = oid
    return slots


def _resolve_fill_key(key: str, slots: dict[str, str], layout_name: str) -> str:
    """Canonical slot key for a caller-supplied fill key, or a precise error."""
    k = str(key).strip().upper()
    if k in slots:
        return k
    m = _FILL_KEY_RE.match(k)
    base = m.group(1) if m else k
    indexed = sorted(s for s in slots if s.startswith(f"{base}["))
    if indexed and "[" not in k:
        raise ValueError(
            f"placeholder {key!r} is ambiguous on layout {layout_name!r}: it has "
            f"{len(indexed)} {base} placeholders — use one of {', '.join(indexed)}"
        )
    if m and m.group(2) == "0" and base in slots:
        return base  # TYPE[0] on a single-placeholder type
    raise ValueError(
        f"no placeholder {key!r} on layout {layout_name!r}; available: "
        f"{', '.join(sorted(slots)) or 'none'}"
    )


def _plan_slide(layout: dict, fills: dict | None, slide_id: str,
                insertion_index: int | None) -> dict:
    """Requests for one slide on ``layout`` with ``fills`` written in.

    ``createSlide`` pins the placeholder objectIds via placeholderIdMappings
    so the text requests can target them in the same batch. Inherited
    placeholders are born empty: only insertText-family requests are emitted,
    never deleteText (which fails the whole batch on empty text).
    """
    name = _display_name(layout)
    slots = _placeholder_slots(layout)
    mappings: list[dict] = []
    text_reqs: list[dict] = []
    filled: list[str] = []
    used: set[str] = set()
    for key, md in (fills or {}).items():
        slot = _resolve_fill_key(key, slots, name)
        if slot in used:
            raise ValueError(f"placeholder {slot} is filled twice on layout {name!r} ({key!r})")
        if md is None or not str(md).strip():
            continue
        used.add(slot)
        new_id = f"{slide_id[:32]}_{re.sub(r'[^a-z0-9]', '', slot.lower())}"
        mappings.append({"layoutPlaceholderObjectId": slots[slot], "objectId": new_id})
        text_reqs.extend(md_requests(new_id, str(md)))
        filled.append(key)

    create: dict = {
        "objectId": slide_id,
        "slideLayoutReference": {"layoutId": layout["objectId"]},
    }
    if insertion_index is not None:
        create["insertionIndex"] = insertion_index
    if mappings:
        create["placeholderIdMappings"] = mappings
    return {
        "requests": [{"createSlide": create}, *text_reqs],
        "filled": filled,
        "left_empty": [s for s in slots if s not in used],
    }


@mcp.tool(annotations=ADDITIVE)
def create_slide_from_layout(
    presentation: str,
    layout: str,
    insertion_index: int | None = None,
    fills: dict | None = None,
    object_id: str | None = None,
) -> dict:
    """Create a slide on a layout and fill its placeholders — one batchUpdate.

    The layout's placeholders (title, body, subtitle…) are inherited with the
    theme's styling; ``fills`` writes markdown into them through the same
    writer as ``write_text_markdown`` (bold, italic, bullets). Atomic: if
    Google rejects any request, no slide is created.

    Args:
        layout: layout_id or display name (see ``list_layouts``).
        insertion_index: 0-based position (same convention as ``create_slide``
            and ``move_slide``); default appends at the end.
        fills: ``{"TITLE": "...", "BODY": "- a\\n- b"}``. When a layout has
            several placeholders of one type, address them as ``"BODY[0]"``,
            ``"BODY[1]"`` (page order; ``list_layouts`` shows the order).
            Empty strings leave the placeholder untouched.
        object_id: optional custom slide objectId (5–50 chars, ``[A-Za-z0-9_-]``,
            not digit-leading).

    Returns: ``{slide_id, index, layout_id, layout_name, placeholders_filled,
    placeholders_left_empty}`` — ``index`` is **1-based**, the ref that
    ``screenshot``, ``list_slides`` and ``delete_slides`` take.

    Example::

        create_slide_from_layout(deck, "A_Retenir",
            fills={"TITLE": "Ce qu'il faut retenir",
                   "BODY[0]": "- point 1\\n- point 2", "BODY[1]": "**Chiffre clé**"})
    """
    validate_object_id(object_id)
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid, fields=_LAYOUT_FIELDS).execute()
    target = resolve_layout(pres, layout)
    slide_id = object_id or _new_id("sl")
    plan = _plan_slide(target, fills, slide_id, insertion_index)
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": plan["requests"]}
    ).execute()
    index = (insertion_index + 1) if insertion_index is not None else len(pres.get("slides", [])) + 1
    return {
        "slide_id": slide_id,
        "index": index,
        "layout_id": target["objectId"],
        "layout_name": _display_name(target),
        "placeholders_filled": plan["filled"],
        "placeholders_left_empty": plan["left_empty"],
    }


@mcp.tool(annotations=ADDITIVE)
def build_from_outline(
    presentation: str, outline: list[dict], insertion_index: int | None = None
) -> list[dict]:
    """Create a run of slides from an ordered outline — one batchUpdate for all.

    Every layout name and fill key is resolved first; any problem aborts
    before a single write and the error lists all of them. Then all slides go
    in one atomic batch: if Google rejects it, nothing is created.

    Args:
        outline: ``[{"layout": <id or name>, "fills": {...}}, ...]`` — same
            ``fills`` contract as ``create_slide_from_layout``.
        insertion_index: 0-based position of the first slide (same convention
            as ``create_slide``); the rest follow in order. Default appends
            at the end.

    Returns: ``[{index, slide_id, layout_name}, ...]`` in outline order;
    ``index`` is **1-based** (the ref ``screenshot_range`` takes).

    Example::

        build_from_outline(deck, [
            {"layout": "A_Retenir", "fills": {"TITLE": "Synthèse", "BODY[0]": "- ..."}},
            {"layout": "Arborescence02", "fills": {"TITLE": "Plan du site"}},
        ])
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid, fields=_LAYOUT_FIELDS).execute()

    problems: list[str] = []
    plans: list[tuple[dict, dict]] = []
    for i, item in enumerate(outline):
        if not isinstance(item, dict) or "layout" not in item:
            problems.append(f"outline[{i}]: missing 'layout' key")
            continue
        idx = None if insertion_index is None else insertion_index + i
        try:
            target = resolve_layout(pres, item["layout"])
            plans.append((target, _plan_slide(target, item.get("fills"), _new_id("sl"), idx)))
        except ValueError as exc:
            problems.append(f"outline[{i}]: {exc}")
    if problems:
        raise ValueError(
            "build_from_outline: nothing was written — fix these first:\n  "
            + "\n  ".join(problems)
        )

    requests = [r for _, plan in plans for r in plan["requests"]]
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": requests}
    ).execute()
    base = (len(pres.get("slides", [])) if insertion_index is None else insertion_index) + 1
    return [
        {
            "index": base + i,
            "slide_id": plan["requests"][0]["createSlide"]["objectId"],
            "layout_name": _display_name(target),
        }
        for i, (target, plan) in enumerate(plans)
    ]


# --- relayout (destructive) ------------------------------------------------------

# Element kinds the API can't recreate on another page. Anything not a plain
# shape or image is refused up front rather than silently dropped.
_RELAYOUT_REFUSED = {
    "elementGroup": "group",
    "table": "table",
    "video": "video",
    "line": "line",
    "sheetsChart": "chart",
    "wordArt": "word art",
    "speakerSpotlight": "speaker spotlight",
}

# Placeholder text moves by exact type; the only alias is the two title kinds.
_TITLE_KINDS = {"TITLE": ("CENTERED_TITLE",), "CENTERED_TITLE": ("TITLE",)}


def _plain_text(el: dict) -> str:
    runs = (
        te.get("textRun", {}).get("content", "")
        for te in el.get("shape", {}).get("text", {}).get("textElements", [])
    )
    return "".join(runs).rstrip("\n")


@mcp.tool(annotations=DESTRUCTIVE)
def relayout_slide(presentation: str, slide: str, layout: str) -> dict:
    """Rebuild a slide on another layout, then delete the original. DESTRUCTIVE.

    The API can't change ``slideProperties.layoutObjectId`` (read-only), so
    this creates a new slide on ``layout`` right after the original, moves
    the content over, and deletes the original:

    - placeholder text is copied by placeholder type (TITLE ↔ CENTERED_TITLE
      count as the same); text whose type has no placeholder on the target
      is returned in ``unplaced_text`` rather than dropped silently;
    - plain shapes are recreated (type, geometry, solid fill, text) and images
      are recreated from their content URL; character-level styling is not
      carried over — the new layout's styling applies, which is the point.

    Speaker notes are carried over (plain text). Refused, with the offending
    element ids: groups, tables, videos, lines, charts, word art. Batches:
    the rebuild is atomic; then the notes copy; then the deletion. If a later
    step fails, both slides stay and the error says which to remove.

    Args:
        slide: 1-based index or objectId.
        layout: target layout id or display name.

    Returns: ``{new_slide_id, deleted_slide_id, index, layout_id, layout_name,
    placeholders_copied, elements_recreated, unplaced_text, notes_copied}`` —
    ``index`` is **1-based** (unchanged from the original's position).

    Example: ``relayout_slide(deck, 4, "Titre et corps")``
    """
    from .deck import _resolve_slide, _resolve_slide_index

    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    source = _resolve_slide(pres, slide)
    src_id = source["objectId"]
    src_index = _resolve_slide_index(pres, slide) - 1
    target = resolve_layout(pres, layout)

    elements = source.get("pageElements", [])
    refused = [
        f"{el['objectId']} ({label})"
        for el in elements
        for key, label in _RELAYOUT_REFUSED.items()
        if key in el
    ] + [
        f"{el['objectId']} (unsupported)"
        for el in elements
        if "shape" not in el and "image" not in el
        and not any(k in el for k in _RELAYOUT_REFUSED)
    ]
    if refused:
        raise ValueError(
            f"relayout_slide refused for slide {src_id}: it contains "
            f"{', '.join(refused)}, which the API can't recreate on another "
            "slide. Delete those elements first, or duplicate the slide and "
            "rebuild by hand."
        )

    available: dict[str, list[str]] = {}
    for ph in _layout_placeholders(target):
        available.setdefault(ph["type"], []).append(ph["object_id"])

    new_id = _new_id("sl")
    mappings: list[dict] = []
    build: list[dict] = []
    copied: list[str] = []
    unplaced: list[dict] = []
    recreated: list[str] = []
    for n, el in enumerate(elements):
        placeholder = el.get("shape", {}).get("placeholder")
        text = _plain_text(el)
        if placeholder is not None:
            if not text:
                continue
            src_type = placeholder.get("type", "NONE")
            dst_type = next(
                (t for t in (src_type, *_TITLE_KINDS.get(src_type, ())) if available.get(t)),
                None,
            )
            if dst_type is None:
                unplaced.append({"type": src_type, "text": text})
                continue
            ph_new = f"{new_id}_ph{n}"
            mappings.append({
                "layoutPlaceholderObjectId": available[dst_type].pop(0),
                "objectId": ph_new,
            })
            build.append({"insertText": {"objectId": ph_new, "text": text}})
            copied.append(f"{src_type}->{dst_type}")
            continue

        el_new = f"{new_id}_el{n}"
        props = {"pageObjectId": new_id, "size": el["size"], "transform": el["transform"]}
        if "image" in el:
            build.append({"createImage": {
                "objectId": el_new, "url": el["image"]["contentUrl"], "elementProperties": props,
            }})
        else:
            build.append({"createShape": {
                "objectId": el_new,
                "shapeType": el["shape"].get("shapeType", "TEXT_BOX"),
                "elementProperties": props,
            }})
            fill = el["shape"].get("shapeProperties", {}).get("shapeBackgroundFill", {}).get("solidFill")
            if fill:
                build.append({"updateShapeProperties": {
                    "objectId": el_new,
                    "shapeProperties": {"shapeBackgroundFill": {"solidFill": fill}},
                    "fields": "shapeBackgroundFill.solidFill",
                }})
            if text:
                build.append({"insertText": {"objectId": el_new, "text": text}})
        recreated.append(el["objectId"])

    create: dict = {
        "objectId": new_id,
        "insertionIndex": src_index + 1,
        "slideLayoutReference": {"layoutId": target["objectId"]},
    }
    if mappings:
        create["placeholderIdMappings"] = mappings
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": [{"createSlide": create}, *build]}
    ).execute()

    notes_text = _speaker_notes_text(source)
    notes_copied = False
    if notes_text:
        try:
            new_page = svc.presentations().pages().get(
                presentationId=pid, pageObjectId=new_id
            ).execute()
            notes_shape = (
                new_page.get("slideProperties", {}).get("notesPage", {})
                .get("notesProperties", {}).get("speakerNotesObjectId")
            )
            if not notes_shape:
                raise RuntimeError("the new slide reports no speaker-notes shape")
            svc.presentations().batchUpdate(
                presentationId=pid,
                body={"requests": [{"insertText": {
                    "objectId": notes_shape, "text": notes_text, "insertionIndex": 0,
                }}]},
            ).execute()
            notes_copied = True
        except Exception as exc:
            raise RuntimeError(
                f"new slide {new_id} was built but its speaker notes could not be "
                f"copied ({exc}); the original {src_id} was kept. Remove {new_id} "
                "with delete_slides and retry."
            ) from None

    try:
        svc.presentations().batchUpdate(
            presentationId=pid, body={"requests": [{"deleteObject": {"objectId": src_id}}]}
        ).execute()
    except Exception as exc:
        raise RuntimeError(
            f"new slide {new_id} was built at index {src_index + 2} but the "
            f"original {src_id} could not be deleted ({exc}). Both slides are "
            f"in the deck — remove {src_id} with delete_slides."
        ) from None

    return {
        "new_slide_id": new_id,
        "deleted_slide_id": src_id,
        "index": src_index + 1,
        "layout_id": target["objectId"],
        "layout_name": _display_name(target),
        "placeholders_copied": copied,
        "elements_recreated": recreated,
        "unplaced_text": unplaced,
        "notes_copied": notes_copied,
    }


def _speaker_notes_text(slide: dict) -> str:
    page = slide.get("slideProperties", {}).get("notesPage") or {}
    shape_id = page.get("notesProperties", {}).get("speakerNotesObjectId")
    for el in page.get("pageElements", []):
        if el.get("objectId") == shape_id:
            return _plain_text(el)
    return ""
