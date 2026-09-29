"""read_cells: a spreadsheet range as displayed values and effective formats."""

import pytest

from conftest import cell, grid_response
from gslides_mcp import sheets_source

NAVY = {"red": 0.0, "green": 0.169, "blue": 0.235}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


def test_values_formats_and_the_general_alignment(fake_sheets):
    fake_sheets.responses["'Données'!B4:D6"] = grid_response([
        [cell("Régie", fill=NAVY, color=WHITE, bold=True), cell("Dépenses", fill=NAVY, color=WHITE, bold=True, h="CENTER")],
        [cell("Google"), cell("46 811 €", number=46811), cell("+52 %", number=0.52, h="RIGHT")],
        [cell("Meta", italic=True)],
    ], start=(3, 1))
    out = sheets_source.read_cells("https://docs.google.com/spreadsheets/d/SHEET1/edit#gid=0", "'Données'!B4:D6")
    assert fake_sheets.calls[0]["spreadsheetId"] == "SHEET1" and fake_sheets.calls[0]["includeGridData"] is True
    assert out["sheet"] == "Données"
    rows = out["rows"]
    assert [len(r) for r in rows] == [3, 3, 3]  # padded to the widest row
    head, dep = rows[0][0], rows[0][1]
    assert head["text"] == "Régie" and head["bold"] and head["fill"] == NAVY and head["color"] == WHITE
    assert head["h_align"] == "START" and dep["h_align"] == "CENTER"
    google, spend, delta = rows[1]
    assert not google["is_number"] and google["h_align"] == "START"  # general text: left
    assert spend["is_number"] and spend["text"] == "46 811 €" and spend["h_align"] == "END"  # general number: right
    assert delta["h_align"] == "END" and delta["font"] == "Arial" and delta["size"] == 10
    assert rows[2][0]["italic"] and rows[2][1]["text"] == "" and rows[2][2]["text"] == ""


def test_theme_colours_are_resolved(fake_sheets):
    accent = {"red": 0.0, "green": 0.96, "blue": 0.71}
    c = cell("Total", bold=True)
    c["effectiveFormat"]["backgroundColorStyle"] = {"themeColor": "ACCENT1"}
    fake_sheets.responses["bilan_total"] = grid_response([[c]], theme={"ACCENT1": accent})
    out = sheets_source.read_cells("SHEET1", "bilan_total")  # a named range goes through as is
    assert out["rows"][0][0]["fill"] == accent
    assert fake_sheets.calls[0]["ranges"] == ["bilan_total"]


def test_merges_are_relative_to_the_range(fake_sheets):
    fake_sheets.responses["'Données'!B4:D5"] = grid_response(
        [[cell("Période", bold=True), cell(""), cell("")], [cell("a"), cell("b"), cell("c")]],
        start=(3, 1), merges=[{"startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1, "endColumnIndex": 4},
                              {"startRowIndex": 40, "endRowIndex": 41, "startColumnIndex": 0, "endColumnIndex": 2}])
    out = sheets_source.read_cells("SHEET1", "'Données'!B4:D5")
    assert out["merges"] == [(0, 0, 1, 3)]  # the merge outside the range is dropped


def test_unknown_range_is_an_error(fake_sheets):
    with pytest.raises(Exception, match="Unable to parse range"):
        sheets_source.read_cells("SHEET1", "'Nope'!A1:B2")
