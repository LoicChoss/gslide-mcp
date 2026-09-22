"""draw.ops_to_requests: primitive ops (pt) -> Slides batchUpdate requests."""

import pytest

from gslides_mcp import draw
from gslides_mcp.themes import Theme

PT = 12700
THEME = Theme(name="t", colors={"mint": "#00F6B5", "navy": "#002B3C"}, font="Barlow")


def _run(ops, **kw):
    return draw.ops_to_requests("slide_1", ops, THEME, prefix="cmp", **kw)


def _of(reqs, kind):
    return [r[kind] for r in reqs if kind in r]


# --- box ------------------------------------------------------------------------

def test_box_geometry_fill_and_hidden_outline():
    reqs, ids = _run([{"op": "box", "x": 10, "y": 20, "w": 100, "h": 50, "fill": "#FF0000"}])
    (create,) = _of(reqs, "createShape")
    assert create["shapeType"] == "RECTANGLE"
    assert create["elementProperties"]["pageObjectId"] == "slide_1"
    assert create["elementProperties"]["size"]["width"]["magnitude"] == 100 * PT
    assert create["elementProperties"]["transform"]["translateX"] == 10 * PT
    (props,) = _of(reqs, "updateShapeProperties")
    assert props["shapeProperties"]["shapeBackgroundFill"]["solidFill"]["color"]["rgbColor"] == {"red": 1, "green": 0, "blue": 0}
    assert props["shapeProperties"]["outline"]["propertyState"] == "NOT_RENDERED"
    assert ids == [create["objectId"]] and len(ids[0]) >= 5


def test_box_uses_theme_tokens_shape_and_outline():
    reqs, _ = _run([{"op": "box", "x": 0, "y": 0, "w": 10, "h": 10, "fill": None,
                     "line": {"color": "mint", "weight": 1.5}, "shape": "ROUND_RECTANGLE"}])
    assert _of(reqs, "createShape")[0]["shapeType"] == "ROUND_RECTANGLE"
    (props,) = _of(reqs, "updateShapeProperties")
    assert props["shapeProperties"]["shapeBackgroundFill"]["propertyState"] == "NOT_RENDERED"
    outline = props["shapeProperties"]["outline"]
    assert outline["weight"] == {"magnitude": 1.5, "unit": "PT"}
    assert outline["outlineFill"]["solidFill"]["color"]["rgbColor"]["green"] == pytest.approx(0.965, abs=0.01)


# --- text -----------------------------------------------------------------------

def test_text_runs_paragraphs_and_base_style():
    reqs, _ = _run([{"op": "text", "x": 0, "y": 0, "w": 200, "h": 40, "size": 12, "color": "navy",
                     "align": "CENTER", "valign": "MIDDLE",
                     "runs": [[{"text": "Hello "}, {"text": "world", "bold": True, "color": "mint"}],
                              [{"text": "Second", "italic": True, "size": 9}]]}])
    (create,) = _of(reqs, "createShape")
    assert create["shapeType"] == "TEXT_BOX"
    (ins,) = _of(reqs, "insertText")
    assert ins["text"] == "Hello world\nSecond"
    styles = _of(reqs, "updateTextStyle")
    base = styles[0]
    assert base["textRange"] == {"type": "ALL"}
    assert base["style"]["fontFamily"] == "Barlow"
    assert base["style"]["fontSize"] == {"magnitude": 12, "unit": "PT"}
    assert "fontFamily" in base["fields"] and "fontSize" in base["fields"] and "foregroundColor" in base["fields"]
    bold = next(s for s in styles if s["style"].get("bold"))
    assert bold["textRange"] == {"type": "FIXED_RANGE", "startIndex": 6, "endIndex": 11}
    assert bold["style"]["foregroundColor"]["opaqueColor"]["rgbColor"]["green"] == pytest.approx(0.965, abs=0.01)
    italic = next(s for s in styles if s["style"].get("italic"))
    assert italic["textRange"] == {"type": "FIXED_RANGE", "startIndex": 12, "endIndex": 18}
    assert italic["style"]["fontSize"]["magnitude"] == 9
    (para,) = _of(reqs, "updateParagraphStyle")
    assert para["style"]["alignment"] == "CENTER"
    (props,) = _of(reqs, "updateShapeProperties")
    assert props["shapeProperties"]["contentAlignment"] == "MIDDLE"


