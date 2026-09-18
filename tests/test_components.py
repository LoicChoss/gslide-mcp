"""Built-in components: registry, prop validation, and what each one draws."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=300, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    # every component must produce ops the canvas accepts, with theme roles only
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp")
    assert reqs and ids
    return ops, height


def _of(ops, kind):
    return [o for o in ops if o["op"] == kind]


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


# --- registry ------------------------------------------------------------------

def test_catalogue_lists_builtins_with_prop_schemas():
    cat = {c["name"]: c for c in components.catalogue()}
    for name in ("kpi", "kpi_grid", "card", "callout", "badge", "steps", "quote", "table",
                 "chart_bars", "chart_line", "donut"):
        assert name in cat, name
        entry = cat[name]
        assert entry["description"] and entry["source"] == "builtin"
        assert entry["example"]["props"]
        assert all({"name", "type", "description"} <= set(p) for p in entry["props"])
    card = cat["card"]
    variant = next(p for p in card["props"] if p["name"] == "variant")
    assert variant["type"] == "choice" and "dark" in variant["choices"] and variant["default"] == "light"


def test_unknown_component_and_bad_props_are_named():
    with pytest.raises(ValueError, match="'nope'"):
        components.render("nope", {}, PERISCOPE, 100)
    with pytest.raises(ValueError, match="'valeu'.*value"):
        components.render("kpi", {"valeu": "12"}, PERISCOPE, 100)
    with pytest.raises(ValueError, match="required.*value"):
        components.render("kpi", {"label": "x"}, PERISCOPE, 100)
    with pytest.raises(ValueError, match="variant.*light"):
        components.render("card", {"variant": "neon"}, PERISCOPE, 100)


def test_every_example_renders():
    for entry in components.catalogue():
        components.render(entry["name"], entry["example"]["props"], PERISCOPE, 320)


# --- kpi ------------------------------------------------------------------------

def test_kpi_bar_value_label_and_signed_delta():
    ops, height = _render("kpi", {"value": "1 625 394", "label": "Impressions", "delta": "-66,57 %"})
    bar = _of(ops, "box")[0]
    assert bar["fill"] == "accent" and bar["w"] < 8
    texts = _of(ops, "text")
    assert [t["style"] for t in texts] == ["kpi_value", "kpi_label", "kpi_delta"]
    assert texts[2]["color"] == "negative"
    assert height > 60
    ops, _ = _render("kpi", {"value": "12", "label": "x", "delta": "+3 %"})
    assert _of(ops, "text")[2]["color"] == "positive"


def test_kpi_dark_switches_text_to_on_dark():
    ops, _ = _render("kpi", {"value": "12", "label": "x", "dark": True})
    assert all(t["color"] == "on_dark" for t in _of(ops, "text"))


def test_kpi_grid_lays_items_out_in_columns():
    items = [{"value": str(i), "label": f"l{i}"} for i in range(4)]
    ops, height = _render("kpi_grid", {"items": items, "cols": 2}, w=400)
    bars = _of(ops, "box")
    assert len(bars) == 4
    assert bars[0]["x"] == bars[2]["x"] and bars[1]["x"] == bars[3]["x"]
    assert bars[0]["y"] < bars[2]["y"] and bars[1]["x"] == pytest.approx(200, abs=1)
    assert height > bars[2]["y"]


# --- card / callout / badge / steps / quote --------------------------------------

@pytest.mark.parametrize("variant, fill, line", [
    ("light", "surface", None), ("dark", "surface_dark", None), ("mint", "accent", None),
    ("acid", "accent_alt", None), ("outline", None, "accent"),
])
def test_card_variants_map_to_theme_roles(variant, fill, line):
    ops, _ = _render("card", {"variant": variant, "title": "T", "body": "b"}, h=120)
    bg = _of(ops, "box")[0]
    assert bg["fill"] == fill
    assert (bg.get("line") or {}).get("color") == line
    assert bg["h"] == 120


def test_card_stacks_label_big_title_body_and_number():
    ops, height = _render("card", {"label": "LABEL", "big": "42 %", "num": "01", "title": "Titre", "body": "- a\n- b", "dot": True})
    texts = _of(ops, "text")
    styles = [t["style"] for t in texts]
    assert styles == ["card_num", "card_label", "card_big", "card_title", "card_body"]
    ys = [t["y"] for t in texts[1:]]
    assert ys == sorted(ys)
    assert any(o["op"] == "box" and o.get("shape") == "ELLIPSE" for o in ops)  # the dot
    assert "- a\n- b" in _texts(ops)
    assert height >= texts[-1]["y"] + texts[-1]["h"]


@pytest.mark.parametrize("kind", ["info", "idea", "warn", "alert", "dark"])
def test_callout_uses_per_type_roles(kind):
    ops, _ = _render("callout", {"type": kind, "title": "Titre", "body": "Corps"})
    bg, bar = _of(ops, "box")[:2]
    assert bg["fill"] == f"callout_{kind}_bg" and bar["fill"] == f"callout_{kind}_bar"
    assert bar["w"] < 6
    title = _of(ops, "text")[0]
    assert title["color"] == f"callout_{kind}_title"


def test_badge_is_a_small_filled_box_with_uppercase_text():
    ops, height = _render("badge", {"text": "Priorité haute"})
    (box,) = _of(ops, "box")
    assert box["fill"] == "accent" and box["text"] == "PRIORITÉ HAUTE" and box["style"] == "badge"
    assert box["align"] == "CENTER" and box["valign"] == "MIDDLE"
    assert height == box["h"] < 20
    ops, _ = _render("badge", {"text": "x", "fill": "surface_dark", "color": "on_dark"})
    assert _of(ops, "box")[0]["fill"] == "surface_dark"


def test_steps_number_each_item():
    ops, height = _render("steps", {"items": ["Un", "Deux **gras**", "Trois"]})
    circles = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    assert len(circles) == 3 and circles[0]["text"] == "1" and circles[2]["text"] == "3"
    bodies = [o for o in ops if o["op"] == "text"]
    assert [b["markdown"] for b in bodies] == ["Un", "Deux **gras**", "Trois"]
    assert height >= bodies[-1]["y"] + bodies[-1]["h"]


def test_quote_outline_and_author_line():
    ops, _ = _render("quote", {"text": "« Vision »", "author": "Client X", "role": "Directrice"})
    (box,) = _of(ops, "box")
    assert box["fill"] is None and box["line"]["color"] == "accent"
    texts = _of(ops, "text")
    assert texts[0]["style"] == "quote"
    assert texts[1]["runs"][0][0] == {"text": "Client X", "bold": True}
    assert texts[1]["runs"][0][1]["text"] == " — Directrice"


# --- table -----------------------------------------------------------------------

def test_table_component_applies_the_theme_table_style():
    ops, height = _render("table", {"rows": [["Levier", "Budget"], ["Google Ads", "18 000 €"], ["Meta", "12 000 €"]],
                                    "align": [None, "END"], "total_row": True})
    (t,) = _of(ops, "table")
    assert t["header"] == {"fill": "accent", "color": "on_accent", "bold": True}
    assert t["banding"] == ["background", "surface"]
    assert t["first_col_bold"] is True
    assert t["borders"] == {"color": "rule", "weight": 1, "position": "INNER_HORIZONTAL"}
    assert t["align"] == [None, "END"]
    assert t["row_fills"] == {2: "accent"} and t["bold_rows"] == [2]
    assert height == t["row_h"] * 3


# --- charts -----------------------------------------------------------------------

def test_chart_bars_vertical_scales_to_max_and_labels():
    ops, _ = _render("chart_bars", {"labels": ["A", "B", "C"], "values": [10, 40, 20]}, w=300, h=150)
    bars = [o for o in ops if o["op"] == "box" and o.get("role") == "bar"]
    assert len(bars) == 3
    assert bars[1]["h"] > bars[2]["h"] > bars[0]["h"]
    assert all(b["fill"] == "accent" for b in bars)
    assert bars[1]["y"] + bars[1]["h"] == pytest.approx(bars[0]["y"] + bars[0]["h"])  # common baseline
    labels = [o for o in ops if o["op"] == "text" and o["style"] == "chart_label"]
    values = [o for o in ops if o["op"] == "text" and o["style"] == "chart_value"]
    assert [l["text"] for l in labels] == ["A", "B", "C"] and [v["text"] for v in values] == ["10", "40", "20"]
    assert _of(ops, "line")  # baseline


def test_chart_bars_horizontal_has_tracks():
    ops, height = _render("chart_bars", {"labels": ["A", "B"], "values": [1, 3], "horizontal": True, "unit": " %"}, w=300)
    tracks = [o for o in ops if o["op"] == "box" and o.get("role") == "track"]
    bars = [o for o in ops if o["op"] == "box" and o.get("role") == "bar"]
    assert len(tracks) == 2 and len(bars) == 2 and tracks[0]["fill"] == "surface"
    assert bars[1]["w"] == pytest.approx(tracks[1]["w"]) and bars[0]["w"] == pytest.approx(tracks[0]["w"] / 3)
    assert "3 %" in _texts(ops)
    assert height > 0


def test_chart_line_grid_series_markers_and_legend():
    ops, _ = _render("chart_line", {"labels": ["J", "F", "M", "A", "M"], "series": [
        {"name": "2025", "values": [10, 20, 15, 25, 22]},
        {"name": "2026", "values": [12, 14, None, 30, 28], "dash": True}]}, w=400, h=200)
    polylines = _of(ops, "polyline")
    assert len(polylines) == 3  # series 1 whole, series 2 split around the None
    assert polylines[0]["color"] == "series_1" and polylines[1]["color"] == "series_2" and polylines[1]["dash"] == "DASH"
    assert len(_of(ops, "line")) >= 5  # grid + axis
    markers = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    assert len(markers) == 9  # 5 + 4 non-None points
    legend = [o for o in ops if o["op"] == "text" and o["style"] == "legend"]
    assert [l["text"] for l in legend] == ["2025", "2026"]
    axis = [o for o in ops if o["op"] == "text" and o["style"] == "axis"]
    assert axis and axis[0]["align"] == "END"


def test_donut_ring_legend_and_center_text():
    ops, _ = _render("donut", {"segments": [{"label": "Google", "value": 60}, {"label": "Meta", "value": 40}],
                               "center": "100 %"}, w=300, h=160)
    (ring,) = _of(ops, "ring")
    assert [s["color"] for s in ring["segments"]] == ["series_1", "series_2"]
    assert ring["cx"] - ring["r"] >= 0 and ring["cy"] + ring["r"] <= 160
    swatches = [o for o in ops if o["op"] == "box" and o.get("role") == "swatch"]
    assert [s["fill"] for s in swatches] == ["series_1", "series_2"]
    assert "Google" in _texts(ops) and "60 %" in _texts(ops) and "100 %" in _texts(ops)


def test_card_long_title_wraps_and_pushes_the_body_down():
    short, _ = _render("card", {"title": "Titre", "body": "b"}, w=160)
    long_, _ = _render("card", {"title": "Un levier d'engagement durable", "body": "b"}, w=160)
    body_y = lambda ops: next(o for o in ops if o["op"] == "text" and o["style"] == "card_body")["y"]
    title = next(o for o in long_ if o["op"] == "text" and o["style"] == "card_title")
    assert body_y(long_) > body_y(short)
    assert body_y(long_) >= title["y"] + title["h"]
