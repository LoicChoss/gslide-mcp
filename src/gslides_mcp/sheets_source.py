"""Read a spreadsheet range with its formatting — the source side of bilan sync.

gslide-mcp only reads spreadsheets (the Sheets MCP writes them): one
``spreadsheets.get`` with ``includeGridData`` on the range gives, per cell,
the value as Sheets displays it and the effective format. ``read_cells``
turns that into a rectangular grid of plain dicts that ``sync_table`` and
``sync_deck`` map onto Slides requests.

Horizontal alignment « general » resolves like Sheets: numbers and dates to
the right, text to the left. Theme colours (``set_theme periscope``) are
resolved through the spreadsheet's theme.
"""

from __future__ import annotations

import re

from .auth import sheets_service

_SHEET_URL = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")
_H = {"LEFT": "START", "CENTER": "CENTER", "RIGHT": "END"}
_V = {"TOP": "TOP", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM"}
_FIELDS = (
    "properties(spreadsheetTheme(themeColors)),"
    "sheets(properties(title,sheetId),merges,"
    "data(startRow,startColumn,rowData(values(formattedValue,effectiveValue,"
    "effectiveFormat(backgroundColor,backgroundColorStyle,textFormat,horizontalAlignment,verticalAlignment)))))"
)


def spreadsheet_id(value: str) -> str:
    """A bare spreadsheet id, or the id in a docs.google.com/spreadsheets URL."""
    m = _SHEET_URL.search(value)
    return m.group(1) if m else value.strip()


def _theme_colors(resp: dict) -> dict[str, dict]:
    theme = resp.get("properties", {}).get("spreadsheetTheme", {})
    return {c.get("colorType"): c.get("color", {}).get("rgbColor", {}) for c in theme.get("themeColors", [])}


def _rgb(style: dict | None, plain: dict | None, theme: dict[str, dict]) -> dict | None:
    """``{red, green, blue}`` (0–1, missing channels 0) from a ColorStyle, else the plain Color."""
    if style:
        if "rgbColor" in style:
            c = style["rgbColor"]
        elif "themeColor" in style:
            c = theme.get(style["themeColor"])
        else:
            c = None
    else:
        c = plain
    if c is None:
        return None
    return {k: float(c.get(k, 0.0)) for k in ("red", "green", "blue")}


def _cell(v: dict, theme: dict[str, dict]) -> dict:
    fmt = v.get("effectiveFormat", {})
    tf = fmt.get("textFormat", {})
    is_number = "numberValue" in v.get("effectiveValue", {})  # dates and times are numbers too
    return {
        "text": v.get("formattedValue", ""),
        "is_number": is_number,
        "fill": _rgb(fmt.get("backgroundColorStyle"), fmt.get("backgroundColor"), theme),
        "color": _rgb(tf.get("foregroundColorStyle"), tf.get("foregroundColor"), theme),
        "bold": bool(tf.get("bold")),
        "italic": bool(tf.get("italic")),
        "underline": bool(tf.get("underline")),
        "strikethrough": bool(tf.get("strikethrough")),
        "font": tf.get("fontFamily"),
        "size": tf.get("fontSize"),
        "h_align": _H.get(fmt.get("horizontalAlignment")) or ("END" if is_number else "START"),
        "v_align": _V.get(fmt.get("verticalAlignment")),
    }


def read_values(spreadsheet: str, ranges: list[str]) -> list[list[list[str]]]:
    """Displayed values of several ranges in one call (``values.batchGet``), in the order asked.

    Enough for texts, image sources and tables that keep the deck's look;
    ``read_cells`` adds the formats when the sheet's look is wanted.
    """
    if not ranges:
        return []
    resp = sheets_service().spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id(spreadsheet), ranges=list(ranges),
        valueRenderOption="FORMATTED_VALUE", majorDimension="ROWS",
    ).execute()
    return [[[str(v) for v in row] for row in vr.get("values", [])] for vr in resp.get("valueRanges", [])]


def as_cells(values: list[list[str]]) -> dict:
    """A ``read_values`` grid in ``read_cells``'s shape (text only), padded to the widest row."""
    width = max((len(r) for r in values), default=0)
    return {"rows": [[{"text": v} for v in r] + [{"text": ""} for _ in range(width - len(r))] for r in values],
            "merges": []}


def read_cells(spreadsheet: str, rng: str) -> dict:
    """The range's cells as ``{sheet, rows: [[cell, …], …], merges: [(r, c, rs, cs)]}``.

    ``rng`` is A1 with the sheet (``'Données'!B4:F12``) or a named range.
    Rows are padded to the widest row; trailing empty rows and columns,
    which Sheets does not return, are not data and are left out. Merges are
    given relative to the range's top-left cell.
    """
    sid = spreadsheet_id(spreadsheet)
    resp = sheets_service().spreadsheets().get(
        spreadsheetId=sid, ranges=[rng], includeGridData=True, fields=_FIELDS,
    ).execute()
    sheets = resp.get("sheets") or []
    if not sheets or not sheets[0].get("data"):
        raise ValueError(f"range {rng!r} not found in spreadsheet {sid}")
    sheet = sheets[0]
    data = sheet["data"][0]
    theme = _theme_colors(resp)
    top, left = data.get("startRow", 0), data.get("startColumn", 0)
    rows = [[_cell(v, theme) for v in row.get("values", [])] for row in data.get("rowData", [])]
    width = max((len(r) for r in rows), default=0)
    empty = _cell({}, theme)
    rows = [r + [dict(empty) for _ in range(width - len(r))] for r in rows]
    merges = []
    for m in sheet.get("merges", []):
        r, c = m.get("startRowIndex", 0) - top, m.get("startColumnIndex", 0) - left
        if 0 <= r < len(rows) and 0 <= c < width:
            merges.append((r, c, m.get("endRowIndex", 0) - m.get("startRowIndex", 0),
                           m.get("endColumnIndex", 0) - m.get("startColumnIndex", 0)))
    return {"sheet": sheet.get("properties", {}).get("title"), "rows": rows, "merges": merges}
