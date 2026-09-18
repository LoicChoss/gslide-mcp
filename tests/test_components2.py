"""Lot 2 built-ins: funnel, timeline, process, hub_spoke, pie, stack, bigstat, stats,
pill, checklist, chevrons, arrows, compare_bars, effort_matrix, bubbles, heatmap."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=400, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp")
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def _texts(ops):
    out = []
    for o in ops:
        if "text" in o:
            out.append(o["text"])
        if "markdown" in o:
            out.append(o["markdown"])
        for para in o.get("runs", []):
            out.extend(r["text"] for r in para)
    return out


def test_lot2_components_are_listed_and_examples_render():
    cat = {c["name"] for c in components.catalogue()}
    for name in ("funnel", "timeline", "process", "hub_spoke", "pie", "stack", "bigstat", "stats",
                 "pill", "checklist", "chevrons", "arrows", "compare_bars", "effort_matrix", "bubbles", "heatmap"):
        assert name in cat, name
    for entry in components.catalogue():
        components.render(entry["name"], entry["example"]["props"], PERISCOPE, 400)


# --- funnel ------------------------------------------------------------------------

def test_funnel_bars_centered_and_scaled_with_pills():
    ops, height = _render("funnel", {"items": [{"label": "Visites", "value": 100}, {"label": "Leads", "value": 60, "sub": "formulaire"},
                                               {"label": "Clients", "value": 30}], "pct": "both"})
    bars = _of(ops, "box", "bar")
    assert len(bars) == 3
    assert bars[1]["w"] == pytest.approx(bars[0]["w"] * 0.6) and bars[2]["w"] == pytest.approx(bars[0]["w"] * 0.3)
    centers = [b["x"] + b["w"] / 2 for b in bars]
    assert centers[0] == pytest.approx(centers[1]) == pytest.approx(centers[2])
    first = [o["text"] for o in _of(ops, "box", "pct_first")]
    prev = [o["text"] for o in _of(ops, "box", "pct_prev")]
    assert first == ["100 %", "60 %", "30 %"] and prev == ["60 %", "50 %"]
    assert _of(ops, "box", "pct_prev")[0]["fill"] is None and _of(ops, "box", "pct_first")[0]["fill"] == "accent"
    assert "formulaire" in _texts(ops) and "% de la 1re étape" in _texts(ops)
    assert height > 3 * 30


def test_funnel_without_pct_has_no_pills_nor_legend():
    ops, height = _render("funnel", {"items": [{"label": "A", "value": 10}, {"label": "B", "value": 5}], "pct": "none", "unit": " k"})
    assert not _of(ops, "box", "pct_first") and "% de la 1re étape" not in _texts(ops)
    assert "10 k" in _texts(ops)
    assert height == 2 * 34


# --- timeline / process / hub_spoke ----------------------------------------------------

def test_timeline_phases_along_a_line():
    ops, _ = _render("timeline", {"phases": [{"date": "T1", "title": "Audit", "text": "Crawl complet"},
                                             {"date": "T2", "title": "Plan", "color": "accent_alt"}, {"date": "T3", "title": "Run"}]})
    assert len(_of(ops, "line")) == 1
    dots = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    assert len(dots) == 3 and dots[1]["fill"] == "accent_alt" and dots[0]["fill"] == "accent"
    assert dots[0]["x"] < dots[1]["x"] < dots[2]["x"]
    assert ["T1", "Audit", "Crawl complet"][0] in _texts(ops) and "Run" in _texts(ops)


def test_process_boxes_and_arrows():
    ops, height = _render("process", {"steps": [{"label": "Audit", "sub": "2 sem."}, {"label": "Plan"}, {"label": "Run", "fill": "surface_dark"}]})
    boxes = _of(ops, "box", "step")
    assert len(boxes) == 3 and boxes[0]["w"] == boxes[1]["w"]
    assert boxes[0]["fill"] == "surface" and boxes[2]["fill"] == "surface_dark"
    arrows = [o for o in ops if o["op"] == "text" and o.get("text") == "→"]
    assert len(arrows) == 2 and boxes[0]["x"] + boxes[0]["w"] <= arrows[0]["x"] + 1 and arrows[0]["x"] + arrows[0]["w"] <= boxes[1]["x"] + 1
    assert "2 sem." in _texts(ops) and height == 100


def test_hub_spoke_lines_under_satellites():
    ops, _ = _render("hub_spoke", {"center": "Site", "sats": [{"label": "SEO"}, {"label": "Ads", "hl": True}, {"label": "Social"}]}, w=400, h=260)
    lines = _of(ops, "line")
    sats = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    hub = [o for o in ops if o["op"] == "box" and o.get("role") == "hub"][0]
    assert len(lines) == 3 and len(sats) == 3
    assert ops.index(lines[0]) < ops.index(sats[0]) < ops.index(hub)  # lines first, hub on top
    assert sats[1]["line"]["color"] == "accent" and sats[0]["line"]["color"] == "ink"
    assert all(0 <= s["x"] and s["x"] + s["w"] <= 400 and 0 <= s["y"] and s["y"] + s["h"] <= 260 for s in sats)
    assert hub["text"] == "Site"


# --- pie / stack -----------------------------------------------------------------------

def test_pie_is_a_full_ring():
    ops, _ = _render("pie", {"segments": [{"label": "A", "value": 1}, {"label": "B", "value": 3}]}, w=300, h=150)
    (ring,) = _of(ops, "ring")
    assert ring["thickness"] == ring["r"]
    assert "75 %" in _texts(ops)


def test_stack_is_centered_and_narrowing():
    ops, height = _render("stack", {"items": [{"label": "Notoriété", "sub": "Haut de funnel"}, {"label": "Considération"}, {"label": "Conversion", "fill": "accent"}]}, w=300)
    boxes = _of(ops, "box", "layer")
    assert len(boxes) == 3 and boxes[0]["w"] > boxes[1]["w"] > boxes[2]["w"]
    assert all(b["x"] + b["w"] / 2 == pytest.approx(150) for b in boxes)
    assert boxes[2]["fill"] == "accent" and boxes[0]["fill"] == "surface_dark"
    assert height == boxes[2]["y"] + boxes[2]["h"]


# --- bigstat / stats / pill --------------------------------------------------------------

def test_bigstat_and_stats_use_stat_styles():
    ops, height = _render("bigstat", {"value": "+42 %", "label": "de trafic organique", "sub": "vs 2025"})
    texts = _of(ops, "text")
    assert [t["style"] for t in texts] == ["stat_value", "stat_label", "caption"]
    assert texts[0]["align"] == "CENTER" and height > 90
    ops, _ = _render("stats", {"items": [{"value": "12", "label": "pays"}, {"value": "3", "label": "langues"}]}, w=300)
    values = [t for t in _of(ops, "text") if t["style"] == "stat_value"]
    assert len(values) == 2 and values[1]["x"] == pytest.approx(150) and values[0]["w"] == pytest.approx(150)


def test_pill_capsule_filled_or_outlined():
    ops, height = _render("pill", {"text": "SEO"})
    (box,) = _of(ops, "box")
    assert box["shape"] == "ROUND_RECTANGLE" and box["fill"] == "accent" and box["text"] == "SEO" and box["color"] == "on_accent"
    assert box["w"] < 100 and height == box["h"]
    ops, _ = _render("pill", {"text": "seo", "outline": True})
    (box,) = _of(ops, "box")
    assert box["fill"] == "background" and box["line"]["color"] == "accent" and box["text"] == "SEO"
    ops, _ = _render("pill", {"text": "x", "color": "surface_dark"})
    assert _of(ops, "box")[0]["color"] == "on_dark"


# --- checklist / chevrons / arrows --------------------------------------------------------

def test_checklist_ticks_done_items():
    ops, height = _render("checklist", {"items": ["Sitemap", {"text": "Robots **ok**", "done": True}]})
    boxes = _of(ops, "box", "check")
    assert len(boxes) == 2 and boxes[0]["fill"] is None and boxes[1]["fill"] == "accent"
    assert len(_of(ops, "polyline")) == 1
    assert [o["markdown"] for o in _of(ops, "text")] == ["Sitemap", "Robots **ok**"]
    assert height >= boxes[1]["y"] + boxes[1]["h"]


@pytest.mark.parametrize("name, marker", [("chevrons", "›"), ("arrows", "→")])
def test_marker_lists_are_one_text_with_styled_prefixes(name, marker):
    ops, height = _render(name, {"items": ["Un", "Deux"]})
    (text,) = _of(ops, "text")
    assert len(text["runs"]) == 2
    prefix = text["runs"][0][0]
    assert prefix["text"].startswith(marker) and prefix["bold"] is True
    assert text["runs"][1][1]["text"] == "Deux"
    assert text["spacing"] == 9 and height > 30
    if name == "chevrons":
        assert prefix["color"] == "positive"


# --- compare_bars / effort_matrix / bubbles / heatmap ---------------------------------------

def test_compare_bars_track_and_fill():
    ops, height = _render("compare_bars", {"bars": [{"label": "Vu", "frac": 0.7}, {"label": "Cliqué", "frac": 0, "color": "accent_alt"}]}, w=200)
    tracks, bars = _of(ops, "box", "track"), _of(ops, "box", "bar")
    assert len(tracks) == 2 and len(bars) == 1 and bars[0]["w"] == pytest.approx(140)
    assert height > tracks[1]["y"]


def test_effort_matrix_axes_and_bubbles():
    ops, _ = _render("effort_matrix", {"bubbles": [{"n": "1", "label": "Maillage", "x": 0.2, "y": 0.8}, {"n": "2", "label": "Refonte", "x": 0.9, "y": 0.6, "fill": "accent_alt", "above": True}]}, w=300, h=200)
    assert len(_of(ops, "line")) == 2
    dots = _of(ops, "box", "bubble")
    assert len(dots) == 2 and dots[0]["x"] < dots[1]["x"] and dots[0]["y"] < dots[1]["y"]  # high impact = top
    assert "Impact" in _texts(ops) and "Effort →" in _texts(ops) and "Refonte" in _texts(ops)


def test_bubbles_scale_and_grid():
    ops, _ = _render("bubbles", {"points": [{"name": "SEO", "x": 10, "y": 50, "size": 100}, {"name": "Ads", "x": 80, "y": 20, "size": 25}]}, w=300, h=200)
    dots = _of(ops, "box", "bubble")
    assert len(dots) == 2 and dots[0]["w"] > dots[1]["w"]
    assert dots[0]["x"] < dots[1]["x"] and dots[0]["y"] < dots[1]["y"]
    assert len(_of(ops, "line")) >= 6 and "SEO" in _texts(ops)


def test_heatmap_bins_cells_into_heat_roles():
    ops, _ = _render("heatmap", {"rows": [["", "Jan", "Fév"], ["SEO", 10, 90], ["Ads", 50, None]]})
    (t,) = _of(ops, "table")
    fills = t["cell_fills"]
    assert fills[(1, 2)] == "heat_4" and fills[(1, 1)] == "heat_1"
    assert (2, 2) not in fills
    assert t["cell_text_colors"][(1, 2)] == "on_dark"
    assert t["rows"][1] == ["SEO", "10", "90"] and t["rows"][2][2] == ""


def test_draw_table_cell_fills_and_text_colors():
    theme = PERISCOPE
    reqs, _ = draw.ops_to_requests("s", [{"op": "table", "x": 0, "y": 0, "w": 100, "rows": [["a", "b"], ["c", "d"]],
                                          "cell_fills": {(1, 1): "accent"}, "cell_text_colors": {(1, 1): "on_accent"}}], theme, prefix="tbl")
    fills = [c for r in reqs for c in [r.get("updateTableCellProperties")] if c]
    assert fills[-1]["tableRange"] == {"location": {"rowIndex": 1, "columnIndex": 1}, "rowSpan": 1, "columnSpan": 1}
    styles = [s for r in reqs for s in [r.get("updateTextStyle")] if s and s["cellLocation"] == {"rowIndex": 1, "columnIndex": 1}]
    assert any(s["style"].get("foregroundColor", {}).get("opaqueColor", {}).get("rgbColor") == theme.color("on_accent") for s in styles)