def test_text_plain_string_and_markdown():
    reqs, _ = _run([{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "text": "Plain", "bold": True}])
    assert _of(reqs, "insertText")[0]["text"] == "Plain"
    assert _of(reqs, "updateTextStyle")[0]["style"]["bold"] is True

    reqs, _ = _run([{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "markdown": "**Lead.** rest"}])
    assert any(s["style"].get("bold") for s in _of(reqs, "updateTextStyle"))
    assert "deleteText" not in {next(iter(r)) for r in reqs}


def test_text_in_box_targets_the_box():
    reqs, ids = _run([{"op": "box", "x": 0, "y": 0, "w": 100, "h": 30, "fill": "mint", "text": "Badge", "size": 9}])
    assert len(ids) == 1
    assert _of(reqs, "insertText")[0]["objectId"] == ids[0]


# --- lines ------------------------------------------------------------------------

def test_line_going_up_left_uses_negative_scale():
    reqs, _ = _run([{"op": "line", "x1": 100, "y1": 100, "x2": 40, "y2": 70, "color": "navy", "weight": 3, "dash": "DASH"}])
    (create,) = _of(reqs, "createLine")
    assert create["lineCategory"] == "STRAIGHT"
    t = create["elementProperties"]["transform"]
    assert (t["scaleX"], t["scaleY"]) == (-1, -1)
    assert t["translateX"] == 100 * PT and t["translateY"] == 100 * PT
    size = create["elementProperties"]["size"]
    assert size["width"]["magnitude"] == 60 * PT and size["height"]["magnitude"] == 30 * PT
    (props,) = _of(reqs, "updateLineProperties")
    assert props["lineProperties"]["weight"] == {"magnitude": 3, "unit": "PT"}
    assert props["lineProperties"]["dashStyle"] == "DASH"
    assert "dashStyle" in props["fields"]


def test_horizontal_line_keeps_a_positive_size():
    reqs, _ = _run([{"op": "line", "x1": 0, "y1": 10, "x2": 50, "y2": 10, "color": "navy"}])
    assert _of(reqs, "createLine")[0]["elementProperties"]["size"]["height"]["magnitude"] >= 1


def test_polyline_is_one_segment_per_pair():
    reqs, ids = _run([{"op": "polyline", "points": [[0, 0], [10, 5], [20, 0], [30, 8]], "color": "navy", "weight": 2}])
    assert len(_of(reqs, "createLine")) == 3 and len(ids) == 3


def test_arc_is_split_into_one_degree_segments():
    reqs, _ = _run([{"op": "arc", "cx": 50, "cy": 50, "r": 40, "a0": -90, "a1": 0, "weight": 20, "color": "mint"}])
    assert len(_of(reqs, "createLine")) == 90


def test_ring_shares_cover_the_full_circle_in_order():
    reqs, ids = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 20,
                       "segments": [{"value": 3, "color": "mint"}, {"value": 1, "color": "navy"}]}])
    lines = _of(reqs, "createLine")
    assert len(lines) == 360
    fills = [p["lineProperties"]["lineFill"]["solidFill"]["color"]["rgbColor"]["green"] for p in _of(reqs, "updateLineProperties")]
    assert fills[0] == pytest.approx(0.965, abs=0.01) and fills[-1] == pytest.approx(0.169, abs=0.01)
    assert sum(1 for f in fills if f > 0.9) == 270


# --- table ------------------------------------------------------------------------

