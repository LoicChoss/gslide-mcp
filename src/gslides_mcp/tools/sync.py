"""Bilan sync: slide tables that follow a spreadsheet range (``sync_table``).

The spreadsheet is read with its formatting (``sheets_source``) and mapped
cell by cell onto an existing table: only cells whose text changed are
written, through ``refill``'s planner, so each keeps its style and
variation cells take the colour of their sign. The table keeps its id,
place and look; the deck needs no re-insertion month after month.
"""

from __future__ import annotations

import builtins

from .. import components, sheets_source, themes
from .. import draw as drawing
from ..app import IDEMPOTENT, mcp
from ..auth import slide_service
from ..util import PT_TO_EMU, find_element, parse_pres_id
from . import refill

_STYLES = ("slides", "sheets", "charter")
# charter props that would add elements or change the table's geometry: not for a table that stays
_CHARTER_REFUSED = ("rows", "icons", "dots", "subs", "pill_cols", "col_w", "row_h", "row_heights", "icon_w", "icon_tint")
_STYLE_KINDS = ("updateTableCellProperties", "updateTextStyle", "updateParagraphStyle", "updateTableBorderProperties")
_ROWS = ("keep",)
_COLUMNS = ("keep",)


def _span(first: int, last: int, noun: str) -> str:
    return f"{noun} {first}" if first == last else f"{noun}s {first}–{last}"


def _dimension_notes(n_r: int, n_c: int, s_r: int, s_c: int) -> list[str]:
    notes = []
    if s_r > n_r:
        notes.append(f"range {_span(n_r, s_r - 1, 'row')} left out: the table has {n_r} rows (rows='fit' adds them)")
    elif s_r < n_r:
        notes.append(f"table {_span(s_r, n_r - 1, 'row')} keep their old text: the range has {s_r} rows "
                     "(rows='fit' removes them)")
    if s_c > n_c:
        notes.append(f"range {_span(n_c, s_c - 1, 'column')} left out: the table has {n_c} columns")
    elif s_c < n_c:
        notes.append(f"table {_span(s_c, n_c - 1, 'column')} keep their old text: the range has {s_c} columns")
    return notes


def _loc(r: int, c: int) -> dict:
    return {"cellLocation": {"rowIndex": r, "columnIndex": c}}


def _write_texts(table_id: str, table: dict, targets: dict, covered: dict) -> tuple[list[dict], list[dict]]:
    """deleteText / insertText for the cells whose text differs; empty cells get a space so they can be styled."""
    reqs, changes = [], []
    for (r, c), new in sorted(targets.items()):
        if (r, c) in covered:
            continue
        text = refill._cell_text(table, r, c) or {}
        old = refill._plain(text)
        changed = new.strip() != old
        if not changed and refill.has_text(text):  # a styled space counts as text
            continue
        if refill.has_text(text):
            reqs.append({"deleteText": {"objectId": table_id, **_loc(r, c), "textRange": {"type": "ALL"}}})
        reqs.append({"insertText": {"objectId": table_id, **_loc(r, c), "text": new if new.strip() else " ",
                                    "insertionIndex": 0}})
        if changed:
            changes.append({"row": r, "column": c, "old": old, "new": new})
    return reqs, changes


def _sheets_style(table_id: str, cells: dict, covered: dict) -> list[dict]:
    """The source's own formatting, cell by cell: fill, vertical alignment, text style, horizontal alignment."""
    reqs = []
    for (r, c), cell in sorted(cells.items()):
        if (r, c) in covered:
            continue
        props, fields = {}, []
        if cell["fill"] is not None:
            props["tableCellBackgroundFill"] = {"solidFill": {"color": {"rgbColor": cell["fill"]}}}
            fields.append("tableCellBackgroundFill.solidFill.color")
        if cell["v_align"]:
            props["contentAlignment"] = cell["v_align"]
            fields.append("contentAlignment")
        if fields:
            reqs.append({"updateTableCellProperties": {
                "objectId": table_id, "tableRange": {"location": {"rowIndex": r, "columnIndex": c}, "rowSpan": 1, "columnSpan": 1},
                "tableCellProperties": props, "fields": ",".join(fields)}})
        style = {k: bool(cell[k]) for k in ("bold", "italic", "underline", "strikethrough")}
        if cell["font"]:
            style["fontFamily"] = cell["font"]
        if cell["size"]:
            style["fontSize"] = {"magnitude": cell["size"], "unit": "PT"}
        if cell["color"] is not None:
            style["foregroundColor"] = {"opaqueColor": {"rgbColor": cell["color"]}}
        reqs.append({"updateTextStyle": {"objectId": table_id, **_loc(r, c), "textRange": {"type": "ALL"},
                                         "style": style, "fields": ",".join(style)}})
        reqs.append({"updateParagraphStyle": {"objectId": table_id, **_loc(r, c), "textRange": {"type": "ALL"},
                                              "style": {"alignment": cell["h_align"]}, "fields": "alignment"}})
    return reqs


