"""Native Sheets charts: insert (linked / snapshot), list, refresh."""

import pytest

from gslides_mcp.tools import sheets_charts
from gslides_mcp.tools.deck import inspect_slide

SHEET_URL = "https://docs.google.com/spreadsheets/d/1AbC_def-GHI/edit#gid=0"


def _chart_element(oid="chart_el_1", sheet="1AbC_def-GHI", chart_id=42):
    return {"objectId": oid, "sheetsChart": {"spreadsheetId": sheet, "chartId": chart_id, "contentUrl": "https://x/y.png"},
            "size": {"width": {"magnitude": 640 * 12700, "unit": "EMU"}, "height": {"magnitude": 300 * 12700, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": 40 * 12700, "translateY": 80 * 12700, "unit": "EMU"}}


def test_parse_sheet_id_accepts_url_or_id():
    assert sheets_charts.parse_sheet_id(SHEET_URL) == "1AbC_def-GHI"
    assert sheets_charts.parse_sheet_id("  plainid  ") == "plainid"


def test_insert_linked_chart_builds_a_createSheetsChart_request(fake_slides):
    out = sheets_charts.insert_sheets_chart("PRES1", "1", SHEET_URL, 42, x_pt=40, y_pt=80, width_pt=640, height_pt=300)
    (req,) = fake_slides.batches[0]
    c = req["createSheetsChart"]
    assert c["spreadsheetId"] == "1AbC_def-GHI" and c["chartId"] == 42 and c["linkingMode"] == "LINKED"
    assert c["elementProperties"]["pageObjectId"] == "slide_1"
    assert c["elementProperties"]["size"]["width"]["magnitude"] == 640 * 12700
    assert c["elementProperties"]["transform"]["translateX"] == 40 * 12700
    assert out["element_id"] == "gen_chart_1" and out["slide_id"] == "slide_1" and out["linked"] is True


def test_insert_snapshot_chart_with_custom_id(fake_slides):
    out = sheets_charts.insert_sheets_chart("PRES1", "slide_1", "sheetid", 7, 0, 0, 100, 100, linked=False, object_id="my_chart_1")
    (req,) = fake_slides.batches[0]
    assert req["createSheetsChart"]["linkingMode"] == "NOT_LINKED_IMAGE" and req["createSheetsChart"]["objectId"] == "my_chart_1"
    assert out["element_id"] == "my_chart_1" and out["linked"] is False
    with pytest.raises(ValueError):
        sheets_charts.insert_sheets_chart("PRES1", "1", "sheetid", 7, 0, 0, 100, 100, object_id="ab")


def test_list_and_refresh_find_linked_charts(fake_slides, pres):
    pres["slides"][0]["pageElements"].append(_chart_element())
    pres["slides"][1]["pageElements"].append(_chart_element("chart_el_2", chart_id=43))
    listing = sheets_charts.list_sheets_charts("PRES1")["charts"]
    assert [c["id"] for c in listing] == ["chart_el_1", "chart_el_2"]
    assert listing[0] == {"id": "chart_el_1", "slide": 1, "slide_id": "slide_1", "spreadsheet_id": "1AbC_def-GHI", "chart_id": 42,
                          "linked": True, "x": 40.0, "y": 80.0, "w": 640.0, "h": 300.0,
                          "spreadsheet_url": "https://docs.google.com/spreadsheets/d/1AbC_def-GHI/edit"}
    assert [c["id"] for c in sheets_charts.list_sheets_charts("PRES1", slide="2")["charts"]] == ["chart_el_2"]
    out = sheets_charts.refresh_sheets_charts("PRES1")
    assert out == {"refreshed": ["chart_el_1", "chart_el_2"], "count": 2}
    assert fake_slides.batches[-1] == [{"refreshSheetsChart": {"objectId": "chart_el_1"}}, {"refreshSheetsChart": {"objectId": "chart_el_2"}}]
    only = sheets_charts.refresh_sheets_charts("PRES1", slide="1")
    assert only["refreshed"] == ["chart_el_1"]
    given = sheets_charts.refresh_sheets_charts("PRES1", element_ids=["chart_el_2"])
    assert given["count"] == 1 and fake_slides.batches[-1] == [{"refreshSheetsChart": {"objectId": "chart_el_2"}}]
    assert sheets_charts.refresh_sheets_charts("PRES1", slide="3") == {"refreshed": [], "count": 0}


def test_inspect_slide_reports_sheets_charts_as_charts(fake_slides, pres):
    pres["slides"][0]["pageElements"].append(_chart_element())
    el = next(e for e in inspect_slide("PRES1", "1")["elements"] if e["id"] == "chart_el_1")
    assert el["type"] == "chart" and el["x"] == 40.0 and el["w"] == 640.0
