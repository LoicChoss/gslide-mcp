"""The « Liaisons » tab: parsing, per-row errors, reading through values.batchGet."""

import pytest

from gslides_mcp import bindings, sheets_source

HEAD = ["Type", "Élément", "Source", "Options"]


def test_rows_become_bindings_with_typed_options():
    good, errors = bindings.parse_bindings([
        HEAD,
        ["texte", "kpi_value_1", "bilan_depenses", ""],
        ["TEXTE", "kpi_delta_1", "'Synthèse'!C7", "delta=inverse"],
        ["tableau", "regies_table_1", "bilan_regies", "style=sheets; rows=fit ; row_height=26,5"],
        ["image", "yt_top_slot_1", "'Visuels'!B2", "fit=crop"],
        ["", "", "", ""],
        ["# à faire", "x", "y", ""],
    ])
    assert errors == []
    assert [(b["row"], b["type"], b["element"]) for b in good] == [
        (2, "texte", "kpi_value_1"), (3, "texte", "kpi_delta_1"), (4, "tableau", "regies_table_1"), (5, "image", "yt_top_slot_1")]
    assert good[1]["options"] == {"delta": "inverse"}
    assert good[2]["options"] == {"style": "sheets", "rows": "fit", "row_height": 26.5}
    assert good[3]["options"] == {"fit": "crop"}


def test_columns_in_any_order_and_english_names():
    good, errors = bindings.parse_bindings([["source", "element", "type"], ["bilan_x", "kpi_1", "text"]])
    assert errors == [] and good == [{"row": 2, "type": "texte", "element": "kpi_1", "source": "bilan_x", "options": {}}]
    good, _ = bindings.parse_bindings([HEAD, ["texte", "kpi_2", "b", "delta=false"]])
    assert good[0]["options"] == {"delta": False}


def test_each_bad_row_is_reported_with_its_row_number():
    good, errors = bindings.parse_bindings([
        HEAD,
        ["graphique", "c1", "x", ""],
        ["texte", "", "x", ""],
        ["texte", "k1", "", ""],
        ["tableau", "t1", "x", "style=comic"],
        ["tableau", "t2", "x", "colour=red"],
        ["image", "s1", "x", "fit"],
        ["texte", "k2", "x", ""],
        ["texte", "k2", "y", ""],
    ])
    assert [b["element"] for b in good] == ["k2"]
    assert [(e["row"], e["error"].split(":")[0].split(" ")[0]) for e in errors] == [
        (2, "type"), (3, "élément"), (4, "source"), (5, "style='comic'"), (6, "unknown"), (7, "option"), (9, "'k2'")]


def test_a_tab_without_the_needed_columns_is_refused():
    with pytest.raises(ValueError, match="missing: source"):
        bindings.parse_bindings([["type", "élément"], ["texte", "k"]])
    with pytest.raises(ValueError, match="empty"):
        bindings.parse_bindings([])


def test_read_bindings_uses_one_batch_get(fake_sheets):
    fake_sheets.values["'Liaisons'!A1:E500"] = [HEAD, ["texte", "kpi_1", "bilan_depenses"]]
    good, errors = bindings.read_bindings("https://docs.google.com/spreadsheets/d/SHEET1/edit")
    assert good[0]["element"] == "kpi_1" and errors == []
    assert fake_sheets.calls == [{"spreadsheetId": "SHEET1", "batchGet": ["'Liaisons'!A1:E500"]}]


def test_read_bindings_without_the_tab(fake_sheets):
    with pytest.raises(ValueError, match="no « Liaisons » tab"):
        bindings.read_bindings("SHEET1")


def test_read_values_keeps_the_order_and_as_cells_pads(fake_sheets):
    fake_sheets.values.update({"a": [["1"]], "b": [["x", "y"], ["z"]]})
    got = sheets_source.read_values("SHEET1", ["b", "a"])
    assert got == [[["x", "y"], ["z"]], [["1"]]]
    cells = sheets_source.as_cells(got[0])
    assert [[c["text"] for c in r] for r in cells["rows"]] == [["x", "y"], ["z", ""]]
