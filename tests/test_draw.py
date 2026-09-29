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


def test_ring_spokes_cover_the_full_circle_in_order():
    reqs, ids = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 20, "render": "spokes",
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
    reqs, _ = _run([{"op": "ring", "cx": 70, "cy": 70, "r": 70, "thickness": 70, "render": "spokes",
                     "segments": [{"value": 1, "color": "mint"}, {"value": 1, "color": "navy"}]}])
    lines = _of(reqs, "createLine")
    assert len(lines) == 360
    for ln in lines:  # every spoke's start point is the centre
        t = ln["elementProperties"]["transform"]
        assert abs(t["translateX"] / PT - 70) < 0.01 and abs(t["translateY"] / PT - 70) < 0.01
    weights = {p["lineProperties"]["weight"]["magnitude"] for p in _of(reqs, "updateLineProperties")}
    assert weights == {2.5}


def test_donut_spokes_start_at_the_inner_radius():
    reqs, _ = _run([{"op": "ring", "cx": 70, "cy": 70, "r": 70, "thickness": 20, "render": "spokes",
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


def test_ring_span_limits_the_spokes_to_a_partial_arc():
    reqs, _ = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 10, "start": 180, "span": 180, "render": "spokes",
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


def test_small_box_text_goes_into_a_centred_overlay():
    """A numbered 18 pt disc: the shape carries no text, a 48 × 30 text box centred on it does."""
    reqs, ids = _run([{"op": "box", "x": 10, "y": 20, "w": 18, "h": 18, "shape": "ELLIPSE", "fill": "mint",
                       "text": "3", "size": 9, "bold": True, "align": "CENTER", "valign": "MIDDLE"}])
    shapes = [r["createShape"] for r in reqs if "createShape" in r]
    assert [s["shapeType"] for s in shapes] == ["ELLIPSE", "TEXT_BOX"]
    box = shapes[1]["elementProperties"]
    assert box["size"]["width"]["magnitude"] == 48 * 12700 and box["size"]["height"]["magnitude"] == 30 * 12700
    assert box["transform"]["translateX"] == round((10 - 15) * 12700) and box["transform"]["translateY"] == round((20 - 6) * 12700)
    inserts = [r["insertText"] for r in reqs if "insertText" in r]
    assert len(inserts) == 1 and inserts[0]["objectId"] == shapes[1]["objectId"] and inserts[0]["text"] == "3"
    big, _ = _run([{"op": "box", "x": 0, "y": 0, "w": 120, "h": 40, "text": "wide"}])
    assert [r["createShape"]["shapeType"] for r in big if "createShape" in r] == ["RECTANGLE"]


# --- ring as quarter-turn arcs ------------------------------------------------------

def _arcs(reqs):
    shapes = [c for c in _of(reqs, "createShape") if c["shapeType"] == "ARC"]
    props = {u["objectId"]: u["shapeProperties"] for u in _of(reqs, "updateShapeProperties")}
    return shapes, props


def test_donut_is_a_handful_of_arcs_stroked_as_thick_as_the_ring():
    reqs, ids = _run([{"op": "ring", "cx": 100, "cy": 100, "r": 80, "thickness": 30,
                       "segments": [{"value": 62, "color": "mint"}, {"value": 25, "color": "navy"}, {"value": 13, "color": "#FF9170"}]}])
    shapes, props = _arcs(reqs)
    assert len(ids) == len(shapes) <= 8 and not _of(reqs, "createLine")
    for sh in shapes:
        size = sh["elementProperties"]["size"]["width"]["magnitude"] / PT
        assert size == pytest.approx(2 * 65, abs=0.01)  # the stroke is centred on r_mid = 80 - 30 / 2
        t = sh["elementProperties"]["transform"]
        assert t["scaleX"] ** 2 + t["shearY"] ** 2 == pytest.approx(1)  # a pure rotation
        # the box centre lands on the ring's centre
        cx = t["translateX"] / PT + t["scaleX"] * 65 + t["shearX"] * 65
        cy = t["translateY"] / PT + t["shearY"] * 65 + t["scaleY"] * 65
        assert (cx, cy) == (pytest.approx(100, abs=0.01), pytest.approx(100, abs=0.01))
        outline = props[sh["objectId"]]["outline"]
        assert outline["weight"]["magnitude"] == 30
        assert props[sh["objectId"]]["shapeBackgroundFill"] == {"propertyState": "NOT_RENDERED"}
    # the largest share is painted last, so nothing lies on top of it
    last = props[shapes[-1]["objectId"]]["outline"]["outlineFill"]["solidFill"]["color"]["rgbColor"]
    assert last == THEME.color("mint")


def test_quarter_arc_rotation_matches_the_preset():
    # the ARC preset covers top → right (270° → 360°); an arc starting at 0° (east) turns it by 90°
    reqs, _ = _run([{"op": "ring", "cx": 0, "cy": 0, "r": 10, "thickness": 4,
                     "segments": [{"value": 1, "color": "mint"}], "start": 0}])
    shapes, _ = _arcs(reqs)
    first = shapes[0]["elementProperties"]["transform"]
    assert first["scaleX"] == pytest.approx(0, abs=0.02) and first["shearY"] == pytest.approx(1, abs=1e-3)  # less the 0.6° seam


def test_pie_arcs_reach_the_centre():
    reqs, _ = _run([{"op": "ring", "cx": 70, "cy": 70, "r": 70, "thickness": 70,
                     "segments": [{"value": 1, "color": "mint"}, {"value": 1, "color": "navy"}]}])
    shapes, props = _arcs(reqs)
    assert all(s["elementProperties"]["size"]["width"]["magnitude"] / PT == pytest.approx(70) for s in shapes)
    assert {p["outline"]["weight"]["magnitude"] for p in props.values()} == {70}


def test_arc_plan_puts_the_largest_share_last_and_checks_itself():
    shares = [("a", -90, 18), ("b", 18, 108), ("c", 108, 270)]
    plan = draw.arc_plan(shares)
    assert [p[1] for p in plan][-1] == "c" and all(p[0] == "arc" for p in plan)
    assert all(p[3] - p[2] == pytest.approx(90) for p in plan)
    assert draw._plan_shows(shares, plan)
    assert not draw._plan_shows(shares, [("arc", "c", -90, 270)])


def test_arc_plan_even_small_shares_top_with_spokes():
    shares = [(f"s{i}", -90 + 72 * i, -18 + 72 * i) for i in range(5)]  # five shares of 72°
    plan = draw.arc_plan(shares)
    assert [p[0] for p in plan].count("spokes") == 1 and plan[-1][0] == "spokes"
    reqs, ids = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 10,
                       "segments": [{"value": 1, "color": c} for c in ("mint", "navy", "#FF9170", "#E8FF00", "#111418")]}])
    assert len(ids) < 100  # four arcs and one share of spokes, not 360 spokes