def test_table_cells_header_banding_widths_and_borders():
    reqs, ids = _run([{"op": "table", "x": 0, "y": 0, "w": 300, "row_h": 20,
                       "rows": [["H1", "H2"], ["a", ""], ["c", "d"]],
                       "col_w": [100, 200], "size": 10,
                       "header": {"fill": "mint", "color": "navy", "bold": True},
                       "banding": ["#FFFFFF", "#F2F4F4"], "first_col_bold": True,
                       "borders": {"color": "#E3E7E7", "weight": 1}}])
    (create,) = _of(reqs, "createTable")
    assert create["rows"] == 3 and create["columns"] == 2
    assert create["elementProperties"]["size"]["height"]["magnitude"] == 60 * PT
    texts = {(t["cellLocation"]["rowIndex"], t["cellLocation"]["columnIndex"]): t["text"] for t in _of(reqs, "insertText")}
    assert texts == {(0, 0): "H1", (0, 1): "H2", (1, 0): "a", (1, 1): " ", (2, 0): "c", (2, 1): "d"}  # empty cell: styled space
    cell_props = _of(reqs, "updateTableCellProperties")
    header = cell_props[0]
    assert header["tableRange"] == {"location": {"rowIndex": 0, "columnIndex": 0}, "rowSpan": 1, "columnSpan": 2}
    assert header["tableCellProperties"]["tableCellBackgroundFill"]["solidFill"]["color"]["rgbColor"]["green"] == pytest.approx(0.965, abs=0.01)
    band = [c for c in cell_props if c["tableRange"]["location"]["rowIndex"] == 2][0]
    assert band["tableCellProperties"]["tableCellBackgroundFill"]["solidFill"]["color"]["rgbColor"]["red"] == pytest.approx(0.949, abs=0.01)
    widths = _of(reqs, "updateTableColumnProperties")
    assert [w["tableColumnProperties"]["columnWidth"]["magnitude"] for w in widths] == [100 * PT, 200 * PT]
    bold_cells = {(s["cellLocation"]["rowIndex"], s["cellLocation"]["columnIndex"])
                  for s in _of(reqs, "updateTextStyle") if s["style"].get("bold")}
    assert bold_cells == {(0, 0), (0, 1), (1, 0), (2, 0)}
    (border,) = _of(reqs, "updateTableBorderProperties")
    assert border["borderPosition"] == "ALL"
    assert border["tableBorderProperties"]["weight"] == {"magnitude": 1, "unit": "PT"}
    assert len(ids) == 1


# --- image / group / errors -----------------------------------------------------------

def test_image_from_drive_or_url():
    reqs, _ = _run([{"op": "image", "x": 0, "y": 0, "w": 50, "h": 50, "drive_file_id": "abc"},
                    {"op": "image", "x": 0, "y": 0, "w": 50, "h": 50, "url": "https://x/y.png"}])
    urls = [c["url"] for c in _of(reqs, "createImage")]
    assert urls == ["https://drive.google.com/uc?export=view&id=abc", "https://x/y.png"]


def test_group_wraps_every_element_and_returns_its_id():
    ops = [{"op": "box", "x": 0, "y": 0, "w": 10, "h": 10, "fill": "mint"},
           {"op": "line", "x1": 0, "y1": 0, "x2": 5, "y2": 5, "color": "navy"}]
    reqs, ids = _run(ops, group="grp_abc")
    (grp,) = _of(reqs, "groupObjects")
    assert grp["groupObjectId"] == "grp_abc" and grp["childrenObjectIds"] == ids
    reqs, _ = _run(ops[:1], group="grp_abc")
    assert _of(reqs, "groupObjects") == []  # a single element can't be grouped


def test_offset_shifts_every_op():
    reqs, _ = _run([{"op": "box", "x": 1, "y": 2, "w": 3, "h": 4, "fill": "mint"}], offset=(100, 200))
    t = _of(reqs, "createShape")[0]["elementProperties"]["transform"]
    assert (t["translateX"], t["translateY"]) == (101 * PT, 202 * PT)


