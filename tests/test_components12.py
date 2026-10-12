"""Variants from the Pasteur memo deck: kpi tiles, stats list, agenda dates, lot opener, bigstat panel."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")


def _assets(ref, tint=None):
    return ("file_" + str(ref), (96, 96))


def _render(name, props, w=600, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp", resolve_asset=_assets)
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


# --- kpi / kpi_grid tile -------------------------------------------------------------------

def test_kpi_tile_is_a_grey_rounded_tile_with_an_ink_arrowed_delta():
    ops, h = _render("kpi", {"value": "21,5 M€", "label": "Collecte individus", "delta": "+3,2 % vs 2024", "tile": True}, w=170)
    assert not _of(ops, "box", "bar")
    (tile,) = _of(ops, "box", "tile")
    assert tile["shape"] == "ROUND_RECTANGLE" and tile["fill"] == "surface" and tile["w"] == 170 and tile["h"] == h
    (delta,) = _of(ops, "text", "delta")
    assert delta["text"] == "▲ +3,2 % vs 2024" and delta["color"] == "ink" and delta["bold"]
    texts = _of(ops, "text")
    assert all(tile["y"] < t["y"] and t["y"] + t["h"] <= tile["h"] + 0.01 and t["x"] + t["w"] <= tile["w"] for t in texts)


@pytest.mark.parametrize("delta, shown", [("-2,3 % vs 2024", "▼ -2,3 % vs 2024"), ("−15 %", "▼ −15 %"),
                                          ("104 € en 2024", "104 € en 2024"), ("▲ +1 pt", "▲ +1 pt")])
def test_kpi_tile_arrow_follows_the_sign_and_a_plain_comparison_keeps_none(delta, shown):
    ops, _ = _render("kpi", {"value": "110 €", "label": "Contribution moyenne", "delta": delta, "tile": True}, w=170)
    assert _of(ops, "text", "delta")[0]["text"] == shown


def test_kpi_tile_on_a_dark_ground():
    ops, _ = _render("kpi", {"value": "196 K", "label": "Donateurs", "delta": "-2 %", "tile": True, "dark": True}, w=170)
    assert _of(ops, "box", "tile")[0]["fill"] == "surface_dark_2"
    assert {t["color"] for t in _of(ops, "text")} == {"on_dark"}


def test_kpi_grid_tiles_fill_the_width_one_gap_apart_and_share_one_height():
    items = [{"value": "21,5 M€", "label": "Collecte individus", "delta": "+3,2 % vs 2024"}, {"value": "196 K", "label": "Donateurs actifs", "delta": "-2,3 %"},
             {"value": "110 €", "label": "Contribution moyenne", "delta": "104 € en 2024"}, {"value": "> 1/3", "label": "du financement vient de la générosité"}]
    ops, h = _render("kpi_grid", {"items": items, "cols": 2, "tile": True}, w=340)
    tiles = _of(ops, "box", "tile")
    assert len(tiles) == 4 and len({t["h"] for t in tiles}) == 1
    assert tiles[0]["x"] == 0 and tiles[1]["x"] + tiles[1]["w"] == pytest.approx(340)
    assert tiles[1]["x"] - (tiles[0]["x"] + tiles[0]["w"]) == pytest.approx(10)
    assert tiles[2]["y"] - (tiles[0]["y"] + tiles[0]["h"]) == pytest.approx(10)
    assert h == pytest.approx(tiles[3]["y"] + tiles[3]["h"])
    values = _of(ops, "text", "value")
    assert values[0]["y"] == values[1]["y"] and len({v["size"] for v in values}) == 1
    # the KPI without a delta keeps the delta line: its tile is as tall as the others
    assert len(_of(ops, "text", "delta")) == 3


def test_kpi_grid_a_long_label_without_delta_runs_into_the_free_delta_line():
    items = [{"value": "21,5 M€", "label": "Collecte", "delta": "+3,2 %"}, {"value": "> 1/3", "label": "du financement vient de la générosité publique"}]
    for tile in (True, False):
        ops, _ = _render("kpi_grid", {"items": items, "cols": 2, "tile": tile}, w=300)
        short, long_ = _of(ops, "text", "label")
        (delta,) = _of(ops, "text", "delta")
        # the delta sits right under a one-line label, the long label takes the room the missing delta leaves
        assert delta["y"] == pytest.approx(short["y"] + short["h"] - 1)
        assert long_["h"] > short["h"] and long_["y"] + long_["h"] <= delta["y"] + delta["h"] + 0.01


def test_kpi_grid_tile_row_labels_are_centred_on_their_tiles():
    ops, _ = _render("kpi_grid", {"rows": ["Marque", "Hors marque"], "cols": 2, "tile": True,
                                  "items": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}, {"value": "3", "label": "c"}, {"value": "4", "label": "d"}]})
    tiles = _of(ops, "box", "tile")
    labels = _of(ops, "text", "row_label")
    assert [lb["y"] for lb in labels] == [tiles[0]["y"], tiles[2]["y"]] and all(lb["h"] == tiles[0]["h"] for lb in labels)
    assert tiles[0]["x"] >= labels[0]["w"]


def test_kpi_grid_without_tile_is_unchanged():
    ops, h = _render("kpi_grid", {"items": [{"value": "1", "label": "a", "delta": "+1 %"}, {"value": "2", "label": "b"}], "cols": 2})
    assert len(_of(ops, "box", "bar")) == 2 and not _of(ops, "box", "tile")
    assert _of(ops, "text", "delta")[0]["color"] == "positive" and _of(ops, "text", "value")[1]["x"] == pytest.approx(300 + 14)


# --- stats list ------------------------------------------------------------------------------

ROWS = [{"value": "2 %", "label": "des 90 K leads en base deviennent donateurs", "sub": "CdC : définir les indicateurs de suivi"},
        {"value": "480 K€", "label": "de valeur annuelle Google Grants", "sub": "SEA = levier principal"},
        {"value": "756", "label": "PA souscrits en ligne en 2025"}]


def test_stats_list_in_grey_bands_aligns_the_figures_and_the_texts():
    ops, h = _render("stats", {"items": ROWS, "layout": "list", "tile": True}, w=640)
    bands = _of(ops, "box", "row")
    assert len(bands) == 3 and all(b["shape"] == "ROUND_RECTANGLE" and b["fill"] == "surface" and b["w"] == 640 for b in bands)
    assert len({b["h"] for b in bands}) == 1 and bands[1]["y"] - (bands[0]["y"] + bands[0]["h"]) == pytest.approx(6)
    assert h == pytest.approx(bands[-1]["y"] + bands[-1]["h"])
    values = _of(ops, "text", "value")
    assert len({v["size"] for v in values}) == 1 and len({v["x"] for v in values}) == 1
    assert all(v["color"] == "ink" and v["valign"] == "MIDDLE" for v in values)
    texts = _of(ops, "text", "text")
    assert all(t["x"] >= values[0]["x"] + values[0]["w"] and t["valign"] == "MIDDLE" for t in texts)
    first = texts[0]["runs"]
    assert first[0][0]["bold"] and first[0][0]["color"] == "ink" and first[1][0]["color"] == "muted"
    assert len(texts[2]["runs"]) == 1  # no sub, no grey line


def test_stats_list_bare_has_no_band_and_a_long_figure_shrinks_to_its_column():
    ops, _ = _render("stats", {"items": [["70 %", "de femmes"], ["87,5 ans", "âge au décès"]], "layout": "list", "value_w": 60}, w=300)
    assert not _of(ops, "box")
    values = _of(ops, "text", "value")
    assert values[0]["size"] < 18 and values[0]["w"] == 60
    # no grey line under the labels: they stay roman beside the bold figures
    assert all(not t["runs"][0][0]["bold"] for t in _of(ops, "text", "text"))


def test_stats_row_layout_is_unchanged():
    ops, h = _render("stats", {"items": [{"value": "12", "label": "pays"}, {"value": "3", "label": "langues"}]})
    assert [o["size"] for o in ops if o.get("style") == "stat_value"] == [38, 38] and h == 82


# --- agenda as a calendar ----------------------------------------------------------------------

DATES = [{"num": "13 · 14 · 15 oct.", "title": "Soutenances (2 h)", "current": True}, {"num": "27 nov.", "title": "Choix du candidat"},
         {"num": "→ 28 févr. 2027", "title": "Phase de transition"}]


def test_agenda_dates_widen_the_chips_into_rounded_pills_and_light_the_current_one():
    ops, h = _render("agenda", {"items": DATES, "chip_fill": "surface", "row_h": 40})
    chips = _of(ops, "box", "chip")
    assert [c["fill"] for c in chips] == ["accent", "surface", "surface"]
    assert all(c["shape"] == "ROUND_RECTANGLE" and c["h"] == 32 and c["color"] == "on_chip" for c in chips)
    assert len({c["w"] for c in chips}) == 1 and chips[0]["w"] >= len("→ 28 févr. 2027") * 11 * 0.55
    titles = [o for o in _of(ops, "text")]
    assert all(t["x"] == pytest.approx(chips[0]["w"] + 10) for t in titles)
    assert all(c["y"] + c["h"] / 2 == pytest.approx(t["y"] + t["h"] / 2) for c, t in zip(chips, titles))
    assert h == 120


def test_agenda_numbers_keep_the_small_square_acid_chip():
    ops, h = _render("agenda", {"items": ["Contexte", {"num": "A", "title": "Annexes"}]})
    chips = _of(ops, "box", "chip")
    assert all(c["w"] == 28 and c["h"] == 16 and c["fill"] == "chip" and "shape" not in c for c in chips)
    assert _of(ops, "text")[0]["x"] == 38 and h == 48


# --- section_header as a lot opener ---------------------------------------------------------------

LOT = {"kicker": "LOT 1", "title": "Collecte Grand Public\n& Taxe d'apprentissage", "size": 24, "icon": "px-heart",
       "stats": [{"value": "15,7 M€", "label": "collectés en 2025 par le Grand Public (+1,6 %)"}, {"value": "189 K", "label": "donateurs actifs"},
                 {"value": "≥ 3 %/an", "label": "de croissance visée sur 5 ans"}]}


def test_lot_opener_kicker_over_title_icon_on_the_right_figures_at_the_foot():
    ops, h = _render("section_header", LOT, w=640, h=300)
    (kicker,) = _of(ops, "text", "kicker")
    (title,) = _of(ops, "text", "title")
    assert kicker["size"] == 54 and kicker["text"] == "LOT 1" and title["y"] > kicker["y"] and title["y"] < kicker["y"] + kicker["h"]
    (icon,) = _of(ops, "image", "icon")
    assert icon["asset"] == "px-heart" and icon["tint"] == "ink" and icon["x"] + icon["w"] == pytest.approx(640) and icon["y"] == 0
    assert kicker["x"] + kicker["w"] < icon["x"] and title["x"] + title["w"] < icon["x"]
    values, labels = _of(ops, "text", "stat_value"), _of(ops, "text", "stat_label")
    assert len(values) == 3 and len({v["size"] for v in values}) == 1 and len({v["y"] for v in values}) == 1
    assert values[2]["x"] + values[2]["w"] == pytest.approx(640) and all(v["color"] == "ink" for v in values)
    # the box height is given: the figures sit at its foot
    assert max(lb["y"] + lb["h"] for lb in labels) == pytest.approx(300) and h == 300


def test_lot_opener_without_height_puts_the_figures_under_the_icon_and_title():
    ops, h = _render("section_header", {**LOT, "dark": True}, w=640)
    (icon,) = _of(ops, "image", "icon")
    assert icon["tint"] == "accent"
    values = _of(ops, "text", "stat_value")
    assert values[0]["y"] >= icon["h"] + 28 and values[0]["color"] == "on_dark"
    assert h == pytest.approx(max(o["y"] + o["h"] for o in _of(ops, "text", "stat_label")))


def test_section_header_without_the_new_props_is_unchanged():
    ops, h = _render("section_header", {"eyebrow": "Équipe", "title": "Un titre"}, w=500)
    assert [o.get("role") for o in ops] == ["eyebrow", "title"] and ops[1]["w"] == 500


# --- bigstat in a panel beside a text --------------------------------------------------------------

PANEL = {"value": "-30 à -40 %", "label": "Audience SEO", "sub": "09/2026 vs N-1 *", "panel": "dark", "source": "* Source Tendances SEMRUSH",
         "text": "**Moins de clics, moins de données first party.**\n\nCette perte de trafic est une perte de matière.\n\nUne partie ==absorbée par l'IA Overview==."}


def test_bigstat_panel_centres_the_figure_puts_the_source_at_its_foot_and_the_text_beside():
    ops, h = _render("bigstat", PANEL, w=660)
    (panel,) = _of(ops, "box", "panel")
    assert panel["fill"] == "surface_dark" and panel["x"] == 0 and panel["w"] == pytest.approx(660 * 0.36) and panel["h"] == h >= 220
    value, label, sub, source = (_of(ops, "text", r)[0] for r in ("value", "label", "sub", "source"))
    assert {t["color"] for t in (value, label, sub, source)} == {"on_dark"}
    assert all(t["align"] == "CENTER" and t["x"] >= panel["x"] and t["x"] + t["w"] <= panel["w"] for t in (value, label, sub, source))
    # the figure group sits in the middle, the source at the foot
    top, bottom = value["y"], sub["y"] + sub["h"]
    assert abs(top - (source["y"] - bottom)) < 25
    assert source["y"] + source["h"] <= panel["h"] and source["y"] > bottom
    # the figure keeps one line: it shrinks to the panel
    assert value["size"] * 0.58 * len(PANEL["value"]) <= value["w"] - 2 * 7.2 + 0.5
    (text,) = _of(ops, "text", "text")
    assert text["x"] > panel["w"] and text["x"] + text["w"] == pytest.approx(660) and text["valign"] == "MIDDLE"
    assert text["highlight"] == "highlight_alt" and text["h"] == panel["h"]


def test_bigstat_panel_alone_takes_the_width_and_a_light_panel_keeps_ink():
    ops, _ = _render("bigstat", {"value": "1 site sur 3", "label": "perd du trafic", "panel": "surface"}, w=240)
    (panel,) = _of(ops, "box", "panel")
    assert panel["w"] == 240 and panel["fill"] == "surface" and not _of(ops, "text", "text")
    assert _of(ops, "text", "value")[0]["color"] == "ink" and _of(ops, "text", "label")[0]["color"] == "ink"


def test_bare_bigstat_is_unchanged():
    ops, h = _render("bigstat", {"value": "+42 %", "label": "de trafic"})
    assert len(ops) == 2 and ops[0]["style"] == "stat_value" and "size" not in ops[0] and h == 98


@pytest.mark.parametrize("name", ["kpi", "kpi_grid", "stats", "agenda", "section_header", "bigstat"])
def test_examples_and_variants_render_in_both_themes(name):
    entry = next(e for e in components.catalogue() if e["name"] == name)
    assert entry["use"] and entry["variants"]
    for theme in (PERISCOPE, themes.load("default")):
        for props in [entry["example"]["props"]] + [v["props"] for v in entry["variants"]]:
            ops, height = components.render(name, props, theme, 640)
            draw.ops_to_requests("s", ops, theme, prefix="cmp", resolve_asset=_assets)
            assert height > 0


def test_descriptions_point_at_the_new_variants():
    from gslides_mcp.components.intents import suggest

    cat = {e["name"]: e for e in components.catalogue()}
    for text, name in (("les dates clés de l'appel d'offres", "agenda"), ("ouverture de lot avec trois chiffres", "section_header"),
                       ("la grille de notation de l'AO", "stats"), ("un constat chiffré à expliquer", "bigstat")):
        found = [c["component"] for i in suggest(text, cat)["intents"] for c in i["candidates"]]
        assert name in found, (text, found)
