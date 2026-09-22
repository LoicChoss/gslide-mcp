"""Bilan média lot: shared chart style (pptx reference), chart_grouped, donut_row,
mini_charts, kpi notes / rows, table icons & delta columns, reporting blocks,
ad_scoreboard, gallery, media_plan, timeline_arrow."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.components import axes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None, theme=PERISCOPE):
    ops, height = components.render(name, props, theme, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, theme, prefix="cmp")
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def _texts(ops):
    return [o["text"] for o in ops if o["op"] == "text" and "text" in o]


# --- shared chart furniture ---------------------------------------------------------------

def test_thin_labels_keeps_first_and_last_and_drops_neighbours():
    labels = [f"{d:02d}/12" for d in range(1, 32)]
    kept = axes.thin_labels(labels, slot=12, size=10)
    assert len(kept) == 31 and kept[0] == "01/12" and kept[-1] == "31/12"
    shown = [i for i, lb in enumerate(kept) if lb]
    assert 2 < len(shown) < 16 and all(b - a >= 3 for a, b in zip(shown, shown[1:]))
    assert axes.thin_labels(["a", "b", "c"], slot=100, size=10) == ["a", "b", "c"]  # room for all


def test_legend_ops_centred_on_top_and_left_at_bottom():
    entries = [{"name": "Dépenses", "color": "accent"}, {"name": "Collecte", "color": "regie_meta", "kind": "line"}]
    top, h = axes.legend_ops(entries, 0, 0, 600, "top")
    texts = [o for o in top if o["op"] == "text"]
    assert [t["text"] for t in texts] == ["Dépenses", "Collecte"] and h == axes.LEGEND_H
    assert texts[0]["x"] > 100 and _of(top, "line") and _of(top, "box", "swatch")[0]["fill"] == "accent"
    bottom, _ = axes.legend_ops(entries, 0, 0, 600, "bottom")
    assert [o for o in bottom if o["op"] == "box"][0]["x"] == 0
    assert axes.legend_ops(entries, 0, 0, 600, "none") == ([], 0.0)


def test_panelize_adds_a_surface_box_and_a_title_and_shifts_ops():
    ops = [{"op": "box", "x": 0, "y": 0, "w": 100, "h": 50, "fill": "accent"}]
    out, h = axes.panelize(ops, 50, 200, {"title": "ROAS par régie", "panel": True})
    (panel,) = _of(out, "box", "panel")
    assert panel["fill"] == "surface" and panel["w"] == 200 and panel["h"] == h and panel["shape"] == "ROUND_RECTANGLE"
    (title,) = _of(out, "text", "chart_title")
    assert title["text"] == "ROAS par régie" and title["align"] == "CENTER"
    inner = [o for o in out if o.get("fill") == "accent"][0]
    assert inner["x"] == axes.PANEL_PAD and inner["y"] > title["y"]
    same, h0 = axes.panelize(ops, 50, 200, {"title": None, "panel": False})
    assert same == ops and h0 == 50
    assert axes.inner_width(200, {"panel": True}) == 200 - 2 * axes.PANEL_PAD


# --- restyled charts ---------------------------------------------------------------------

def test_chart_combo_pptx_style_legend_top_thin_line_auto_markers_and_values():
    labels = [f"{d:02d}/12" for d in range(1, 32)]
    props = {"labels": labels, "bars": {"name": "Dépenses", "values": [1000 + 30 * i for i in range(31)]},
             "line": {"name": "Collecte GA4", "values": [600 + 50 * i for i in range(31)], "color": "regie_meta"}, "unit": "€"}
    ops, height = _render("chart_combo", props, w=800, h=260)
    (line,) = _of(ops, "polyline", "line")
    assert line["weight"] == axes.LINE_W and line["color"] == "regie_meta"
    assert not _of(ops, "box", "marker") and not _of(ops, "text", "bar_value")  # 31 points: auto off
    legend = [o for o in ops if o["op"] == "text" and o.get("style") == "legend"]
    assert legend and legend[0]["y"] < _of(ops, "box", "bar")[0]["y"]  # legend on top
    grid = _of(ops, "line", "grid")
    assert grid and grid[0]["weight"] == axes.GRID_W and grid[0]["color"] == "chart_grid"
    (base,) = _of(ops, "line", "baseline")
    assert base["color"] == "chart_axis"
    shown = [t for t in _of(ops, "text", "label") if t["text"]]
    assert 3 <= len(shown) < 31 and shown[0]["text"] == "01/12" and shown[-1]["text"] == "31/12"
    small, _ = _render("chart_combo", {"labels": ["a", "b", "c"], "bars": {"values": [1, 2, 3]}, "line": {"values": [3, 2, 1]}})
    assert len(_of(small, "box", "marker")) == 3 and _of(small, "box", "marker")[0]["w"] == axes.MARKER
    assert len(_of(small, "text", "point_value")) == 3
    forced, _ = _render("chart_combo", {"labels": ["a", "b"], "bars": {"values": [1, 2]}, "line": {"values": [3, 2]},
                                        "markers": False, "show_values": False, "legend_pos": "none"})
    assert not _of(forced, "box", "marker") and not [o for o in forced if o.get("style") == "legend"]


def test_chart_bars_per_bar_colors_title_and_panel():
    ops, h = _render("chart_bars", {"labels": ["Google", "Bing", "Meta"], "values": [3.9, 2.5, 3.45],
                                    "colors": ["regie_google", "regie_bing", "regie_meta"], "y_axis": True,
                                    "title": "ROAS par régie", "panel": True}, w=300, h=180)
    bars = _of(ops, "box", "bar")
    assert [b["fill"] for b in bars] == ["regie_google", "regie_bing", "regie_meta"]
    (panel,) = _of(ops, "box", "panel")
    assert panel["w"] == 300 and h == panel["h"] == 180
    assert _of(ops, "text", "chart_title")[0]["text"] == "ROAS par régie"
    assert all(panel["x"] < b["x"] and b["x"] + b["w"] < panel["w"] for b in bars)
    (base,) = _of(ops, "line", "baseline")
    assert base["color"] == "chart_axis" and base["weight"] == axes.AXIS_W


def test_chart_line_thin_lines_small_markers_light_grid():
    ops, _ = _render("chart_line", {"labels": ["J", "F", "M"], "series": [{"name": "a", "values": [1, 2, 3]}]}, w=300, h=150)
    (line,) = _of(ops, "polyline")
    assert line["weight"] == axes.LINE_W
    markers = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    assert markers[0]["w"] == axes.MARKER
    grid = [o for o in _of(ops, "line") if o.get("role") == "grid"]
    assert grid and grid[0]["weight"] == axes.GRID_W and _of(ops, "line", "baseline")[0]["color"] == "chart_axis"


def test_chart_stacked_legend_pos_and_light_baseline():
    ops, _ = _render("chart_stacked", {"labels": ["A", "B"], "horizontal": False, "legend_pos": "top",
                                       "series": [{"name": "s1", "values": [1, 2]}, {"name": "s2", "values": [2, 1]}]}, w=300, h=180)
    legend = [o for o in ops if o.get("style") == "legend"]
    assert legend[0]["y"] < _of(ops, "box", "segment")[0]["y"]
    assert _of(ops, "line", "baseline")[0]["color"] == "chart_axis"


def test_donut_segment_labels_and_bottom_legend():
    ops, h = _render("donut", {"segments": [{"label": "Google", "value": 74, "color": "regie_google"},
                                            {"label": "Bing", "value": 8, "color": "regie_bing"},
                                            {"label": "Meta", "value": 3, "color": "regie_meta"},
                                            {"label": "Autres", "value": 15, "color": "navy"}],
                               "labels": True, "legend_pos": "bottom", "title": "Nb de dons"}, w=200, h=200)
    seg_labels = _of(ops, "text", "segment_label")
    assert [t["text"] for t in seg_labels] == ["74 %", "8 %", "15 %"]  # 3 % is too small to label
    assert seg_labels[0]["color"] == "ink" and seg_labels[-1]["color"] == "on_dark"  # mint vs navy
    (ring,) = _of(ops, "ring")
    assert abs(seg_labels[0]["x"] + seg_labels[0]["w"] / 2 - ring["cx"]) < ring["r"]  # inside the ring
    legend = [o for o in ops if o.get("style") == "legend"]
    assert legend and legend[0]["y"] > ring["cy"] + ring["r"]  # below the ring
    assert _of(ops, "text", "chart_title")[0]["text"] == "Nb de dons"
    default, _ = _render("donut", {"segments": [{"label": "a", "value": 1}, {"label": "b", "value": 1}]})
    assert not _of(default, "text", "segment_label")


# --- chart_grouped / donut_row / mini_charts ------------------------------------------------

def test_chart_grouped_vertical_category_tints_and_legend_top():
    props = {"labels": ["Google", "Bing", "Facebook"], "unit": "€",
             "series": [{"name": "Collecte N", "values": [356118, 35079, 60007]}, {"name": "Collecte N-1", "values": [0, 47353, 36090]}],
             "category_colors": ["regie_google", "regie_bing", "regie_facebook"]}
    ops, height = _render("chart_grouped", props, w=500, h=220)
    bars = _of(ops, "box", "bar")
    assert len(bars) == 6
    n_series = [b for b in bars if b["series"] == 0]
    prev = [b for b in bars if b["series"] == 1]
    assert [b["fill"] for b in n_series] == ["regie_google", "regie_bing", "regie_facebook"]
    assert all(pv["fill"].startswith("#") for pv in prev)  # lighter tint of the category colour
    assert n_series[0]["x"] < prev[0]["x"] < n_series[1]["x"]  # side by side inside the category slot
    assert bars[1]["h"] == 0 and n_series[0]["h"] > n_series[2]["h"]
    values = [t["text"] for t in _of(ops, "text", "value")]
    assert values[0] == "356 118 €" and values[1] == "0 €"
    legend = [o for o in ops if o.get("style") == "legend"]
    assert [l["text"] for l in legend] == ["Collecte N", "Collecte N-1"] and legend[0]["y"] < n_series[0]["y"]
    assert _of(ops, "line", "baseline") and _of(ops, "text", "tick") and height == 220


def test_chart_grouped_horizontal_and_series_colors():
    props = {"labels": ["Paid Search", "Email"], "horizontal": True,
             "series": [{"name": "N", "values": [219545, 155800], "color": "navy"}, {"name": "N-1", "values": [223773, 112738], "color": "cyan"}]}
    ops, height = _render("chart_grouped", props, w=400)
    bars = _of(ops, "box", "bar")
    assert [b["fill"] for b in bars] == ["navy", "cyan", "navy", "cyan"]
    assert bars[0]["y"] < bars[1]["y"] < bars[2]["y"] and bars[0]["x"] == bars[1]["x"]
    assert bars[0]["w"] / bars[1]["w"] == pytest.approx(219545 / 223773)
    labels = [t["text"] for t in _of(ops, "text", "label")]
    assert labels == ["Paid Search", "Email"] and height > 0
    assert _of(ops, "text", "value")[0]["x"] > bars[0]["x"] + bars[0]["w"]


def test_donut_row_repeats_donuts_with_titles_and_bottom_legends():
    items = [{"title": "Impressions", "segments": [{"label": "Google", "value": 13}, {"label": "Facebook", "value": 78}]},
             {"title": "Clics", "segments": [{"label": "Google", "value": 62}, {"label": "Facebook", "value": 28}]},
             {"title": "Dépenses", "segments": [{"label": "Google", "value": 70}, {"label": "Facebook", "value": 13}]}]
    ops, height = _render("donut_row", {"items": items, "colors": ["regie_google", "regie_facebook"]}, w=600, h=200)
    rings = _of(ops, "ring")
    assert len(rings) == 3 and rings[0]["cx"] < rings[1]["cx"] < rings[2]["cx"]
    assert [s["color"] for s in rings[0]["segments"]] == ["regie_google", "regie_facebook"]
    titles = [t["text"] for t in _of(ops, "text", "chart_title")]
    assert titles == ["Impressions", "Clics", "Dépenses"]
    assert len(_of(ops, "text", "segment_label")) == 6
    legend = [o for o in ops if o.get("style") == "legend"]
    assert len(legend) == 6 and legend[0]["y"] > rings[0]["cy"] + rings[0]["r"]
    assert height == 200


def test_mini_charts_share_categories_and_colours():
    props = {"labels": ["Google", "Bing"], "colors": ["regie_google", "regie_bing"],
             "charts": [{"title": "Impressions", "values": [2439153, 150851]}, {"title": "Clics", "values": [62579, 5627]},
                        {"title": "Collecte GA4", "values": [178175, 18448], "unit": "€"}, {"title": "ROAS GA4", "values": [1.95, 1.32]},
                        {"title": "Dépenses", "values": [91244, 14014], "unit": "€"}]}
    ops, height = _render("mini_charts", props, w=800, h=180)
    bars = _of(ops, "box", "bar")
    assert len(bars) == 10 and [b["fill"] for b in bars[:2]] == ["regie_google", "regie_bing"]
    titles = [t["text"] for t in _of(ops, "text", "chart_title")]
    assert titles == ["Impressions", "Clics", "Collecte GA4", "ROAS GA4", "Dépenses"]
    xs = sorted({round(b["x"]) for b in bars})
    assert xs[0] < xs[2] < xs[4] < xs[6] < xs[8]
    values = [t["text"] for t in _of(ops, "text", "value")]
    assert "178 175 €" in values and "1,95" in values and "2 439 153" in values
    assert len(_of(ops, "text", "tick")) == 25  # a graduated axis per mini chart
    assert height == 180
