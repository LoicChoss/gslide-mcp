"""Rework tools: harvest_deck_assets, suggest_components, inspect_slide enrichment, layout content areas."""

import pytest

from gslides_mcp import assets
from gslides_mcp.tools import harvest
from gslides_mcp.tools.deck import inspect_slide
from gslides_mcp.tools.layout import list_layouts

EMU = 12700


def _shape(oid, text, x, y, w, h, bullets=0, placeholder=None):
    tes = []
    if bullets:
        for i in range(bullets):
            tes.append({"paragraphMarker": {"bullet": {"nestingLevel": 0}}})
            tes.append({"textRun": {"content": f"{text} {i + 1}\n"}})
    else:
        tes.append({"paragraphMarker": {}})
        tes.append({"textRun": {"content": text + "\n"}})
    sh = {"shapeType": "TEXT_BOX", "text": {"textElements": tes}}
    if placeholder:
        sh["placeholder"] = {"type": placeholder}
    return {"objectId": oid, "shape": sh,
            "size": {"width": {"magnitude": w * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x * EMU, "translateY": y * EMU, "unit": "EMU"}}


def _image(oid, x, y, w, h, url="https://lh7.googleusercontent.com/x", alt=""):
    el = {"objectId": oid, "image": {"contentUrl": url},
          "size": {"width": {"magnitude": w * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}},
          "transform": {"scaleX": 1, "scaleY": 1, "translateX": x * EMU, "translateY": y * EMU, "unit": "EMU"}}
    if alt:
        el["title"] = alt
    return el


@pytest.fixture
def assets_root(monkeypatch):
    monkeypatch.setenv(assets.ENV_FOLDER, "assets_root")
    monkeypatch.setattr(assets, "CACHE", assets.CACHE.parent / "test-harvest-cache.json")
    yield "assets_root"
    try:
        assets.CACHE.unlink()
    except OSError:
        pass


def test_harvest_stores_images_and_thumbnails_in_a_sources_folder(fake_slides, fake_drive, fake_download, assets_root, pres):
    pres["title"] = "Bilan CFA"
    pres["slides"][0]["pageElements"].append(_image("logo_small", 10, 10, 12, 12))  # skipped: tiny
    pres["slides"][0]["pageElements"][3]["title"] = "Logo client"  # s1_img alt
    out = harvest.harvest_deck_assets("PRES1", slides=["1"])
    assert out["folder_created"] is True and out["deck_title"] == "Bilan CFA"
    folder = next(f for f in fake_drive.store_files if f["mimeType"] == harvest._FOLDER_MIME)
    assert folder["name"] == "Bilan CFA · sources" and folder["parents"] == [assets_root]
    (row,) = out["slides"]
    assert row["index"] == 1 and len(row["images"]) == 1
    img = row["images"][0]
    assert img["name"] == "s01-1-logo-client.png" and img["asset"] == f"drive:{img['file_id']}" and img["url"].endswith(img["file_id"])
    assert img["alt"] == "Logo client" and img["w"] == 63.0 and img["element_id"] == "s1_img"
    assert row["thumbnail"]["name"] == "s01-slide.png"
    assert out["skipped"] == [{"slide": 1, "element_id": "logo_small", "reason": "smaller than 20.0 pt"}]
    uploaded = [f for f in fake_drive.store_files if f["mimeType"] != harvest._FOLDER_MIME]
    assert [f["name"] for f in uploaded] == ["s01-1-logo-client.png", "s01-slide.png"]
    assert all(f["parents"] == [folder["id"]] for f in uploaded)
    assert "https://lh7.googleusercontent.com/img1" in fake_download  # the image was fetched
    shared = [c for c in fake_drive.calls if c[0] == "permissions.create"]
    assert len(shared) == 2  # both files shared read-only for createImage
    # idempotent: a second run reuses the folder and the files
    again = harvest.harvest_deck_assets("PRES1", slides=["1"])
    assert again["folder_created"] is False and again["slides"][0]["images"][0]["file_id"] == img["file_id"]
    assert len([f for f in fake_drive.store_files if f["mimeType"] != harvest._FOLDER_MIME]) == 2


def test_harvest_into_a_given_folder_without_thumbnails(fake_slides, fake_drive, fake_download, assets_root):
    out = harvest.harvest_deck_assets("PRES1", folder="https://drive.google.com/drive/folders/MyFolder123?usp=sharing", thumbnails=False)
    assert out["folder_id"] == "MyFolder123" and out["folder_created"] is False
    assert all(r["thumbnail"] is None for r in out["slides"]) and out["image_count"] == 1
    assert not any(f["mimeType"] == harvest._FOLDER_MIME for f in fake_drive.store_files)
    assert fake_slides.thumbnail_calls == []


def test_drive_asset_refs_resolve_without_the_folder(assets_root):
    assert assets.ensure_asset("drive:abc123") == "abc123"
    with pytest.raises(ValueError):
        assets.ensure_asset("drive:")


def test_inspect_slide_exposes_image_urls_table_cells_placeholders_and_paragraphs(fake_slides, pres):
    pres["slides"][0]["pageElements"].append(_shape("bul", "Point", 40, 200, 300, 100, bullets=3))
    by_id = {e["id"]: e for e in inspect_slide("PRES1", "1")["elements"]}
    assert by_id["s1_img"]["image_url"] == "https://lh7.googleusercontent.com/img1" and by_id["s1_img"]["source_url"] == "https://example.com/logo.png"
    assert by_id["s1_title"]["placeholder"] == "CENTERED_TITLE" and "paragraphs" not in by_id["s1_title"]
    assert by_id["bul"]["paragraphs"] == [{"text": f"Point {i}", "level": 0, "bullet": True} for i in (1, 2, 3)]
    tbl = {e["id"]: e for e in inspect_slide("PRES1", "2")["elements"]}["tbl_1"]
    assert tbl["rows"] == [["A", ""], ["", ""]]


def test_list_layouts_reports_placeholder_geometry_and_content_area(fake_slides, pres):
    lay = next(l for l in pres["layouts"] if l["objectId"] == "lay_body")
    for el, (x, y, w, h) in zip(lay["pageElements"], [(30, 20, 660, 50), (30, 90, 660, 260), (600, 380, 90, 20)]):
        el["size"] = {"width": {"magnitude": w * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}}
        el["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": x * EMU, "translateY": y * EMU, "unit": "EMU"}
    lay2 = next(l for l in pres["layouts"] if l["objectId"] == "lay_summary")  # title only
    lay2["pageElements"][0]["size"] = {"width": {"magnitude": 600 * EMU, "unit": "EMU"}, "height": {"magnitude": 40 * EMU, "unit": "EMU"}}
    lay2["pageElements"][0]["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": 60 * EMU, "translateY": 30 * EMU, "unit": "EMU"}
    out = list_layouts("PRES1")
    assert out["page"] == {"w": 720.0, "h": 405.0}
    by_id = {l["layout_id"]: l for l in out["layouts"]}
    body = by_id["lay_body"]
    assert body["placeholders"][1] == {"type": "BODY", "index": 1, "object_id": "lay_body_b", "x": 30.0, "y": 90.0, "w": 660.0, "h": 260.0}
    assert body["content_area"] == {"x": 30.0, "y": 90.0, "w": 660.0, "h": 260.0, "from": "body placeholders"}
    assert by_id["lay_summary"]["content_area"] == {"x": 60.0, "y": 82.0, "w": 600.0, "h": 293.0, "from": "below the title"}
    assert by_id["lay_title"]["content_area"] is None and "x" not in by_id["lay_title"]["placeholders"][0]


def test_suggest_components_splits_a_slide_into_blocks(fake_slides, pres):
    sl = pres["slides"][2]  # empty slide 3
    sl["pageElements"] = [
        _shape("t", "Résultats de la campagne", 30, 20, 660, 40, placeholder="TITLE"),
        _shape("k1", "18 336 040 impressions", 30, 80, 200, 60), _shape("k2", "101 216 clics +109 %", 250, 80, 200, 60), _shape("k3", "130 311 € investis", 470, 80, 200, 60),
        {"objectId": "tb", "table": {"rows": 3, "columns": 4, "tableRows": [
            {"tableCells": [{"text": {"textElements": [{"textRun": {"content": c}}]}} for c in ("Canal", "Clics", "Coût", "CPA")]},
            {"tableCells": [{"text": {"textElements": [{"textRun": {"content": c}}]}} for c in ("Google", "4 530", "18 024 €", "34 €")]},
            {"tableCells": [{"text": {"textElements": [{"textRun": {"content": c}}]}} for c in ("Meta", "811", "442 €", "12 €")]}]},
         "size": {"width": {"magnitude": 660 * EMU, "unit": "EMU"}, "height": {"magnitude": 150 * EMU, "unit": "EMU"}},
         "transform": {"scaleX": 1, "scaleY": 1, "translateX": 30 * EMU, "translateY": 160 * EMU, "unit": "EMU"}},
        _shape("src", "* Sources : Google Ads, décembre 2025", 30, 370, 400, 20),
    ]
    out = harvest.suggest_components("PRES1", "3")
    assert out["title"] == "Résultats de la campagne" and out["index"] == 3
    kinds = {b["kind"]: b for b in out["blocks"]}
    assert kinds["table"]["candidates"][0]["component"] == "table" and "pill_cols" in kinds["table"]["candidates"][0]["why"]
    assert kinds["table"]["candidates"][0]["variants"]  # the ready-made settings are named
    assert kinds["columns"]["elements"] == ["k1", "k2", "k3"] and kinds["columns"]["candidates"][0]["component"] == "kpi_grid"
    assert kinds["columns"]["zone"] == {"x": 30.0, "y": 80.0, "w": 640.0, "h": 60.0}
    assert kinds["text"]["candidates"][0]["component"] == "source_note"
    assert [s["component"] for s in out["slide_level"]][:2] == ["kpi_grid", "chart_bars"]
    assert all("use" in c for b in out["blocks"] for c in b["candidates"])
    assert out["signals"]["unused_elements"] == []


def test_suggest_components_reads_images_bullets_and_keywords(fake_slides, pres):
    sl = pres["slides"][2]
    sl["pageElements"] = [
        _shape("t", "Avant / après la refonte du site", 30, 20, 660, 40, placeholder="TITLE"),
        _shape("a", "Structure plate", 30, 80, 300, 200, bullets=4), _shape("b", "Structure cible", 390, 80, 300, 200, bullets=4),
        _image("shot", 30, 290, 660, 100, url="https://lh7.googleusercontent.com/shot"),
    ]
    out = harvest.suggest_components("PRES1", "3")
    pair = next(b for b in out["blocks"] if b["kind"] == "pair")
    assert pair["candidates"][0]["component"] == "before_after" and pair["elements"] == ["a", "b"]
    img = next(b for b in out["blocks"] if b["kind"] in ("image", "images"))
    assert img["candidates"][0]["component"] in ("gallery", "browser")
    assert out["slide_level"][0]["component"] == "before_after"
    # title-only slide
    sl["pageElements"] = [_shape("t", "Partie 2", 30, 20, 660, 40, placeholder="TITLE")]
    out = harvest.suggest_components("PRES1", "3")
    assert out["blocks"] == [] and out["slide_level"][0]["component"] == "section_header"


def test_suggest_components_groups_stacked_labels_and_ignores_empty_shapes(fake_slides, pres):
    sl = pres["slides"][2]
    sl["pageElements"] = [
        _shape("t", "Codes couleurs", 30, 20, 660, 40, placeholder="TITLE"),
        _shape("l1", "Navy", 150, 100, 60, 20), _shape("l2", "Menthe", 150, 130, 60, 20), _shape("l3", "Corail", 150, 160, 60, 20), _shape("l4", "Acide", 150, 190, 60, 20),
        _shape("empty", "", 400, 100, 200, 100),
    ]
    out = harvest.suggest_components("PRES1", "3")
    (block,) = out["blocks"]
    assert block["kind"] == "stack" and block["elements"] == ["l1", "l2", "l3", "l4"] and block["candidates"][0]["component"] == "table"
    assert out["signals"]["unused_elements"] == []


def test_content_area_falls_back_to_the_page_when_the_title_fills_the_layout(fake_slides, pres):
    lay = next(l for l in pres["layouts"] if l["objectId"] == "lay_summary")
    lay["pageElements"][0]["size"] = {"width": {"magnitude": 500 * EMU, "unit": "EMU"}, "height": {"magnitude": 330 * EMU, "unit": "EMU"}}
    lay["pageElements"][0]["transform"] = {"scaleX": 1, "scaleY": 1, "translateX": 40 * EMU, "translateY": 40 * EMU, "unit": "EMU"}
    area = {l["layout_id"]: l for l in list_layouts("PRES1")["layouts"]}["lay_summary"]["content_area"]
    assert area == {"x": 30.0, "y": 30.0, "w": 660.0, "h": 345.0, "from": "page (the title fills the layout)"}


def test_single_cell_tables_are_boxes_not_tables(fake_slides, pres):
    sl = pres["slides"][2]
    sl["pageElements"] = [
        _shape("t", "Taux d'acceptation", 30, 20, 660, 40, placeholder="TITLE"),
        {"objectId": "box", "table": {"rows": 1, "columns": 1, "tableRows": [{"tableCells": [{"text": {"textElements": [{"textRun": {"content": "63 %"}}]}}]}]},
         "size": {"width": {"magnitude": 120 * EMU, "unit": "EMU"}, "height": {"magnitude": 80 * EMU, "unit": "EMU"}},
         "transform": {"scaleX": 1, "scaleY": 1, "translateX": 60 * EMU, "translateY": 120 * EMU, "unit": "EMU"}},
    ]
    (block,) = harvest.suggest_components("PRES1", "3")["blocks"]
    assert block["kind"] == "box" and block["content"] == "63 %" and block["candidates"][0]["component"] == "stat_box"
