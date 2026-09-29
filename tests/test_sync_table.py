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


# --- style="sheets" / "charter" ---------------------------------------------------------------

NAVY = {"red": 0.0, "green": 0.169, "blue": 0.235}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


def _for_cell(batch, kind, r, c):
    return [q[kind] for q in batch if kind in q
            and q[kind].get("cellLocation", q[kind].get("tableRange", {}).get("location")) == {"rowIndex": r, "columnIndex": c}]


def test_sheets_style_copies_the_source_formatting(deck, fake_sheets):
    fake_sheets.responses[RANGE] = grid_response([
        [cell("Régie", fill=NAVY, color=WHITE, bold=True, h="CENTER"), cell("Dépenses"), cell("vs N-1")],
        [cell("Google"), cell("50 000 €", number=50000), cell("-7 %", number=-0.07)],
    ])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, style="sheets")
    (batch,) = deck.batches
    (fill,) = _for_cell(batch, "updateTableCellProperties", 0, 0)
    assert fill["tableCellProperties"]["tableCellBackgroundFill"]["solidFill"]["color"]["rgbColor"] == NAVY
    (text,) = _for_cell(batch, "updateTextStyle", 0, 0)
    assert text["style"]["bold"] is True and text["style"]["foregroundColor"]["opaqueColor"]["rgbColor"] == WHITE
    assert text["style"]["fontFamily"] == "Arial" and text["style"]["fontSize"] == {"magnitude": 10, "unit": "PT"}
    assert _for_cell(batch, "updateParagraphStyle", 0, 0)[0]["style"] == {"alignment": "CENTER"}
    assert _for_cell(batch, "updateParagraphStyle", 1, 1)[0]["style"] == {"alignment": "END"}  # a number, general
    assert _for_cell(batch, "updateParagraphStyle", 1, 0)[0]["style"] == {"alignment": "START"}
    # only the overlap is touched: the table's rows 2-3 are left alone
    assert not _for_cell(batch, "updateTextStyle", 2, 0)
    assert out["style"] == "sheets" and out["changed"] == 2


def test_charter_style_applies_the_table_component_look(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Google", "50 000 €", "-7 %"],
                                         ["Meta", "12 000 €", "-8 %"], ["Bing", "", "+2 %"]])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, style="charter", charter={"header_fill": "ink", "total_row": True})
    (batch,) = deck.batches
    kinds = {next(iter(q)) for q in batch}
    assert "createTable" not in kinds and "updateTableColumnProperties" not in kinds and "updateTableRowProperties" not in kinds
    assert all(q[next(iter(q))]["objectId"] == "tbl_b" for q in batch)
    assert any(q["insertText"]["text"] == "–" for q in batch if "insertText" in q)  # empty cell → na_text
    header = [q["updateTableCellProperties"] for q in batch if "updateTableCellProperties" in q
              and q["updateTableCellProperties"]["tableRange"]["location"] == {"rowIndex": 0, "columnIndex": 0}]
    assert header  # the header row gets its fill
    assert out["style"] == "charter"


def test_charter_refuses_props_that_would_add_elements(deck):
    with pytest.raises(ValueError, match="icons"):
        sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, style="charter", charter={"icons": ["search"]})
    assert deck.batches == []


# --- rows="fit" ----------------------------------------------------------------------------

PT = 12700


def _kinds(batch):
    return [next(iter(q)) for q in batch]


def test_fit_adds_rows_below_the_last_data_row_then_writes_them(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Google", "46 811 €", "+52 %"],
                                         ["Meta", "12 000 €", "-8 %"], ["Bing", "900 €", "+2 %"],
                                         ["Pinterest", "300 €", "+1 %"], ["Total", "60 011 €", "+30 %"]])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, rows="fit")
    (batch,) = deck.batches
    assert batch[0] == {"insertTableRows": {"tableObjectId": "tbl_b", "cellLocation": {"rowIndex": 2},
                                            "insertBelow": True, "number": 2}}
    written = _cells_written(batch)
    assert (3, 0) in written and (4, 0) in written and (5, 0) in written  # new rows, then the old last row moved down
    assert {"row": 5, "column": 0, "old": "Bing", "new": "Total"} in out["changes"]
    assert any("2 rows added below row 2" in n for n in out["notes"])
    assert out["dimensions"] == {"table": [4, 3], "range": [6, 3]}


