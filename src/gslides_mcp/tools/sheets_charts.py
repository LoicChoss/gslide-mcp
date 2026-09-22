"""Native Google Sheets charts on slides: insert_sheets_chart, list_sheets_charts,
refresh_sheets_charts.

The chart itself is built in the spreadsheet (by a Sheets MCP or by hand);
this server only embeds it on a slide through ``createSheetsChart`` and
refreshes it. A *linked* chart stays a ``sheetsChart`` element that follows
the spreadsheet (data and style edited there show up after a refresh); an
*unlinked* one is flattened to a plain image at insert time. Slides can only
link charts, never tables: table data computed in Sheets is read with the
Sheets MCP and written with ``create_table`` / the ``table`` component.

The caller needs read access to the spreadsheet; the server's Drive scope
covers the user's own files.
"""

from __future__ import annotations

import re

from ..app import ADDITIVE, IDEMPOTENT, READ_ONLY, mcp
from ..auth import slide_service
from ..util import emu_to_pt, parse_pres_id, pt_to_emu, resolve_slide_ids, validate_object_id

_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def parse_sheet_id(value: str) -> str:
    """Accept a bare spreadsheet id or a full Google Sheets URL."""
    m = _SHEET_ID_RE.search(str(value))
    return m.group(1) if m else str(value).strip()


def _chart_elements(pres: dict, slide_ids: set[str] | None) -> list[dict]:
    """Every sheetsChart element of the deck (or of the given slides), with its geometry."""
    out: list[dict] = []
    for index, sl in enumerate(pres.get("slides", []), start=1):
        if slide_ids is not None and sl["objectId"] not in slide_ids:
            continue
        for el in sl.get("pageElements", []):
            chart = el.get("sheetsChart")
            if not chart:
                continue
            tx = el.get("transform", {})
            size = el.get("size", {})
            out.append({
                "id": el["objectId"],
                "slide": index,
                "slide_id": sl["objectId"],
                "spreadsheet_id": chart.get("spreadsheetId"),
                "chart_id": chart.get("chartId"),
                "linked": True,  # an unlinked chart is an image element, not a sheetsChart
                "x": round(emu_to_pt(tx.get("translateX", 0)), 1),
                "y": round(emu_to_pt(tx.get("translateY", 0)), 1),
                "w": round(emu_to_pt(size.get("width", {}).get("magnitude", 0)) * tx.get("scaleX", 1), 1),
                "h": round(emu_to_pt(size.get("height", {}).get("magnitude", 0)) * tx.get("scaleY", 1), 1),
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{chart.get('spreadsheetId')}/edit",
            })
    return out


@mcp.tool(annotations=ADDITIVE)
def insert_sheets_chart(
    presentation: str,
    slide: str,
    spreadsheet: str,
    chart_id: int,
    x_pt: float,
    y_pt: float,
    width_pt: float,
    height_pt: float,
    linked: bool = True,
    object_id: str | None = None,
) -> dict:
    """Embed a chart that lives in a Google Sheets spreadsheet on a slide.

    Build the chart in the spreadsheet first (a Sheets MCP ``manage_chart``
    returns its ``chart_id``), then place it here. ``linked=True`` keeps the
    element bound to the spreadsheet: data or style changed there appear on
    the slide after ``refresh_sheets_charts`` (or a click on the slide's
    « Mettre à jour » chip). ``linked=False`` inserts a snapshot image that
    never changes.

    Args:
        slide: 1-based index or objectId.
        spreadsheet: spreadsheet id or full Google Sheets URL.
        chart_id: the chart's id in that spreadsheet (from the Sheets MCP
            ``manage_chart list``).
        x_pt, y_pt, width_pt, height_pt: box on the slide, in points; the
            chart is scaled to fit it.
        linked: keep the link to the spreadsheet (default) or flatten to an image.
        object_id: optional custom element id (≥ 5 chars).

    Returns: ``{element_id, slide_id, spreadsheet_id, chart_id, linked}``.

    Example::

        insert_sheets_chart(deck, 4, "https://docs.google.com/spreadsheets/d/…", 1234567890,
                            x_pt=40, y_pt=80, width_pt=640, height_pt=300)
    """
    validate_object_id(object_id)
    pid = parse_pres_id(presentation)
    sid_sheet = parse_sheet_id(spreadsheet)
    svc = slide_service()
    slide_id = resolve_slide_ids(svc, pid, [slide])[0]
    req: dict = {
        "spreadsheetId": sid_sheet,
        "chartId": int(chart_id),
        "linkingMode": "LINKED" if linked else "NOT_LINKED_IMAGE",
        "elementProperties": {
            "pageObjectId": slide_id,
            "size": {"width": {"magnitude": pt_to_emu(width_pt), "unit": "EMU"},
                     "height": {"magnitude": pt_to_emu(height_pt), "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": pt_to_emu(x_pt), "translateY": pt_to_emu(y_pt), "unit": "EMU"},
        },
    }
    if object_id:
        req["objectId"] = object_id
    resp = svc.presentations().batchUpdate(presentationId=pid, body={"requests": [{"createSheetsChart": req}]}).execute(num_retries=5)
    replies = resp.get("replies") or [{}]
    element_id = object_id or replies[0].get("createSheetsChart", {}).get("objectId")
    return {"element_id": element_id, "slide_id": slide_id, "spreadsheet_id": sid_sheet, "chart_id": int(chart_id), "linked": bool(linked)}


@mcp.tool(annotations=READ_ONLY)
def list_sheets_charts(presentation: str, slide: str | None = None) -> dict:
    """The linked Sheets charts of a deck (or of one slide): where each one sits
    and which spreadsheet chart it follows.

    Unlinked charts are ordinary images and are not listed.

    Returns: ``{charts: [{id, slide, slide_id, spreadsheet_id, chart_id, x, y, w, h, spreadsheet_url}]}``.
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    only = None
    if slide is not None:
        only = set(resolve_slide_ids(svc, pid, [slide]))
    return {"charts": _chart_elements(pres, only)}


@mcp.tool(annotations=IDEMPOTENT)
def refresh_sheets_charts(presentation: str, slide: str | None = None, element_ids: list[str] | None = None) -> dict:
    """Refresh linked Sheets charts so the slides show the spreadsheet's current data
    and style. Whole deck by default, or one slide, or the given elements.

    Returns: ``{refreshed: [element ids], count}``.
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    if element_ids:
        ids = [str(i) for i in element_ids]
    else:
        pres = svc.presentations().get(presentationId=pid).execute()
        only = set(resolve_slide_ids(svc, pid, [slide])) if slide is not None else None
        ids = [c["id"] for c in _chart_elements(pres, only)]
    if ids:
        svc.presentations().batchUpdate(presentationId=pid, body={"requests": [{"refreshSheetsChart": {"objectId": i}} for i in ids]}).execute(num_retries=5)
    return {"refreshed": ids, "count": len(ids)}
