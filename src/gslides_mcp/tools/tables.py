"""Table tools: create_table, edit_table, set_table_cell.

Cells are addressed 0-based ``(row, column)``. Text goes through the same
markdown writer as ``write_text_markdown`` with a ``cellLocation`` on every
request; new tables and empty cells get insertText only, never deleteText.
"""

from __future__ import annotations

import uuid

from ..app import ADDITIVE, DESTRUCTIVE, IDEMPOTENT, mcp
from ..auth import slide_service
from ..util import (
    PT_TO_EMU,
    find_element,
    md_requests,
    parse_pres_id,
    resolve_slide_ids,
    validate_object_id,
)

_MAX_DIM = 20  # Slides API: at most 20x20 at creation (rows/columns can be added later)
_ACTIONS = ("insert_rows", "insert_columns", "delete_row", "delete_column")


def _element_properties(page_id: str, x_pt: float, y_pt: float,
                        width_pt: float, height_pt: float) -> dict:
    return {
        "pageObjectId": page_id,
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
    }


@mcp.tool(annotations=ADDITIVE)
def create_table(
    presentation: str,
    slide: str,
    rows: int,
    columns: int,
    x_pt: float,
    y_pt: float,
    width_pt: float,
    height_pt: float,
    data: list[list[str]] | None = None,
    object_id: str | None = None,
) -> dict:
    """Create a table on a slide, optionally pre-filled — one batchUpdate.

    Args:
        slide: 1-based index or objectId.
        rows, columns: 1..20 each (Slides API limit at creation; grow it
            afterwards with ``edit_table``).
        x_pt, y_pt, width_pt, height_pt: geometry in points.
        data: list of rows, each a list of cell strings (plain text). Ragged
            rows are fine; empty strings are skipped. Must fit the grid.
        object_id: optional custom objectId (5–50 chars, ``[A-Za-z0-9_-]``).

    Returns: ``{table_id, slide_id, rows, columns, cells_written}``.

    Example::

        create_table(deck, 4, rows=3, columns=2, x_pt=40, y_pt=120,
                     width_pt=640, height_pt=150,
                     data=[["KPI", "Valeur"], ["Sessions", "12 400"], ["CTR", "3,2 %"]])
    """
    validate_object_id(object_id)
    if not (1 <= rows <= _MAX_DIM and 1 <= columns <= _MAX_DIM):
        raise ValueError(
            f"rows and columns must each be 1..{_MAX_DIM} at creation "
            f"(Slides API limit), got {rows}x{columns}"
        )
    cells: list[tuple[int, int, str]] = []
    for r, row in enumerate(data or []):
        if r >= rows:
            raise ValueError(f"data has row {r} but the table has only {rows} rows")
        for c, value in enumerate(row):
            if c >= columns:
                raise ValueError(
                    f"data row {r} has column {c} but the table has only {columns} columns"
                )
            if value is None or str(value) == "":
                continue
            cells.append((r, c, str(value)))

    pid = parse_pres_id(presentation)
    svc = slide_service()
    sid = resolve_slide_ids(svc, pid, [slide])[0]
    table_id = object_id or f"tbl_{uuid.uuid4().hex[:10]}"
    reqs: list[dict] = [{"createTable": {
        "objectId": table_id,
        "elementProperties": _element_properties(sid, x_pt, y_pt, width_pt, height_pt),
        "rows": rows,
        "columns": columns,
    }}]
    for r, c, value in cells:
        reqs.append({"insertText": {
            "objectId": table_id,
            "cellLocation": {"rowIndex": r, "columnIndex": c},
            "text": value,
            "insertionIndex": 0,
        }})
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": reqs}
    ).execute()
    return {
        "table_id": table_id, "slide_id": sid,
        "rows": rows, "columns": columns, "cells_written": len(cells),
    }


