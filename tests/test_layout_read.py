"""Lot 1 read-side tools: get_presentation, get_page, list_layouts."""

import json

import pytest

from gslides_mcp.tools import layout


# --- get_presentation -------------------------------------------------------

def test_get_presentation_passes_fields_mask_through(fake_slides):
    out = layout.get_presentation("PRES1", fields="slides(objectId)")
    assert fake_slides.get_calls[-1]["fields"] == "slides(objectId)"
    assert out["truncated"] is False
    assert out["presentation"]["presentationId"] == "PRES1"


def test_get_presentation_accepts_full_url(fake_slides):
    layout.get_presentation("https://docs.google.com/presentation/d/PRES1/edit")
    assert fake_slides.get_calls[-1]["presentationId"] == "PRES1"


def test_get_presentation_truncates_oversized_response_by_whole_slides(fake_slides):
    big_text = "x" * 50_000
    fake_slides.pres["slides"] = [
        {"objectId": f"s{i}", "pageElements": [{"objectId": f"e{i}", "shape": {"text": {"textElements": [{"textRun": {"content": big_text}}]}}}]}
        for i in range(8)
    ]
    out = layout.get_presentation("PRES1")
    assert out["truncated"] is True
    assert out["size_bytes"] > 200_000
    assert out["slides_total"] == 8
    assert 0 < out["slides_included"] < 8
    assert len(out["presentation"]["slides"]) == out["slides_included"]
    assert len(json.dumps(out["presentation"])) <= 200_000
    assert "fields" in out["hint"]


# --- get_page ---------------------------------------------------------------

@pytest.mark.parametrize("page_id, kind", [
    ("slide_1", "slide"), ("lay_body", "layout"), ("m_main", "master"), ("notes_1", "notes"),
])
def test_get_page_returns_page_with_kind(fake_slides, page_id, kind):
    out = layout.get_page("PRES1", page_id)
    assert out["page_kind"] == kind
    assert out["page"]["objectId"] == page_id


def test_get_page_unknown_id_names_it(fake_slides):
    with pytest.raises(ValueError, match="'nope'"):
        layout.get_page("PRES1", "nope")


# --- list_layouts -----------------------------------------------------------

def test_list_layouts_default_hides_orphan_masters(fake_slides):
    out = layout.list_layouts("PRES1")
    assert out["masters"] == [{"master_id": "m_main", "display_name": "Simple Light", "used_by_slides": 3}]
    ids = [l["layout_id"] for l in out["layouts"]]
    assert ids == ["lay_title", "lay_body", "lay_two", "lay_summary", "lay_dup_a"]
    used = {l["layout_id"]: l["used_by_slides"] for l in out["layouts"]}
    assert used == {"lay_title": 1, "lay_body": 2, "lay_two": 0, "lay_summary": 0, "lay_dup_a": 0}


def test_list_layouts_all_masters(fake_slides):
    out = layout.list_layouts("PRES1", only_used_master=False)
    assert [m["master_id"] for m in out["masters"]] == ["m_main", "m_orphan"]
    assert out["masters"][1]["used_by_slides"] == 0
    assert len(out["layouts"]) == 7


def test_list_layouts_placeholders_default_index_to_zero(fake_slides):
    out = layout.list_layouts("PRES1")
    two = next(l for l in out["layouts"] if l["layout_id"] == "lay_two")
    assert two["display_name"] == "A_Retenir"
    assert two["name"] == "TITLE_AND_TWO_COLUMNS"
    assert two["master_id"] == "m_main"
    assert two["placeholders"] == [
        {"type": "TITLE", "index": 0, "object_id": "lay_two_t"},
        {"type": "BODY", "index": 1, "object_id": "lay_two_b1"},
        {"type": "BODY", "index": 2, "object_id": "lay_two_b2"},
    ]


def test_list_layouts_requests_a_narrow_fields_mask(fake_slides):
    layout.list_layouts("PRES1")
    fields = fake_slides.get_calls[-1]["fields"]
    assert fields and "layouts(" in fields and "pageElements" not in fields.split("layouts(")[0]


def test_get_page_compact_lists_elements_with_placeholders(fake_slides):
    out = layout.get_page("PRES1", "slide_1", compact=True)
    assert out["page_kind"] == "slide" and out["page_id"] == "slide_1"
    assert "page" not in out
    by_id = {e["id"]: e for e in out["elements"]}
    assert by_id["s1_title"]["placeholder"] == {"type": "CENTERED_TITLE", "index": 0}
    assert by_id["s1_title"]["text"] == "Hello title"
    assert by_id["s1_box"]["type"] == "RECTANGLE" and "placeholder" not in by_id["s1_box"]
    assert by_id["s1_img"]["type"] == "image"
    assert by_id["s1_box"]["x"] == round(5000000 / 12700, 1)


def test_get_page_compact_on_layout_keeps_page_order(fake_slides):
    out = layout.get_page("PRES1", "lay_two", compact=True)
    assert [e["placeholder"]["index"] for e in out["elements"]] == [0, 1, 2]
    assert [e["id"] for e in out["elements"]] == ["lay_two_t", "lay_two_b1", "lay_two_b2"]
