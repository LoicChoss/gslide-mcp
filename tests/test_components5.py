"""Chart furniture: graduated Y axis, French values, period dividers, and chart_combo."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.components import axes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp")
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def test_fmt_value_french_thousands_and_glued_unit():
    assert axes.fmt_value(4000000, "€") == "4 000 000 €"
    assert axes.fmt_value(62, "%") == "62 %"
    assert axes.fmt_value(62, " %") == "62 %"
    assert axes.fmt_value(0, None) == "0" and axes.fmt_value(12.5, "") == "12,5"


def test_chart_bars_vertical_axis_and_dividers():
    props = {"labels": ["2015", "2016", "2017", "2018"], "values": [4.1, 4.7, 5.2, 1.9], "unit": "M€", "y_axis": True,
             "dividers": [{"after": "2017", "left": "ISF", "right": "IFI"}], "max": 6}
    ops, height = _render("chart_bars", props, w=600, h=200)
    ticks = _of(ops, "text", "tick")
    assert [t["text"] for t in ticks] == ["1,5 M€", "3 M€", "4,5 M€", "6 M€", "0 M€"]
    grid = _of(ops, "line", "grid")
    assert len(grid) == 4 and grid[0]["x1"] > 40  # plot starts after the axis labels
    bars = _of(ops, "box", "bar")
    assert len(bars) == 4 and bars[0]["x"] >= grid[0]["x1"]
    assert bars[2]["h"] / bars[3]["h"] == pytest.approx(5.2 / 1.9)
    (div,) = _of(ops, "line", "divider")
    assert bars[2]["x"] + bars[2]["w"] < div["x1"] < bars[3]["x"]  # between 2017 and 2018
    labels = _of(ops, "text", "divider_label")
    assert [lb["text"] for lb in labels] == ["ISF", "IFI"] and labels[0]["align"] == "END" and labels[1]["x"] == div["x1"] + 8
    assert _of(ops, "text", "value")[0]["text"] == "4,1 M€"
    ops, _ = _render("chart_bars", {"labels": ["a"], "values": [1]})
    assert not _of(ops, "text", "tick") and not _of(ops, "line", "divider")  # defaults unchanged


def test_chart_stacked_vertical_axis_dividers_and_french_totals():
    props = {"labels": ["2017", "2018", "2019"], "horizontal": False, "y_axis": True, "unit": "€", "show_values": True,
             "series": [{"name": "A", "values": [3800000, 1100000, 1000000]}, {"name": "B", "values": [1400000, 800000, 1800000]}],
             "dividers": [{"after": "2017", "left": "ISF", "right": "IFI"}]}
    ops, height = _render("chart_stacked", props, w=600, h=220)
    assert _of(ops, "text", "tick")[-1]["text"] == "0 €"
    totals = [t["text"] for t in _of(ops, "text", "total")]
    assert totals[0] == "5 200 000 €"
    segs = _of(ops, "box", "segment")
    grid = _of(ops, "line", "grid")
    assert min(s["x"] for s in segs) >= grid[0]["x1"]
    (div,) = _of(ops, "line", "divider")
    assert segs[0]["x"] + segs[0]["w"] < div["x1"] < segs[2]["x"]
    assert len(_of(ops, "box", "swatch")) == 2 and height == 220
    ops, _ = _render("chart_stacked", {"labels": ["a"], "series": [{"name": "s", "values": [1500]}], "show_values": True})
    assert _of(ops, "text", "total")[0]["text"] == "1 500"  # horizontal totals are French too


def test_chart_combo_bars_left_axis_line_right_axis_values_and_legend():
    props = {"labels": ["2024", "2025", "2026"], "bars": {"name": "Collecte", "values": [1152729, 1067244, 708134]},
             "line": {"name": "Dons", "values": [780, 404, None]}, "unit": "€", "y_max": 1500000, "y2_max": 800}
    ops, height = _render("chart_combo", props, w=600, h=240)
    bars = _of(ops, "box", "bar")
    assert len(bars) == 3 and bars[0]["h"] / bars[2]["h"] == pytest.approx(1152729 / 708134)
    left = [t["text"] for t in _of(ops, "text", "tick")]
    right = [t["text"] for t in _of(ops, "text", "tick2")]
    assert left[-2] == "1 500 000 €" and right[-2] == "800" and len(right) == 5
    (line,) = _of(ops, "polyline", "line")
    markers = _of(ops, "box", "marker")
    assert len(line["points"]) == 2 and len(markers) == 2  # None = gap, no marker
    base = _of(ops, "line", "baseline")[0]["y1"]
    top = base - (base - markers[0]["y"] - 4.5)
    assert markers[0]["y"] + 4.5 == pytest.approx(base - (base - _of(ops, "line", "grid")[3]["y1"]) * 780 / 800)
    assert markers[0]["x"] + 4.5 == pytest.approx(bars[0]["x"] + bars[0]["w"] / 2)  # centred on the bar
    assert [t["text"] for t in _of(ops, "text", "bar_value")][0] == "1 152 729 €"
    assert [t["text"] for t in _of(ops, "text", "point_value")] == ["780", "404"]
    assert all(t["color"] == "series_6" for t in _of(ops, "text", "point_value"))
    legend = [o["text"] for o in ops if o["op"] == "text" and o.get("style") == "legend"]
    assert legend == ["Collecte", "Dons"] and height == 240


def test_chart_combo_without_axes_or_values_and_examples_render():
    ops, _ = _render("chart_combo", {"labels": ["a", "b"], "bars": {"values": [1, 2]}, "line": {"values": [3, 4]},
                                     "y_axis": False, "show_values": False, "legend": False})
    assert not _of(ops, "text", "tick") and not _of(ops, "text", "bar_value") and len(_of(ops, "box", "marker")) == 2
    for name in ("chart_bars", "chart_stacked", "chart_combo"):
        entry = next(c for c in components.catalogue() if c["name"] == name)
        for theme in (PERISCOPE, themes.load("default")):
            ops, height = components.render(name, entry["example"]["props"], theme, 600)
            draw.ops_to_requests("s", ops, theme, prefix="cmp")
            assert height > 0