def test_gauge_arcs_stay_inside_the_half_turn():
    reqs, ids = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 10, "start": 180, "span": 180,
                       "segments": [{"value": 43, "color": "mint"}, {"value": 57, "color": "#F2F4F4"}]}])
    shapes, _ = _arcs(reqs)
    assert 0 < len(shapes) == len(ids) <= 4
    plan = draw.arc_plan([("m", 180, 257.4), ("t", 257.4, 360)], span=180)
    assert all(180 - 1e-9 <= p[2] and p[3] <= 360 + 1e-9 for p in plan)


def test_partial_ring_without_an_exact_plan_falls_back_to_spokes():
    # a 50° share near the gauge's end can neither overshoot past it nor be laid back over the first share
    assert draw.arc_plan([("m", 180, 300), ("x", 300, 350), ("t", 350, 360)], span=180) is None
    reqs, _ = _run([{"op": "ring", "cx": 50, "cy": 50, "r": 40, "thickness": 10, "start": 180, "span": 180,
                     "segments": [{"value": 120, "color": "mint"}, {"value": 50, "color": "navy"}, {"value": 10, "color": "#F2F4F4"}]}])
    assert _of(reqs, "createLine") and not _arcs(reqs)[0]


# --- image slots -------------------------------------------------------------------

SLOT_COLOURS = {"slot_fill": "#F2F4F4", "slot_line": "#C8D0D0"}