def test_unknown_op_and_unknown_color_are_named():
    with pytest.raises(ValueError, match="'blob'"):
        _run([{"op": "blob"}])
    with pytest.raises(ValueError, match="'teal'"):
        _run([{"op": "box", "x": 0, "y": 0, "w": 1, "h": 1, "fill": "teal"}])


def test_table_row_fills_and_bold_rows_override_banding():
    reqs, _ = _run([{"op": "table", "x": 0, "y": 0, "w": 100, "rows": [["h"], ["a"], ["total"]],
                     "header": {"fill": "mint"}, "banding": ["#FFFFFF"], "row_fills": {2: "navy"}, "bold_rows": [2],
                     "borders": {"color": "#E3E7E7", "weight": 1}}])
    fills = [(c["tableRange"]["location"]["rowIndex"], c["tableCellProperties"]["tableCellBackgroundFill"]["solidFill"]["color"]["rgbColor"]["blue"])
             for c in _of(reqs, "updateTableCellProperties")]
    assert fills[-1] == (2, pytest.approx(0.235, abs=0.01))  # navy wins on the total row
    bold = {s["cellLocation"]["rowIndex"] for s in _of(reqs, "updateTextStyle") if s["style"].get("bold")}
    assert bold == {0, 2}  # header row is bold by default


def test_markdown_styles_never_reset_the_base_style():
    reqs, _ = _run([{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "markdown": "- a\n- **b** c", "size": 10, "color": "navy"}])
    styles = _of(reqs, "updateTextStyle")
    assert styles[0]["textRange"] == {"type": "ALL"} and "fontFamily" in styles[0]["fields"]  # base first
    for s in styles[1:]:
        assert s["fields"] != "*" and s["style"], s  # only the fields the writer really sets
        assert set(s["fields"].split(",")) == set(s["style"])
    assert any(s["style"].get("bold") for s in styles[1:])


def test_pie_spokes_start_at_the_centre():
    reqs, _ = _run([{"op": "ring", "cx": 70, "cy": 70, "r": 70, "thickness": 70,
                     "segments": [{"value": 1, "color": "mint"}, {"value": 1, "color": "navy"}]}])
    lines = _of(reqs, "createLine")
    assert len(lines) == 360
    for ln in lines:  # every spoke's start point is the centre
        t = ln["elementProperties"]["transform"]
        assert abs(t["translateX"] / PT - 70) < 0.01 and abs(t["translateY"] / PT - 70) < 0.01
    weights = {p["lineProperties"]["weight"]["magnitude"] for p in _of(reqs, "updateLineProperties")}
    assert weights == {2.5}


def test_donut_spokes_start_at_the_inner_radius():
    reqs, _ = _run([{"op": "ring", "cx": 70, "cy": 70, "r": 70, "thickness": 20,
                     "segments": [{"value": 1, "color": "mint"}]}])
    lines = _of(reqs, "createLine")
    assert len(lines) == 360
    t = lines[0]["elementProperties"]["transform"]
    dist = ((t["translateX"] / PT - 70) ** 2 + (t["translateY"] / PT - 70) ** 2) ** 0.5
    assert abs(dist - 50) < 0.5


def test_image_cover_crops_to_the_box_when_the_resolver_knows_the_size():
    wide = lambda n, t: ("fid", (1600, 800))   # 2:1 source into a 1.6:1 box → crop left/right
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 160, "h": 100, "asset": "shot", "cover": True}],
                                   THEME, resolve_asset=wide)
    (crop,) = [r["updateImageProperties"] for r in reqs if "updateImageProperties" in r]
    assert crop["imageProperties"]["cropProperties"] == {"leftOffset": pytest.approx(0.1), "rightOffset": pytest.approx(0.1),
                                                          "topOffset": 0.0, "bottomOffset": 0.0}
    assert crop["fields"] == "cropProperties"
    tall = lambda n, t: ("fid", (800, 800))    # square source → crop top/bottom
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 160, "h": 100, "asset": "shot", "cover": True}],
                                   THEME, resolve_asset=tall)
    (crop,) = [r["updateImageProperties"] for r in reqs if "updateImageProperties" in r]
    c = crop["imageProperties"]["cropProperties"]
    assert c["topOffset"] > 0 and c["bottomOffset"] > 0 and c["leftOffset"] == c["rightOffset"] == 0
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 160, "h": 100, "asset": "shot"}],
                                   THEME, resolve_asset=lambda n, t: "fid")
    assert not [r for r in reqs if "updateImageProperties" in r]  # no cover, or unknown size → no crop