def _charter_style(el: dict, texts: list[list[str]], charter: dict | None) -> tuple[list[list[str]], list[dict]]:
    """The ``table`` component's look applied to an existing table: its texts (``na_text`` applied) and style requests."""
    table_id = el["objectId"]
    bad = sorted(k for k in (charter or {}) if k in _CHARTER_REFUSED)
    if bad:
        raise ValueError(f"charter props {bad} add elements or change the geometry: not available on a table that stays")
    theme = themes.load(refill.DEFAULT_THEME)
    width = sum(col.get("columnWidth", {}).get("magnitude", 0) for col in el["table"].get("tableColumns", [])) / PT_TO_EMU
    ops, _h = components.render("table", {**(charter or {}), "rows": texts}, theme, width or 400.0, None)
    top = next(o for o in ops if o["op"] == "table")
    reqs, _ids = drawing.ops_to_requests("page", [top], theme, prefix="charter")
    kept = []
    for r in reqs:
        (kind, payload), = r.items()
        if kind in _STYLE_KINDS:
            kept.append({kind: {**payload, "objectId": table_id}})
    return [[str(v) for v in row] for row in top["rows"]], kept


def plan_table_sync(pres: dict, table_id: str, src: dict, style: str = "slides",
                    charter: dict | None = None) -> tuple[list[dict], dict]:
    """Requests and report to bring table ``table_id`` in line with ``src`` (``read_cells``); nothing is sent."""
    el, _slide = find_element(pres, table_id)
    if el is None:
        raise ValueError(f"element not found: {table_id!r}")
    if "table" not in el:
        raise ValueError(f"{table_id!r} is not a table (use find_elements with type='table')")
    table = el["table"]
    n_r, n_c = table.get("rows", 0), table.get("columns", 0)
    s_rows = src["rows"]
    s_r, s_c = len(s_rows), (len(s_rows[0]) if s_rows else 0)
    covered = refill.covered_cells(table)
    report: dict = {"table": table_id, "dimensions": {"table": [n_r, n_c], "range": [s_r, s_c]}, "style": style}
    notes = _dimension_notes(n_r, n_c, s_r, s_c)
    if notes:
        report["notes"] = notes
    overlap = {(r, c): s_rows[r][c] for r in range(min(n_r, s_r)) for c in range(min(n_c, s_c))}
    if style == "sheets":
        reqs, changes = _write_texts(table_id, table, {k: v["text"] for k, v in overlap.items()}, covered)
        reqs += _sheets_style(table_id, overlap, covered)
        report.update(changed=len(changes), changes=changes)
        return reqs, report
    if style == "charter":
        texts = [[refill._plain(refill._cell_text(table, r, c)) for c in range(n_c)] for r in range(n_r)]
        for (r, c), cell in overlap.items():
            texts[r][c] = cell["text"]
        final, style_reqs = _charter_style(el, texts, charter)
        targets = {(r, c): final[r][c] for r in range(n_r) for c in range(n_c)}
        reqs, changes = _write_texts(table_id, table, targets, covered)
        reqs += [q for q in style_reqs
                 if tuple(q[next(iter(q))].get("cellLocation", {}).values()) not in covered]
        report.update(changed=len(changes), changes=changes)
        return reqs, report
    edits, changes = [], []
    for r in range(min(n_r, s_r)):
        for c in range(min(n_c, s_c)):
            if (r, c) in covered:
                continue  # its text lives in the merge's head cell
            new = s_rows[r][c]["text"]
            old = refill._plain(refill._cell_text(table, r, c))
            if new.strip() == old:
                continue
            edits.append({"element": table_id, "row": r, "column": c, "text": new})
            changes.append({"row": r, "column": c, "old": old, "new": new})
    reqs, planned = refill.plan_refill(pres, edits) if edits else ([], {})
    report.update(changed=len(changes), changes=changes)
    if planned.get("colors"):
        report["colors"] = planned["colors"]
    return reqs, report