@mcp.tool(annotations=DESTRUCTIVE)
def edit_table(
    presentation: str,
    table_id: str,
    action: str,
    index: int | None = None,
    count: int = 1,
    position: str = "after",
) -> dict:
    """Insert or delete rows/columns of an existing table.

    Args:
        action: ``insert_rows`` | ``insert_columns`` | ``delete_row`` |
            ``delete_column``.
        index: 0-based row (or column) the action is anchored on. Required.
        count: how many rows/columns to insert or delete (default 1).
        position: for inserts, ``after`` (default) or ``before`` ``index``.

    Deletes are sent as ``count`` requests on the same ``index``: after each
    deletion the following rows/columns shift down by one, so deleting rows
    1..3 is "delete row 1, three times". Keep that in mind if you chain
    several ``edit_table`` calls — re-read the table between them.

    Returns: ``{table_id, action, index, count, position}``.

    Example: ``edit_table(deck, "tbl_1", "insert_rows", index=0, count=2)``
    """
    if action not in _ACTIONS:
        raise ValueError(f"action must be one of {', '.join(_ACTIONS)}, got {action!r}")
    if index is None:
        raise ValueError("index is required: the 0-based row or column to act on")
    if position not in ("after", "before"):
        raise ValueError(f"position must be 'after' or 'before', got {position!r}")
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")

    if action == "insert_rows":
        reqs = [{"insertTableRows": {
            "tableObjectId": table_id, "cellLocation": {"rowIndex": index},
            "insertBelow": position == "after", "number": count,
        }}]
    elif action == "insert_columns":
        reqs = [{"insertTableColumns": {
            "tableObjectId": table_id, "cellLocation": {"columnIndex": index},
            "insertRight": position == "after", "number": count,
        }}]
    elif action == "delete_row":
        reqs = [{"deleteTableRow": {
            "tableObjectId": table_id, "cellLocation": {"rowIndex": index},
        }}] * count
    else:
        reqs = [{"deleteTableColumn": {
            "tableObjectId": table_id, "cellLocation": {"columnIndex": index},
        }}] * count

    pid = parse_pres_id(presentation)
    slide_service().presentations().batchUpdate(
        presentationId=pid, body={"requests": reqs}
    ).execute()
    return {"table_id": table_id, "action": action, "index": index,
            "count": count, "position": position}


def _cell_has_text(table: dict, row: int, column: int) -> bool:
    try:
        cell = table["tableRows"][row]["tableCells"][column]
    except (KeyError, IndexError):
        return False  # merged-away or not materialised: nothing to delete
    return any(
        te.get("textRun", {}).get("content", "") not in ("", "\n")
        for te in cell.get("text", {}).get("textElements", [])
    )


@mcp.tool(annotations=IDEMPOTENT)
def set_table_cell(presentation: str, table_id: str, row: int, column: int, markdown: str) -> dict:
    """Write markdown into one table cell (bold, italic, bullets).

    Same writer as ``write_text_markdown``. Existing cell text is cleared in
    the same batch; the clear is skipped on empty cells, where a deleteText
    would fail the batch.

    The writer resets the cell's text style (font, size, colour) to the
    table's defaults: fine in a table you just made, wrong in a designed
    one. To refill cells of an existing table and keep their look (and
    colour « vs N-1 » values by sign), use ``refill_text``.

    Args:
        row, column: 0-based cell coordinates.

    Returns: ``{table_id, row, column, content_length}``.

    Example: ``set_table_cell(deck, "tbl_1", 1, 1, "**12 400** (+8 %)")``
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    el, _slide = find_element(pres, table_id)
    if el is None:
        raise ValueError(f"element not found: {table_id!r}")
    table = el.get("table")
    if table is None:
        raise ValueError(f"{table_id!r} is not a table (use find_elements with type='table')")
    n_rows, n_cols = table.get("rows", 0), table.get("columns", 0)
    if not (0 <= row < n_rows and 0 <= column < n_cols):
        raise ValueError(
            f"cell ({row}, {column}) is outside table {table_id} ({n_rows}x{n_cols}, 0-based)"
        )

    reqs: list[dict] = []
    if _cell_has_text(table, row, column):
        reqs.append({"deleteText": {
            "objectId": table_id,
            "cellLocation": {"rowIndex": row, "columnIndex": column},
            "textRange": {"type": "ALL"},
        }})
    reqs.extend(md_requests(table_id, markdown, cell=(row, column)))
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": reqs}
    ).execute()
    return {"table_id": table_id, "row": row, "column": column, "content_length": len(markdown)}