# --- lot 4 canvas features -------------------------------------------------------------

HL = Theme(name="h", colors={"mint": "#00F6B5", "navy": "#002B3C"}, roles={"highlight": "mint", "ink": "navy"}, font="Barlow")


def test_markdown_highlight_spans_become_background_color_and_are_stripped():
    reqs, _ = draw.ops_to_requests("s", [{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20,
                                          "markdown": "Un ==mot fort== et **gras ==ici==**\n- ==puce== x"}], HL, prefix="cmp")
    text = "".join(r["insertText"]["text"] for r in reqs if "insertText" in r)
    assert text == "Un mot fort et gras ici\n\tpuce x"
    assert "\ue000" not in text and "\ue001" not in text
    idx = [r["insertText"]["insertionIndex"] for r in reqs if "insertText" in r]
    assert idx == sorted(idx) and idx[0] == 0
    bg = [r["updateTextStyle"] for r in reqs if "updateTextStyle" in r and "backgroundColor" in r["updateTextStyle"]["style"]]
    ranges = [(b["textRange"]["startIndex"], b["textRange"]["endIndex"]) for b in bg]
    assert ranges == [(3, 11), (20, 23), (25, 29)]
    assert bg[0]["fields"] == "backgroundColor"
    assert bg[0]["style"]["backgroundColor"]["opaqueColor"]["rgbColor"] == {"red": 0, "green": 246 / 255, "blue": 181 / 255}
    bold = next(r["updateTextStyle"] for r in reqs if "updateTextStyle" in r and r["updateTextStyle"]["style"].get("bold"))
    assert (bold["textRange"]["startIndex"], bold["textRange"]["endIndex"]) == (15, 23)  # shifted past the stripped marks
    bullets = next(r["createParagraphBullets"] for r in reqs if "createParagraphBullets" in r)
    assert (bullets["textRange"]["startIndex"], bullets["textRange"]["endIndex"]) == (24, 31)


def test_runs_highlight_key_and_custom_highlight_color():
    reqs, _ = draw.ops_to_requests("s", [{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20,
                                          "runs": [[{"text": "A "}, {"text": "B", "highlight": "#FF0000"}]]}], HL, prefix="cmp")
    bg = [r["updateTextStyle"] for r in reqs if "updateTextStyle" in r and "backgroundColor" in r["updateTextStyle"]["style"]]
    assert len(bg) == 1 and bg[0]["textRange"]["startIndex"] == 2 and bg[0]["style"]["backgroundColor"]["opaqueColor"]["rgbColor"]["red"] == 1
    reqs, _ = draw.ops_to_requests("s", [{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "markdown": "==x==", "highlight": "navy"}], HL, prefix="cmp")
    bg = [r["updateTextStyle"] for r in reqs if "updateTextStyle" in r and "backgroundColor" in r["updateTextStyle"]["style"]]
    assert bg[0]["style"]["backgroundColor"]["opaqueColor"]["rgbColor"]["red"] == 0


def test_ring_span_limits_the_segments_to_a_partial_arc():
    reqs, _ = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 10, "start": 180, "span": 180,
                     "segments": [{"value": 1, "color": "mint"}, {"value": 1, "color": "navy"}]}])
    lines = _of(reqs, "createLine")
    assert 175 <= len(lines) <= 185  # half a turn of 1° spokes
    ys = [c["elementProperties"]["transform"]["translateY"] / PT for c in lines]
    assert max(ys) <= 50.5  # everything sits in the upper half