@mcp.tool(annotations=IDEMPOTENT)
def sync_table(
    presentation: str,
    table: str,
    spreadsheet: str,
    range: str,  # noqa: A002 — the name the Sheets side uses too
    style: str = "slides",
    rows: str = "keep",
    columns: str = "keep",
    row_height_pt: float | None = None,
    dry_run: bool = False,
    charter: dict | None = None,
) -> dict:
    """Bring an existing table in line with a spreadsheet range — in place, one batch.

    For a bilan whose tables live in a spreadsheet: instead of deleting and
    inserting the table again every month, each cell whose displayed value
    changed is rewritten; the table keeps its id, place and look.
    ``style``:
        ``slides`` (default) keeps each cell's style (font, weight, size,
        colour, alignment, as ``refill_text``) and colours variation cells
        (« vs N-1 », signed values) by their sign — for a designed deck.
        ``sheets`` copies the spreadsheet's formatting cell by cell: fill,
        text colour, weight, italics, underline, font, size, alignments
        (numbers right as in Sheets) — when the look lives in the sheet
        (conditional colours).
        ``charter`` applies the ``table`` component's look (header fill,
        banding, bold first column, N-1 columns muted, variation columns
        by sign, empty cells « – »); ``charter`` props tune it
        (``{"header_fill": "ink", "total_row": true}``).

    Args:
        table: the table's element id.
        spreadsheet: id or URL. gslide-mcp only reads it.
        range: A1 with the sheet (``'Données'!A1:F8``) or a named range
            (preferred: it follows the data when rows are inserted). The
            values are read as Sheets displays them (``46 811 €``, ``+52 %``).
        rows, columns: ``keep`` — the table's size does not change; when the
            range is larger the extra rows / columns are left out, when it
            is smaller the table's extra cells keep their text; both are
            reported in ``notes`` (0-based indexes).
        row_height_pt: minimum height set on every row afterwards.
        dry_run: report what would change and write nothing.
        charter: props of the ``table`` component for ``style="charter"``
            (header, total_row, header_fill, total_fill, delta_cols,
            prev_cols, zero_cols, na_text, align, size); nothing that adds
            elements (icons, dots, subs, pills) or changes the geometry.

    Returns: ``{table, changed, changes: [{row, column, old, new}],
    dimensions: {table: [rows, cols], range: [rows, cols]}, notes?, colors?,
    dry_run?}``.

    Example: ``sync_table(deck, "yt_top_table_1", sheet_url, "bilan_youtube", dry_run=True)``
    """
    if style not in _STYLES:
        raise ValueError(f"style must be one of {', '.join(_STYLES)}, got {style!r}")
    if rows not in _ROWS:
        raise ValueError(f"rows must be one of {', '.join(_ROWS)}, got {rows!r}")
    if columns not in _COLUMNS:
        raise ValueError(f"columns must be one of {', '.join(_COLUMNS)}, got {columns!r}")
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    el, _slide = find_element(pres, table)  # fail on the deck before reading the spreadsheet
    if el is None:
        raise ValueError(f"element not found: {table!r}")
    if "table" not in el:
        raise ValueError(f"{table!r} is not a table (use find_elements with type='table')")
    src = sheets_source.read_cells(spreadsheet, range)
    reqs, report = plan_table_sync(pres, table, src, style, charter)
    if row_height_pt:
        reqs.append({"updateTableRowProperties": {
            "objectId": table, "rowIndices": list(builtins.range(el["table"].get("rows", 0))),
            "tableRowProperties": {"minRowHeight": {"magnitude": row_height_pt, "unit": "PT"}},
            "fields": "minRowHeight",
        }})
    if dry_run:
        report["dry_run"] = True
        return report
    if reqs:
        svc.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute()
    return report

