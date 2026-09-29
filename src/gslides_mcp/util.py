"""Shared helpers: ID parsing, geometry, color, range parsing."""

from __future__ import annotations

import re
from typing import Iterable

PT_TO_EMU = 12700
EMU_TO_PT = 1 / 12700
INCH_TO_EMU = 914_400
SUBTLE_BASE_EMU = 100_000  # for ROUND_RECTANGLE subtle-radius trick (~5px visual)

_PRES_ID_RE = re.compile(r"/presentation/d/([a-zA-Z0-9_-]+)")
_DRIVE_ID_RE = re.compile(r"/(?:d|folders)/([a-zA-Z0-9_-]+)|[?&]id=([a-zA-Z0-9_-]+)")


def parse_pres_id(value: str) -> str:
    """Accept a bare presentation ID or a full Google Slides URL."""
    m = _PRES_ID_RE.search(value)
    return m.group(1) if m else value


def parse_drive_id(value: str) -> str:
    """A bare Drive id, or the id in a Slides / Sheets / Docs / Drive file or folder URL."""
    m = _DRIVE_ID_RE.search(value)
    return (m.group(1) or m.group(2)) if m else value.strip()


def hex_to_rgb01(hex_str: str) -> tuple[float, float, float]:
    """Convert 'F1EBE0' or '#F1EBE0' to a (r, g, b) 0-1 float tuple."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_color(hex_str: str) -> dict:
    """Build a Slides API rgbColor object from a hex string."""
    r, g, b = hex_to_rgb01(hex_str)
    return {"red": r, "green": g, "blue": b}


def resolve_slide_ids(svc, pres_id: str, refs: Iterable) -> list[str]:
    """Resolve slide refs (1-based int/string OR objectId) to objectIds."""
    pres = svc.presentations().get(presentationId=pres_id).execute()
    slides = pres["slides"]
    by_index = {str(i): s["objectId"] for i, s in enumerate(slides, 1)}
    by_id = {s["objectId"]: s["objectId"] for s in slides}
    out = []
    for ref in refs:
        ref = str(ref).strip()
        if ref in by_index:
            out.append(by_index[ref])
        elif ref in by_id:
            out.append(by_id[ref])
        else:
            raise ValueError(f"slide ref not found: {ref!r}")
    return out


def parse_range(s: str) -> dict:
    """ALL or 'START:END' → Slides textRange dict."""
    if s.upper() == "ALL":
        return {"type": "ALL"}
    start, end = s.split(":")
    return {"type": "FIXED_RANGE", "startIndex": int(start), "endIndex": int(end)}


def find_element(pres: dict, element_id: str) -> tuple[dict | None, dict | None]:
    """Walk slides + nested groups for element_id. Returns (element, slide)."""

    def _search(elements, slide):
        for el in elements:
            if el.get("objectId") == element_id:
                return el, slide
            children = el.get("elementGroup", {}).get("children", [])
            if children:
                result = _search(children, slide)
                if result[0] is not None:
                    return result
        return None, None

    for slide in pres.get("slides", []):
        el, s = _search(slide.get("pageElements", []), slide)
        if el is not None:
            return el, s
    return None, None


def emu_to_pt(emu: int | float) -> float:
    return emu * EMU_TO_PT


def pt_to_emu(pt: int | float) -> int:
    return int(pt * PT_TO_EMU)


_OBJECT_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{4,49}$")


def validate_object_id(value: str | None) -> None:
    """Pre-flight check for custom Slides API objectIds.

    Slides API rules:
        - Length 5–50 chars.
        - Allowed chars: ``[a-zA-Z0-9_-]``.
        - Must start with alpha or underscore (digit-leading rejected by API).

    Raises ValueError with a clear message if invalid. No-op when ``value`` is
    None — None means "let the server pick one."
    """
    if value is None:
        return
    if not _OBJECT_ID_RE.match(value):
        raise ValueError(
            f"invalid object_id {value!r}: must be 5–50 chars, "
            f"start with [A-Za-z_], and use only [A-Za-z0-9_-]. "
            f"(Slides API rejects shorter/exotic IDs with HTTP 400.)"
        )


def fold_text(s: str) -> str:
    """Case- and accent-insensitive comparison key ('Résumé' → 'resume')."""
    import unicodedata

    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )
    return stripped.casefold().strip()


def resolve_layout(pres: dict, ref: str) -> dict:
    """Find a layout page in ``pres`` by objectId or display name.

    Match tiers, first hit wins: exact ``layout_id`` → exact ``displayName``
    → case/accent-folded ``displayName`` → exact API ``name`` (e.g.
    ``TITLE_AND_BODY``) → folded API ``name``. A tier with several hits is an
    error listing every candidate with its id and master — copied decks pile
    up same-named layouts across masters and picking one silently would put
    content on the wrong theme.

    ``pres`` needs ``layouts[].objectId`` and ``layouts[].layoutProperties``.
    """
    ref_s = str(ref).strip()
    layouts = pres.get("layouts", [])

    def props(layout: dict) -> dict:
        return layout.get("layoutProperties", {})

    tiers = (
        lambda l: l.get("objectId") == ref_s,
        lambda l: props(l).get("displayName") == ref_s,
        lambda l: fold_text(props(l).get("displayName", "")) == fold_text(ref_s),
        lambda l: props(l).get("name") == ref_s,
        lambda l: fold_text(props(l).get("name", "")) == fold_text(ref_s),
    )
    for matches in tiers:
        hits = [l for l in layouts if matches(l)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            listing = "; ".join(
                f"{props(l).get('displayName')!r} (layout_id={l['objectId']}, "
                f"master={props(l).get('masterObjectId')})"
                for l in hits
            )
            raise ValueError(
                f"layout ref {ref!r} is ambiguous — {len(hits)} layouts match: "
                f"{listing}. Pass the layout_id instead."
            )
    available = sorted({props(l).get("displayName") or l["objectId"] for l in layouts})
    raise ValueError(
        f"layout not found: {ref!r}. Available layouts: {', '.join(available)}. "
        "Call list_layouts for ids, masters and placeholders."
    )


def md_requests(object_id: str, markdown: str, cell: tuple[int, int] | None = None) -> list[dict]:
    """Slides API requests that write ``markdown`` into an EMPTY text container.

    Same writer as ``write_text_markdown`` (gslides-api), minus the deleteText
    it would emit for existing content: this is for freshly created shapes,
    inherited placeholders and table cells, where a deleteText on empty text
    makes the whole batchUpdate fail.

    Args:
        cell: ``(row, column)`` when ``object_id`` is a table.

    Raises ValueError for markdown the writer can't express (fenced code,
    block quotes…) so callers can fail before any write.
    """
    from gslides_api.domain.table_cell import TableCellLocation
    from gslides_api.markdown.from_markdown import markdown_to_text_elements

    try:
        reqs = markdown_to_text_elements(markdown)
    except Exception as exc:  # gslides-api raises its own error hierarchy
        raise ValueError(f"unsupported markdown for {object_id!r}: {exc}") from None
    location = TableCellLocation(rowIndex=cell[0], columnIndex=cell[1]) if cell else None
    out: list[dict] = []
    for r in reqs:
        r.objectId = object_id
        if location is not None:
            r.cellLocation = location
        out.extend(r.to_request())
    return out