def test_line_and_polyline_arrowheads():
    reqs, _ = _run([{"op": "line", "x1": 0, "y1": 0, "x2": 50, "y2": 0, "color": "mint", "end_arrow": "arrow", "start_arrow": "dot"}])
    (props,) = _of(reqs, "updateLineProperties")
    assert props["lineProperties"]["endArrow"] == "FILL_ARROW" and props["lineProperties"]["startArrow"] == "FILL_CIRCLE"
    assert "endArrow" in props["fields"] and "startArrow" in props["fields"]
    reqs, _ = _run([{"op": "polyline", "points": [[0, 0], [10, 0], [10, 10]], "color": "mint", "end_arrow": "arrow"}])
    props = _of(reqs, "updateLineProperties")
    assert "endArrow" not in props[0]["lineProperties"] and props[1]["lineProperties"]["endArrow"] == "FILL_ARROW"


def test_image_contain_shrinks_the_box_to_the_source_aspect():
    wide = lambda n, t: ("fid", (200, 100))
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 10, "y": 10, "w": 100, "h": 100, "asset": "logo", "contain": True}],
                                   THEME, resolve_asset=wide)
    (img,) = _of(reqs, "createImage")
    size, tr = img["elementProperties"]["size"], img["elementProperties"]["transform"]
    assert size["width"]["magnitude"] == 100 * PT and size["height"]["magnitude"] == 50 * PT
    assert tr["translateX"] == 10 * PT and tr["translateY"] == 35 * PT  # centred vertically
    assert not _of(reqs, "updateImageProperties")


def test_runs_and_overrides_respect_the_theme_size_floor():
    from gslides_mcp import themes as T
    peri = T.load("periscope")
    reqs, _ = draw.ops_to_requests("s", [{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "style": "body", "size": 8,
                                          "runs": [[{"text": "a", "size": 7}, {"text": "b"}]]}], peri, prefix="cmp")
    sizes = [r["updateTextStyle"]["style"]["fontSize"]["magnitude"] for r in reqs if "updateTextStyle" in r and "fontSize" in r["updateTextStyle"]["style"]]
    assert sizes == [11, 11]
    reqs, _ = _run([{"op": "text", "x": 0, "y": 0, "w": 100, "h": 20, "size": 6, "text": "t", "color": "mint"}])  # theme without rules
    assert [r["updateTextStyle"]["style"]["fontSize"]["magnitude"] for r in reqs if "updateTextStyle" in r] == [6]


def test_box_outline_dash_style():
    reqs, _ = _run([{"op": "box", "x": 0, "y": 0, "w": 50, "h": 20, "line": {"color": "navy", "weight": 1, "dash": "DASH"}}])
    (props,) = _of(reqs, "updateShapeProperties")
    assert props["shapeProperties"]["outline"]["dashStyle"] == "DASH"
    reqs, _ = _run([{"op": "box", "x": 0, "y": 0, "w": 50, "h": 20, "line": {"color": "navy"}}])
    assert "dashStyle" not in _of(reqs, "updateShapeProperties")[0]["shapeProperties"]["outline"]


def test_table_row_heights_per_row():
    reqs, _ = _run([{"op": "table", "x": 0, "y": 0, "w": 200, "row_h": 20, "row_heights": [20, 60, 20],
                     "rows": [["a", "b"], ["c", "d"], ["e", "f"]], "borders": {"color": "navy", "weight": 1}}])
    (create,) = _of(reqs, "createTable")
    assert create["elementProperties"]["size"]["height"]["magnitude"] == 100 * PT
    rows = _of(reqs, "updateTableRowProperties")
    heights = {tuple(r["rowIndices"]): r["tableRowProperties"]["minRowHeight"]["magnitude"] for r in rows}
    assert heights == {(0, 2): 20 * PT, (1,): 60 * PT}