def test_image_slot_without_a_picture_is_the_placeholder_at_the_exact_box():
    seen = []

    def resolve(name, tint=None):
        seen.append(name)
        return "fid_" + name.replace(":", "_"), (400, 224)

    reqs, ids = draw.ops_to_requests("s", [{"op": "image", "x": 10, "y": 20, "w": 100, "h": 56, "slot": True,
                                            **SLOT_COLOURS}], THEME, resolve_asset=resolve)
    (create,) = _of(reqs, "createImage")
    assert seen == ["slot:400x224:f2f4f4:c8d0d0"]
    assert create["url"].endswith("id=fid_slot_400x224_f2f4f4_c8d0d0")
    size = create["elementProperties"]["size"]
    assert size["width"]["magnitude"] == 100 * PT and size["height"]["magnitude"] == 56 * PT
    assert not _of(reqs, "replaceImage") and ids == [create["objectId"]]
    (alt,) = _of(reqs, "updatePageElementAltText")
    assert alt == {"objectId": create["objectId"], "description": "slot:10.0,20.0,100.0,56.0"}
    assert draw.parse_slot_frame(alt["description"]) == (10.0, 20.0, 100.0, 56.0)


def test_image_slot_with_a_picture_swaps_it_in_and_keeps_the_frame():
    resolve = lambda name, tint=None: ("fid_" + name, (10, 10))  # noqa: E731
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 100, "h": 56, "slot": True,
                                          "asset": "post-video", "fit": "crop", **SLOT_COLOURS}], THEME, resolve_asset=resolve)
    (create,) = _of(reqs, "createImage")
    (swap,) = _of(reqs, "replaceImage")
    assert swap == {"imageObjectId": create["objectId"], "imageReplaceMethod": "CENTER_CROP",
                    "url": "https://drive.google.com/uc?export=view&id=fid_post-video"}
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 100, "h": 56, "slot": True,
                                          "url": "https://x/y.png", **SLOT_COLOURS}], THEME, resolve_asset=resolve)
    assert _of(reqs, "replaceImage")[0]["imageReplaceMethod"] == "CENTER_INSIDE"
    assert _of(reqs, "replaceImage")[0]["url"] == "https://x/y.png"


def test_image_slot_needs_an_asset_resolver():
    with pytest.raises(ValueError, match="resolver"):
        draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 10, "h": 10, "slot": True, **SLOT_COLOURS}], THEME)


def test_slot_frame_text_round_trips_and_rejects_other_alt_texts():
    assert draw.parse_slot_frame(draw.slot_frame_text(1, 2.25, 30, 40)) == (1.0, 2.2, 30.0, 40.0)
    for text in (None, "", "Logo du client", "slot:1,2,3", "slot:1,2,0,4", "slot:a,b,c,d"):
        assert draw.parse_slot_frame(text) is None


def test_summarize_topic_skips_slot_frames():
    from gslides_mcp.tools.library import _infer_topic

    slide = {"pageElements": [
        {"objectId": "img", "description": "slot:1.0,2.0,3.0,4.0", "image": {}},
        {"objectId": "t", "description": "Bilan Meta", "shape": {}},
    ]}
    assert _infer_topic(slide) == "Bilan Meta"


# --- readable ids per role ---------------------------------------------------------

def test_named_ids_count_per_role_and_fall_back_to_the_op_kind():
    roles = {}
    ops = [{"op": "box", "x": 0, "y": 0, "w": 60, "h": 40, "role": "value"},
           {"op": "text", "x": 0, "y": 0, "w": 60, "h": 40, "text": "a"},
           {"op": "box", "x": 0, "y": 0, "w": 60, "h": 40, "role": "value"},
           {"op": "line", "x1": 0, "y1": 0, "x2": 10, "y2": 0, "color": "navy", "role": "bad role!"}]
    _, ids = draw.ops_to_requests("s", ops, THEME, prefix="yt_top", named=True, roles_out=roles)
    assert ids == ["yt_top_value_1", "yt_top_text_1", "yt_top_value_2", "yt_top_bad_role__1"]
    assert roles == {"value": ["yt_top_value_1", "yt_top_value_2"], "text": ["yt_top_text_1"],
                     "bad_role_": ["yt_top_bad_role__1"]}


def test_unnamed_ids_are_unchanged_and_roles_still_reported():
    roles = {}
    _, ids = draw.ops_to_requests("s", [{"op": "box", "x": 0, "y": 0, "w": 60, "h": 40, "role": "value"},
                                        {"op": "text", "x": 0, "y": 0, "w": 60, "h": 40, "text": "a"}],
                                  THEME, prefix="cmp", roles_out=roles)
    assert ids == ["cmp_001", "cmp_002"] and roles == {"value": ["cmp_001"], "text": ["cmp_002"]}
