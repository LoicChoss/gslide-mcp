"""sync_table: an existing table follows a spreadsheet range, cell by cell, in place."""

import pytest

from conftest import cell, grid_response
from gslides_mcp.tools import sync
from test_refill import BARLOW, GREEN, RED, _shape, _table

RANGE = "'Données'!A1:C4"


def _src(rows):
    return grid_response([[cell(v) for v in row] for row in rows])


@pytest.fixture
def deck(fake_slides, pres, fake_sheets):
    pres["slides"][2]["pageElements"] = [
        _table("tbl_b", [
            [("Régie", BARLOW), ("Dépenses", BARLOW), ("vs N-1", BARLOW)],
            [("Google", {}), ("46 811 €", {"fontSize": {"magnitude": 9, "unit": "PT"}}), ("+52 %", {**BARLOW, "foregroundColor": GREEN})],
            [("Meta", {}), ("12 000 €", {"fontSize": {"magnitude": 9, "unit": "PT"}}), ("-8 %", {**BARLOW, "foregroundColor": RED})],
            [("Bing", {}), None, None],
        ]),
        _shape("kpi_val", "12 400"),
    ]
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Google", "50 000 €", "-7 %"],
                                         ["Meta", "12 000 €", "-8 %"], ["Bing", "900 €", "+2 %"]])
    return fake_slides


def _cells_written(batch):
    return sorted({(r["insertText"]["cellLocation"]["rowIndex"], r["insertText"]["cellLocation"]["columnIndex"])
                   for r in batch if "insertText" in r})


def test_only_changed_cells_are_written_in_one_batch_with_their_style(deck, fake_sheets):
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE)
    (batch,) = deck.batches
    assert _cells_written(batch) == [(1, 1), (1, 2), (3, 1), (3, 2)]
    styles = {(r["updateTextStyle"]["cellLocation"]["rowIndex"], r["updateTextStyle"]["cellLocation"]["columnIndex"]):
              r["updateTextStyle"]["style"] for r in batch if "updateTextStyle" in r}
    assert styles[(1, 2)]["foregroundColor"] == RED       # +52 % → -7 %: the table's colour for a minus
    assert styles[(3, 2)]["foregroundColor"] == GREEN     # empty cell of the vs N-1 column: style borrowed, green
    assert styles[(1, 1)] == {"fontSize": {"magnitude": 9, "unit": "PT"}}
    assert out["changed"] == 4 and out["dimensions"] == {"table": [4, 3], "range": [4, 3]} and "notes" not in out
    assert {"row": 1, "column": 1, "old": "46 811 €", "new": "50 000 €"} in out["changes"]
    assert fake_sheets.calls[0]["ranges"] == [RANGE]


def test_dry_run_reports_without_writing(deck):
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, dry_run=True)
    assert deck.batches == [] and out["dry_run"] is True and out["changed"] == 4


def test_an_unchanged_table_sends_nothing(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Google", "46 811 €", "+52 %"],
                                         ["Meta", "12 000 €", "-8 %"], ["Bing", "", ""]])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE)
    assert deck.batches == [] and out["changed"] == 0


def test_dimension_mismatch_with_keep_is_reported(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1", "Clics"], ["Google", "46 811 €", "+52 %", "4 530"]])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE)
    notes = " ".join(out["notes"])
    assert "rows 2–3" in notes and "keep their old text" in notes  # the range is shorter than the table
    assert "column 3" in notes and "left out" in notes             # and wider
    assert out["dimensions"] == {"table": [4, 3], "range": [2, 4]}


def test_row_height_is_applied_to_every_row(deck):
    sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, row_height_pt=26)
    heights = [r["updateTableRowProperties"] for r in deck.batches[0] if "updateTableRowProperties" in r]
    assert heights == [{"objectId": "tbl_b", "rowIndices": [0, 1, 2, 3],
                        "tableRowProperties": {"minRowHeight": {"magnitude": 26, "unit": "PT"}}, "fields": "minRowHeight"}]


@pytest.mark.parametrize("kw, match", [
    ({"table": "kpi_val"}, "not a table"),
    ({"table": "nope"}, "not found"),
    ({"style": "comic"}, "style"),
    ({"rows": "grow"}, "rows"),
    ({"columns": "grow"}, "columns"),
])
def test_refusals_come_before_any_write(deck, kw, match):
    args = {"table": "tbl_b", **kw}
    with pytest.raises(ValueError, match=match):
        sync.sync_table("PRES1", args.pop("table"), "SHEET1", RANGE, **args)
    assert deck.batches == []
