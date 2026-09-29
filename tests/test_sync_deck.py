"""sync_deck: a bilan deck follows its spreadsheet's « Liaisons » tab."""

import pytest

from gslides_mcp.tools import sync
from test_images import _image
from test_refill import BARLOW, GREEN, RED, _shape, _table

TAB = "'Liaisons'!A1:E500"
HEAD = ["type", "élément", "source", "options"]
SLOT_URL = "https://drive.google.com/uc?export=view&id=visual_new"


def _chart(oid="chart_1", sheet="SHEET1"):
    return {"objectId": oid, "sheetsChart": {"spreadsheetId": sheet, "chartId": 7},
            "size": {"width": {"magnitude": 12700, "unit": "EMU"}, "height": {"magnitude": 12700, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0, "unit": "EMU"}}


@pytest.fixture
def bilan(fake_slides, pres, fake_sheets, monkeypatch):
    slot = _image("yt_top_slot_1", 40, 40, 100, 56, description="slot:40.0,40.0,100.0,56.0")
    slot["image"]["sourceUrl"] = "https://drive.google.com/uc?export=view&id=visual_old"
    pres["slides"][2]["pageElements"] = [
        _table("regies_table_1", [
            [("Régie", BARLOW), ("Dépenses", BARLOW), ("vs N-1", BARLOW)],
            [("Google", {}), ("46 811 €", {}), ("+52 %", {**BARLOW, "foregroundColor": GREEN})],
            [("Meta", {}), ("12 000 €", {}), ("-8 %", {**BARLOW, "foregroundColor": RED})],
        ]),
        _shape("kpi_depenses_value_1", "58 811 €", {"bold": True}),
        _shape("kpi_depenses_delta_1", "+4 %", {"foregroundColor": GREEN}),
        slot,
        _chart(),
    ]
    fake_sheets.values.update({
        TAB: [HEAD,
              ["texte", "kpi_depenses_value_1", "bilan_depenses", ""],
              ["texte", "kpi_depenses_delta_1", "bilan_delta", ""],
              ["tableau", "regies_table_1", "bilan_regies", "rows=fit"],
              ["image", "yt_top_slot_1", "'Visuels'!B2", ""]],
        "bilan_depenses": [["63 200 €"]],
        "bilan_delta": [["-3 %"]],
        "bilan_regies": [["Régie", "Dépenses", "vs N-1"], ["Google", "50 000 €", "+7 %"], ["Meta", "13 200 €", "-2 %"]],
        "'Visuels'!B2": [["drive:visual_new"]],
    })
    import gslides_mcp.assets as assets_mod
    monkeypatch.setattr(assets_mod, "ensure_asset", lambda ref, tint=None: ref[6:] if ref.startswith("drive:") else "fid_" + ref)
    return fake_slides


def _kinds(batch):
    return [next(iter(q)) for q in batch]


def test_dry_run_reports_every_binding_and_writes_nothing(bilan, fake_sheets):
    out = sync.sync_deck("PRES1", dry_run=True)
    assert bilan.batches == [] and out["written"] is False and out["errors"] == []
    assert out["spreadsheet"] == "SHEET1"  # found through the linked chart
    by_el = {b["element"]: b for b in out["bindings"]}
    assert by_el["kpi_depenses_value_1"] == {"row": 2, "type": "texte", "element": "kpi_depenses_value_1",
                                             "status": "would change", "old": "58 811 €", "new": "63 200 €"}
    assert by_el["regies_table_1"]["status"] == "would change" and by_el["regies_table_1"]["changed_cells"] == 4
    assert by_el["yt_top_slot_1"]["status"] == "would change" and by_el["yt_top_slot_1"]["source"] == "drive:visual_new"
    assert out["charts_to_refresh"] == 1
    # texts and image sources come in one values.batchGet with the tab read before it
    batch_gets = [c["batchGet"] for c in fake_sheets.calls if "batchGet" in c]
    assert batch_gets == [[TAB], ["bilan_depenses", "bilan_delta", "bilan_regies", "'Visuels'!B2"]]


def test_run_writes_tables_first_then_visuals_texts_and_charts(bilan):
    out = sync.sync_deck("PRES1")
    tables, later = bilan.batches
    assert all(q[next(iter(q))].get("objectId", q[next(iter(q))].get("tableObjectId")) == "regies_table_1" for q in tables)
    kinds = _kinds(later)
    assert "replaceImage" in kinds and kinds[-1] == "refreshSheetsChart"
    delta_style = [q["updateTextStyle"] for q in later if "updateTextStyle" in q
                   and q["updateTextStyle"]["objectId"] == "kpi_depenses_delta_1"]
    assert delta_style[0]["style"]["foregroundColor"] == RED  # -3 %: the deck's colour for a minus
    assert out["written"] is True and out["charts_refreshed"] == 1


def test_a_second_run_leaves_matching_elements_alone(bilan, fake_sheets, pres):
    fake_sheets.values["bilan_depenses"] = [["58 811 €"]]
    fake_sheets.values["bilan_delta"] = [["+4 %"]]
    fake_sheets.values["bilan_regies"] = [["Régie", "Dépenses", "vs N-1"], ["Google", "46 811 €", "+52 %"], ["Meta", "12 000 €", "-8 %"]]
    fake_sheets.values["'Visuels'!B2"] = [["drive:visual_old"]]
    out = sync.sync_deck("PRES1")
    assert {b["status"] for b in out["bindings"]} == {"unchanged"}
    assert bilan.batches == [[{"refreshSheetsChart": {"objectId": "chart_1"}}]]


def test_errors_stop_the_run_with_their_rows(bilan, fake_sheets):
    fake_sheets.values[TAB] = [HEAD,
                               ["texte", "regies_table_1", "bilan_depenses", ""],   # a table is not a text
                               ["image", "nope_slot", "'Visuels'!B2", ""],          # not in the deck
                               ["graphique", "chart_1", "x", ""],                  # unknown type
                               ["texte", "kpi_depenses_value_1", "bilan_depenses", ""]]
    out = sync.sync_deck("PRES1")
    assert bilan.batches == [] and out["written"] is False
    assert [e["row"] for e in out["errors"]] == [2, 3, 4]
    assert "shape" in out["errors"][0]["error"] and "not found" in out["errors"][1]["error"]


def test_an_unreadable_range_is_named(bilan, fake_sheets):
    del fake_sheets.values["bilan_delta"]
    out = sync.sync_deck("PRES1", dry_run=True)
    assert [(e["row"], "bilan_delta" in e["error"]) for e in out["errors"]] == [(3, True)]


def test_only_runs_one_kind(bilan):
    out = sync.sync_deck("PRES1", only=["texte"])
    assert {b["type"] for b in out["bindings"]} == {"texte"}
    (later,) = bilan.batches  # no table batch
    assert "replaceImage" not in _kinds(later)
    with pytest.raises(ValueError, match="only takes"):
        sync.sync_deck("PRES1", only=["graphique"])


def test_the_spreadsheet_must_be_given_when_charts_do_not_say(bilan, pres):
    pres["slides"][2]["pageElements"][-1]["sheetsChart"]["spreadsheetId"] = "OTHER"
    pres["slides"][2]["pageElements"].append(_chart("chart_2", "SHEET1"))
    with pytest.raises(ValueError, match="2 spreadsheets"):
        sync.sync_deck("PRES1")
    pres["slides"][2]["pageElements"] = pres["slides"][2]["pageElements"][:-2]
    with pytest.raises(ValueError, match="no linked Sheets chart"):
        sync.sync_deck("PRES1")
    out = sync.sync_deck("PRES1", spreadsheet="https://docs.google.com/spreadsheets/d/SHEET1/edit", dry_run=True)
    assert out["spreadsheet"] == "SHEET1" and out.get("charts_to_refresh") == 0
