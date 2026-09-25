"""Workshop / restitution blocks and the table upgrade: score_matrix, ranked_bars, chip_cloud,
quadrant_matrix, next_steps, board_columns, session_plan, attention_points, bar_list; table
dark header, subs, dots, pills, zeros, n/a; badge mono; pill count."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.components.workshop import _num, threshold_color

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None, theme=PERISCOPE):
    ops, height = components.render(name, props, theme, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, theme, prefix="cmp",
                                     resolve_asset=lambda name, tint=None: ("fid_" + name, (120, 120)))
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def test_num_and_threshold_color():
    assert _num("34,71 €") == 34.71 and _num("1 270") == 1270 and _num("0,17 %") == 0.17 and _num("-") is None and _num(3) == 3.0
    t = [{"max": 17, "color": "accent"}, {"max": 30, "color": "accent_alt"}, {"color": "coral"}]
    assert threshold_color(10, t) == "accent" and threshold_color(17, t) == "accent_alt" and threshold_color(31, t) == "coral"
    assert threshold_color(None, t) == "surface"


def test_table_dark_header_subs_dots_pills_zeros_and_na():
    rows = [["Ligne", "Coût", "Contacts", "CPL"], ["Display", "499,39 €", "2", "249,69 €"], ["Vidéo", "252,01 €", "0", "-"], ["Total", "751,40 €", "2", "375,70 €"]]
    ops, height = _render("table", {"rows": rows, "subs": ["Google · Display", None], "dots": ["regie_google", "regie_bing"], "header_fill": "ink",
                                    "total_fill": "surface", "total_row": True, "zero_cols": [2],
                                    "pill_cols": {"3": [{"max": 300, "color": "accent"}, {"color": "coral"}]}}, w=400)
    (t,) = _of(ops, "table")
    assert t["header"] == {"fill": "ink", "color": "on_dark", "bold": True} and t["row_fills"] == {3: "surface"}
    assert t["rows"][1][0] == "" and t["rows"][1][1] == "Display"  # leading dot column
    dots = _of(ops, "box", "dot")
    assert [d["fill"] for d in dots] == ["regie_google", "regie_bing"] and dots[0]["shape"] == "ELLIPSE"
    assert t["cell_runs"][(1, 1)][1][0]["text"] == "Google · Display" and t["row_heights"][1] > t["row_heights"][2]
    assert t["cell_text_colors"][(2, 3)] == "negative"  # a zero contact
    assert t["rows"][2][4] == "–" and t["cell_text_colors"][(2, 4)] == "muted"  # n/a
    pills = _of(ops, "box", "pill")
    assert [pl["text"] for pl in pills] == ["249,69 €"] and pills[0]["fill"] == "accent" and t["rows"][1][4] == ""
    assert t["row_heights"][0] < pills[0]["y"] < sum(t["row_heights"][:2]) and height == sum(t["row_heights"])
    plain, _ = _render("table", {"rows": [["a", "b"], ["c", ""]], "na_text": ""})
    assert plain[0]["rows"][1][1] == "" and plain[0]["header"]["fill"] == "accent"


def test_badge_mono_and_pill_count():
    (mono,), _ = _render("badge", {"text": "signal doux", "mono": True, "fill": "surface", "color": "ink"})
    assert mono["text"] == "signal doux" and mono["font"] == "Roboto Mono" and mono["shape"] == "ROUND_RECTANGLE"
    (pill,), _ = _render("pill", {"text": "CFA, dont CFA 2027", "count": 2})
    assert pill["text"].endswith("×2")
    (one,), _ = _render("pill", {"text": "FDD", "count": 1})
    assert one["text"] == "FDD"


def test_score_matrix_tiles_by_threshold_with_counts_and_legend():
    props = {"columns": ["Qualité", "Délais"], "rows": [{"label": "Sites", "sub": "web", "values": [2.5, 1.5], "counts": [2, 2]},
                                                        {"label": "CRM", "values": [3.7, None]}]}
    ops, h = _render("score_matrix", props, w=600)
    tiles = _of(ops, "box", "tile")
    assert len(tiles) == 4 and tiles[0]["fill"] == "mint_pale" and tiles[1]["fill"] == "coral" and tiles[2]["fill"] == "accent" and tiles[3]["fill"] == "surface"
    assert [s["text"] for s in _of(ops, "text", "score")] == ["2,5", "1,5", "3,7", "–"]
    assert [c["text"] for c in _of(ops, "text", "count")] == ["2 rép.", "2 rép."]
    assert [e["text"] for e in _of(ops, "text", "eyebrow")][0].replace(" ", "") == "FAMILLE DE MISSIONS"
    assert len(_of(ops, "box", "swatch")) == 4 and h > tiles[-1]["y"] + tiles[-1]["h"]


def test_ranked_bars_highlight_the_top_and_show_counts():
    ops, h = _render("ranked_bars", {"eyebrow": "Vos priorités", "items": [{"label": "A", "value": 3}, {"label": "B", "value": 1}, {"label": "C", "value": 0}], "top": 1}, w=500)
    bars = _of(ops, "box", "bar")
    assert len(bars) == 2 and bars[0]["fill"] == "accent" and bars[1]["fill"] == "gray_2" and bars[0]["w"] > bars[1]["w"]
    labels = _of(ops, "text", "label")
    assert labels[0]["bold"] and not labels[1]["bold"]
    assert [c["text"] for c in _of(ops, "text", "count")] == ["3", "1", "0"] and len(_of(ops, "box", "track")) == 3


def test_chip_cloud_wraps_and_counts():
    ops, h = _render("chip_cloud", {"items": [{"text": "CFA 2027", "count": 2}, "Refonte des causes", "Fil rouge", "Campagnes legs", "IA"]}, w=300)
    chips = _of(ops, "box", "chip")
    assert len(chips) == 5 and chips[0]["runs"][0][1]["text"].strip() == "×2" and chips[0]["fill"] == "surface"
    assert max(c["y"] for c in chips) > 0 and all(c["x"] + c["w"] <= 300.01 for c in chips) and h > chips[0]["h"]


def test_quadrant_matrix_highlight_axes_and_items():
    ops, h = _render("quadrant_matrix", {"quadrants": [{"title": "A", "sub": "x"}, {"title": "B", "highlight": True, "items": ["un", "deux"]}, {"title": "C"}, {"title": "D"}]}, w=600)
    quads = _of(ops, "box", "quadrant")
    assert len(quads) == 4 and quads[1]["fill"] == "accent" and quads[0]["fill"] == "surface" and quads[2]["y"] > quads[0]["y"]
    assert [t["text"] for t in _of(ops, "text", "title")] == ["A", "B", "C", "D"] and h == 300
    eyebrows = [e["text"].replace(" ", "") for e in _of(ops, "text", "eyebrow")]
    assert "↑ IMPACT" in eyebrows and "URGENCE →" in eyebrows
    assert any("runs" in o for o in ops)  # the items of B as chevrons


def test_next_steps_and_session_plan_rules():
    ops, h = _render("next_steps", {"steps": [{"title": "Aujourd'hui", "text": "Atelier.", "current": True}, {"title": "Fin septembre", "text": "Entretiens."}]}, w=600)
    rules = _of(ops, "box", "rule")
    assert [r["fill"] for r in rules] == ["accent", "gray_2"] and h > 34
    ops, h = _render("session_plan", {"sections": [{"title": "S1", "text": "t"}, {"title": "S2"}],
                                      "slots": [{"time": "0-5'", "label": "Ouverture", "weight": 5, "current": True}, {"time": "5-20'", "label": "Collab", "weight": 15}]}, w=600)
    slots = _of(ops, "box", "slot")
    assert len(slots) == 2 and slots[1]["w"] > slots[0]["w"] >= 72 and _of(ops, "box", "slot_rule")[0]["fill"] == "accent"
    assert _of(ops, "text", "section")[0]["y"] < slots[0]["y"] and h == slots[0]["y"] + slots[0]["h"]


def test_board_columns_numbered_cards_and_empty_state():
    ops, h = _render("board_columns", {"columns": [{"title": "Forces"}, {"title": "Irritants", "items": ["Trop d'interlocuteurs.", "Slack à revoir."]}]}, w=600)
    cols = _of(ops, "box", "column")
    assert len(cols) == 2 and cols[0]["h"] == cols[1]["h"] == h and cols[0]["fill"] == "surface"
    assert _of(ops, "text", "empty")[0]["italic"] and [n["text"] for n in _of(ops, "text", "num")] == ["1", "2"]
    cards = _of(ops, "box", "card")
    assert len(cards) == 2 and cards[0]["x"] > cols[1]["x"] and cards[1]["y"] > cards[0]["y"]


def test_attention_points_levels_tags_and_outline():
    items = [{"level": "critical", "tag": "Tracking", "text": "Mobile : **439 clics** : ==vérifier le tag=="}, {"level": "warning", "tag": "Budget", "text": "Sous-conso."},
             {"level": "good", "tag": "Qualité", "text": "OK."}]
    ops, h = _render("attention_points", {"title": "Points d'attention", "note": "seuils automatiques", "items": items}, w=600)
    crit, warn, good = _of(ops, "box", "critical")[0], _of(ops, "box", "warning")[0], _of(ops, "box", "good")[0]
    assert crit["line"]["color"] == "coral" and warn["line"]["color"] == "rule" and good["fill"] == "background"
    tags = _of(ops, "box", "tag")
    assert [t["fill"] for t in tags] == ["coral", "accent_alt", "accent"] and tags[0]["text"] == "TRACKING" and tags[0]["color"] == "on_dark"
    assert _of(ops, "text", "text")[0]["highlight"] == "highlight_alt" and _of(ops, "box", "square")[0]["fill"] == "accent"
    assert h == pytest.approx(good["y"] + good["h"])


def test_bar_list_states_stripes_and_values():
    items = [{"label": "transmettre", "sub": "LP", "value": 999.59, "value_text": "999,59 € · 1 385 clics", "sub_right": "9 contacts", "state": "ok"},
             {"label": "legs", "value": 28.15, "state": "none"}, {"label": "Page vue", "value": 257, "pattern": "stripes", "state": "ok"}]
    ops, h = _render("bar_list", {"items": items, "states": {"ok": "accent", "none": "gray_2"}, "max": 1539.62, "note": "Échelle : part des 1 539,62 €"}, w=600)
    bars = _of(ops, "box", "bar")
    assert [b["fill"] for b in bars] == ["accent", "gray_2", "accent"] and bars[0]["w"] > bars[1]["w"]
    assert _of(ops, "line", "stripe") and all(s["x1"] >= bars[2]["x"] - 0.01 and s["x2"] <= bars[2]["x"] + bars[2]["w"] + 0.01 for s in _of(ops, "line", "stripe"))
    values = [v["text"] for v in _of(ops, "text", "value")]
    assert values[0] == "999,59 € · 1 385 clics" and values[1] == "28,15" and _of(ops, "text", "sub_right")[0]["text"] == "9 contacts"
    assert len(_of(ops, "box", "swatch")) == 2 and _of(ops, "text", "note")[0]["text"].startswith("Échelle")
    inbar, _ = _render("bar_list", {"items": [{"label": "Clic", "value": 57, "sub_right": "14,8 %"}], "value_in_bar": True}, w=500)
    assert _of(inbar, "text", "value")[0]["align"] == "END" and _of(inbar, "text", "sub_right")[0]["text"] == "14,8 %"


def test_workshop_components_have_use_and_render_in_both_themes():
    names = {"score_matrix", "ranked_bars", "chip_cloud", "quadrant_matrix", "next_steps", "board_columns", "session_plan", "attention_points", "bar_list", "table"}
    for entry in components.catalogue():
        if entry["name"] not in names:
            continue
        names.discard(entry["name"])
        assert entry["use"], entry["name"]
        for theme in (PERISCOPE, themes.load("default")):
            ops, height = components.render(entry["name"], entry["example"]["props"], theme, 600)
            draw.ops_to_requests("s", ops, theme, prefix="cmp", resolve_asset=lambda name, tint=None: ("fid", (100, 100)))
            assert height > 0, entry["name"]
    assert not names


def test_fit_text_size_and_fit_labels():
    from gslides_mcp.components.axes import fit_labels, legend_ops
    from gslides_mcp.components.builtin import fit_text_size

    assert fit_text_size("Court", 200, 11) == 11
    small = fit_text_size("Un libellé beaucoup trop long pour la colonne", 90, 11, max_lines=2, floor=9)
    assert 9 <= small < 11
    shown, size = fit_labels(["Search Hors marque", "PMax", "Search Marque"], slot=60)
    assert size < 10 and all(shown)  # shrunk, nothing thinned
    dense, dsize = fit_labels([f"{d:02d}/12" for d in range(1, 32)], slot=14)
    assert dsize == 10.0 and any(lb is None for lb in dense)  # short labels: nothing to shrink, thinned instead
    ops, _ = legend_ops([{"name": "Une série au nom vraiment très long"}, {"name": "Une autre série au nom très long aussi"}], 0, 0, 220, "top")
    texts = [o for o in ops if o["op"] == "text"]
    assert texts and texts[0]["size"] < 10 and texts[0]["small_ok"]
    ops, _ = _render("chart_bars", {"labels": ["Search Hors marque", "PMax", "Search Marque"], "values": [1, 2, 3]}, w=200)
    labels = _of(ops, "text", "label")
    assert len(labels) == 3 and labels[0]["size"] < 10


# --- charter restyle (0.5.0): rounded cards, light grounds, table variants -----------------

def test_table_declares_catalogue_variants_with_valid_props():
    from gslides_mcp import components
    comp = components.get("table")
    assert len(comp.variants) >= 4 and all(v["title"] and v["when"] and v["props"]["rows"] for v in comp.variants)
    schema = comp.schema()
    assert len(schema["variants"]) == len(comp.variants) and all(set(v) == {"title", "when", "props"} for v in schema["variants"])
    assert "variants" in comp.use  # the use sentence points the model at them
    for v in comp.variants:
        ops, h = _render("table", v["props"], w=600)
        assert h > 0 and any(o["op"] == "table" for o in ops)


def test_every_declared_variant_renders_and_says_when():
    from gslides_mcp import components
    from gslides_mcp.components.variants import VARIANTS
    assert set(VARIANTS) <= set(components.names())
    for name, variants in VARIANTS.items():
        for v in variants:
            assert v["title"] and v["when"] and isinstance(v["props"], dict), (name, v.get("title"))
            ops, h = _render(name, v["props"], w=600)
            assert ops and h > 0, (name, v["title"])


def test_choice_props_derive_variants_automatically():
    from gslides_mcp import components
    comp = components.get("eyebrow")  # no explicit entry: align START/CENTER/END → two auto variants
    assert not comp.variants
    auto = comp.schema()["variants"]
    assert {v["props"]["align"] for v in auto} == {"CENTER", "END"} and all(v["when"] for v in auto)
    for v in auto:
        assert _render("eyebrow", v["props"], w=400)[1] > 0
    # every component with a choice prop exposes variants one way or the other
    for e in components.catalogue():
        if any(p.get("choices") for p in e["props"]):
            assert e.get("variants"), e["name"]


def test_rounded_charter_frames():
    ops, _ = _render("card", {"title": "T", "body": "x"}, w=300)
    assert _of(ops, "box", "card")[0]["shape"] == "ROUND_RECTANGLE"
    ops, _ = _render("card", {"title": "T", "body": "x", "variant": "plain"}, w=300)
    assert _of(ops, "box", "card")[0]["shape"] == "RECTANGLE"
    ops, _ = _render("compare_cards", {"cards": [{"kind": "bad", "title": "a"}, {"kind": "good", "title": "b"}]}, w=400)
    assert all(c["shape"] == "ROUND_RECTANGLE" for c in _of(ops, "box", "card"))
    ops, _ = _render("process", {"steps": [{"title": "a"}, {"title": "b"}]}, w=400)
    assert all(s["shape"] == "ROUND_RECTANGLE" for s in _of(ops, "box", "step"))
    ops, _ = _render("before_after", {"before": {"title": "Avant", "items": ["a"]}, "after": {"title": "Après", "items": ["b"]}}, w=500)
    assert all("line" not in pnl for pnl in _of(ops, "box", "panel"))


def test_media_plan_objective_is_a_content_card():
    props = {"levers": [{"name": "Search", "budget": "1 000 €"}], "objective": {"title": "Objectif", "items": ["a", "b"]}}
    ops, h = _render("media_plan", props, w=660)
    (panel,) = _of(ops, "box", "objective")
    assert panel["shape"] == "ROUND_RECTANGLE" and panel["fill"] == "accent" and panel["h"] == h
    (eyebrow,) = _of(ops, "text", "objective_eyebrow")
    assert "\u2009" in eyebrow["text"] and eyebrow["text"].replace("\u2009", "") == "OBJECTIF"
    assert not _of(ops, "box", "objective_dot")


def test_heatmap_and_scoreboard_use_dark_header_and_grey_label_column():
    ops, _ = _render("heatmap", {"rows": [["", "A"], ["x", "1"], ["y", "4"]]}, w=300)
    (t,) = [o for o in ops if o["op"] == "table"]
    assert t["header"]["fill"] == "ink"
    ops, _ = _render("ad_scoreboard", {"ads": [{"name": "A", "values": {"Clics": "1"}}, {"name": "B", "values": {"Clics": "2"}}], "metrics": ["Clics"]}, w=400)
    (t,) = [o for o in ops if o["op"] == "table"]
    assert t["cell_fills"][(1, 0)] == "surface"


def test_theme_defines_pale_mint_and_heat_scale():
    assert PERISCOPE.colors["mint_pale"].upper() == "#BFF5E6"
    assert PERISCOPE.color("heat_2") == PERISCOPE.color("mint_pale") and PERISCOPE.color("heat_4") == PERISCOPE.color("navy")


def test_bar_list_value_in_bar_without_sub_right_emits_no_empty_text():
    ops, _ = _render("bar_list", {"items": [{"label": "a", "value": 10}, {"label": "b", "value": 5}], "value_in_bar": True}, w=600)
    assert not [o for o in ops if o["op"] == "text" and o.get("role") == "sub_right"]
    assert all(o.get("text") or o.get("runs") or o.get("markdown") for o in ops if o["op"] == "text")
