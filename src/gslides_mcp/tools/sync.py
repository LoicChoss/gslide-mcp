"""Bilan sync: slide tables that follow a spreadsheet range (``sync_table``).

The spreadsheet is read with its formatting (``sheets_source``) and mapped
cell by cell onto an existing table: only cells whose text changed are
written, through ``refill``'s planner, so each keeps its style and
variation cells take the colour of their sign. The table keeps its id,
place and look; the deck needs no re-insertion month after month.
"""

from __future__ import annotations

import builtins

from .. import sheets_source
from ..app import IDEMPOTENT, mcp
from ..auth import slide_service
from ..util import find_element, parse_pres_id
from . import refill

_STYLES = ("slides",)
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


def plan_table_sync(pres: dict, table_id: str, src: dict, style: str = "slides") -> tuple[list[dict], dict]:
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
    report: dict = {"table": table_id, "changed": len(changes), "changes": changes,
                    "dimensions": {"table": [n_r, n_c], "range": [s_r, s_c]}}
    notes = _dimension_notes(n_r, n_c, s_r, s_c)
    if notes:
        report["notes"] = notes
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
) -> dict:
    """Bring an existing table in line with a spreadsheet range — in place, one batch.

    For a bilan whose tables live in a spreadsheet: instead of deleting and
    inserting the table again every month, each cell whose displayed value
    changed is rewritten; the table keeps its id, place and look.
    ``style="slides"`` keeps each cell's style (font, weight, size, colour,
    alignment, as ``refill_text``) and colours variation cells (« vs N-1 »,
    signed values) by their sign.

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
    reqs, report = plan_table_sync(pres, table, src, style)
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