def test_fit_removes_rows_before_the_last_row(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Google", "46 811 €", "+52 %"],
                                         ["Total", "46 811 €", "+52 %"]])
    out = sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, rows="fit")
    (batch,) = deck.batches
    assert batch[0] == {"deleteTableRow": {"tableObjectId": "tbl_b", "cellLocation": {"rowIndex": 2}}}
    assert _kinds(batch).count("deleteTableRow") == 1
    assert {"row": 2, "column": 0, "old": "Bing", "new": "Total"} in out["changes"]


def test_fit_moves_the_components_own_elements_under_the_table(fake_slides, pres, fake_sheets):
    tbl = _table("yt_top_table_1", [[("Nom", {}), ("A", {})], [("Vues", {}), ("1", {})], [("CTR", {}), ("2", {})]])
    tbl["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 40 * PT, "unit": "EMU"}
    for row in tbl["table"]["tableRows"]:
        row["rowHeight"] = {"magnitude": 26 * PT, "unit": "EMU"}
    note, other = _shape("yt_top_top_note_1", "Top annonce"), _shape("free_text", "Analyse")
    for el, y in ((note, 130), (other, 140)):
        el["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": y * PT, "unit": "EMU"}
    pres["slides"][2]["pageElements"] = [tbl, note, other]
    fake_sheets.responses[RANGE] = _src([["Nom", "A"], ["Vues", "1"], ["Clics", "5"], ["CTR", "2"]])
    out = sync.sync_table("PRES1", "yt_top_table_1", "SHEET1", RANGE, rows="fit")
    (batch,) = fake_slides.batches
    moves = [q["updatePageElementTransform"] for q in batch if "updatePageElementTransform" in q]
    assert moves == [{"objectId": "yt_top_top_note_1", "applyMode": "RELATIVE",
                      "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 26 * PT, "unit": "EMU"}}]
    assert any("free_text" in n and "overlap_check" in n for n in out["notes"])


def test_fit_refuses_to_drop_the_header_or_a_merge(deck, fake_sheets, pres):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"]])
    with pytest.raises(ValueError, match="header and one row"):
        sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, rows="fit")
    pres["slides"][2]["pageElements"][0]["table"]["tableRows"][1]["tableCells"][0]["rowSpan"] = 2
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1"], ["Total", "1", "+1 %"]])
    with pytest.raises(ValueError, match="merged"):
        sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, rows="fit")
    assert deck.batches == []


# --- columns="fit" and image slots --------------------------------------------------------

from test_images import _image  # noqa: E402


@pytest.fixture
def board(fake_slides, pres, fake_sheets, monkeypatch):
    """A named scoreboard: label column 76 pt + two ads of 262 pt, image row 1, two slots."""
    import gslides_mcp.assets as assets_mod

    tbl = _table("yt_top_table_1", [[("Nom", {}), ("Vidéo", {}), ("Bumper", {})],
                                    [("Visuel", {}), (" ", {}), (" ", {})],
                                    [("Vues", {}), ("12 400", {}), ("8 950", {})]])
    tbl["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": 40 * PT, "translateY": 40 * PT, "unit": "EMU"}
    tbl["table"]["tableColumns"] = [{"columnWidth": {"magnitude": w * PT, "unit": "EMU"}} for w in (76, 262, 262)]
    for row, h in zip(tbl["table"]["tableRows"], (26, 64, 26)):
        row["rowHeight"] = {"magnitude": h * PT, "unit": "EMU"}
    shown = _image("yt_top_slot_1", 120 + (254 - 99.6) / 2, 70, 99.6, 56, description="slot:120.0,70.0,254.0,56.0")
    empty = _image("yt_top_slot_2", 386, 70, 254, 56, base=(6400, 6400), description="slot:386.0,70.0,254.0,56.0")
    pres["slides"][2]["pageElements"] = [tbl, shown, empty]
    monkeypatch.setattr(assets_mod, "ensure_asset", lambda ref, tint=None: "fid_" + ref)
    return fake_slides


def _transform(batch, oid):
    return [q["updatePageElementTransform"]["transform"] for q in batch
            if "updatePageElementTransform" in q and q["updatePageElementTransform"]["objectId"] == oid]


def test_fit_columns_adds_a_column_shares_the_width_and_adds_a_slot(board, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Nom", "Vidéo", "Bumper", "Démo"], ["Visuel", "", "", ""], ["Vues", "12 400", "8 950", "3 210"]])
    out = sync.sync_table("PRES1", "yt_top_table_1", "SHEET1", RANGE, columns="fit")
    (batch,) = board.batches
    assert batch[0] == {"insertTableColumns": {"tableObjectId": "yt_top_table_1", "cellLocation": {"columnIndex": 2},
                                               "insertRight": True, "number": 1}}
    widths = [q["updateTableColumnProperties"]["tableColumnProperties"]["columnWidth"]["magnitude"] / PT
              for q in batch if "updateTableColumnProperties" in q]
    assert widths == pytest.approx([76, 174.667, 174.667, 174.667], abs=0.01)
    # the picture keeps its aspect, centred in its narrower frame
    (t1,) = _transform(batch, "yt_top_slot_1")
    assert t1["translateX"] / PT == pytest.approx(120 + (166.667 - 99.6) / 2, abs=0.05)
    assert t1["scaleX"] * 49000 / PT == pytest.approx(99.6, abs=0.05)
    # the empty slot fills its new frame
    (t2,) = _transform(batch, "yt_top_slot_2")
    assert t2["translateX"] / PT == pytest.approx(40 + 76 + 174.667 + 4, abs=0.05)
    (new,) = [q["createImage"] for q in batch if "createImage" in q]
    assert new["objectId"] == "yt_top_slot_3" and "slot:" in new["url"]
    alts = {q["updatePageElementAltText"]["objectId"] for q in batch if "updatePageElementAltText" in q}
    assert alts == {"yt_top_slot_1", "yt_top_slot_2", "yt_top_slot_3"}
    # slot 2 filled its frame and the frame changes shape: its picture is fitted again (crop), not stretched
    swaps = {q["replaceImage"]["imageObjectId"]: q["replaceImage"] for q in batch if "replaceImage" in q}
    assert swaps["yt_top_slot_2"] == {"imageObjectId": "yt_top_slot_2", "url": "https://x/old.png", "imageReplaceMethod": "CENTER_CROP"}
    assert "yt_top_slot_1" not in swaps  # a picture shrunk inside its frame just moves
    assert {"row": 2, "column": 3, "old": "", "new": "3 210"} in out["changes"]
    assert "image slots: 2 realigned, 1 added, 0 removed" in out["notes"]


def test_fit_columns_removes_the_last_column_and_its_slot(board, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Nom", "Vidéo"], ["Visuel", ""], ["Vues", "12 400"]])
    sync.sync_table("PRES1", "yt_top_table_1", "SHEET1", RANGE, columns="fit")
    (batch,) = board.batches
    assert batch[0] == {"deleteTableColumn": {"tableObjectId": "yt_top_table_1", "cellLocation": {"columnIndex": 2}}}
    assert {"deleteObject": {"objectId": "yt_top_slot_2"}} in batch
    (t1,) = _transform(batch, "yt_top_slot_1")
    assert t1["translateX"] / PT == pytest.approx(120 + (516 - 99.6) / 2, abs=0.05)


def test_fit_columns_needs_a_named_table(deck, fake_sheets):
    fake_sheets.responses[RANGE] = _src([["Régie", "Dépenses", "vs N-1", "Clics"], ["Google", "1", "+1 %", "2"]])
    with pytest.raises(ValueError, match="named table"):
        sync.sync_table("PRES1", "tbl_b", "SHEET1", RANGE, columns="fit")
    assert deck.batches == []


def test_an_empty_slot_gets_a_placeholder_of_its_new_shape(board, fake_sheets, fake_drive, pres):
    slot2 = pres["slides"][2]["pageElements"][2]
    slot2["image"]["sourceUrl"] = "https://drive.google.com/uc?export=view&id=ph_old"
    fake_drive.store_files.append({"id": "ph_old", "name": "slot-1016x224-f2f4f4-c8d0d0.png", "mimeType": "image/png", "parents": []})
    fake_sheets.responses[RANGE] = _src([["Nom", "Vidéo", "Bumper", "Démo"], ["Visuel", "", "", ""], ["Vues", "1", "2", "3"]])
    sync.sync_table("PRES1", "yt_top_table_1", "SHEET1", RANGE, columns="fit")
    swaps = {q["replaceImage"]["imageObjectId"]: q["replaceImage"] for q in board.batches[0] if "replaceImage" in q}
    assert swaps["yt_top_slot_2"]["url"].startswith("https://drive.google.com/uc?export=view&id=fid_slot:667x224:")
