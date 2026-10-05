"""persona_sheet: full-width persona with its own header, two columns, no overflow, warnings by field."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.tools import components as tools

PERISCOPE = themes.load("periscope")
W = 564  # content width of a 720 × 405 deck

MANON = {
    "name": "Manon", "age": "48 ans", "segment": "Porteurs de projets", "role": "Financements et partenariats",
    "origin": "Persona 2017 revu", "badge": {"text": "NOUVEAU 2026", "color": "acid"},
    "context": "Responsable développement ou chargée de projets, utilise l'IA générative.",
    "goal": "Identifier rapidement les financements pertinents.",
    "expectations": ["Recherche et filtres", "Alertes personnalisées", "FAQ détaillée"],
    "brakes": ["Trop de dossiers", "Lourdeur administrative", "Infos dispersées"],
    "side_label": "Requêtes Google types",
    "side_items": ['"appel à projet" : 1242 impr., pos. 18,5 (GSC)', '"appel à projet fondation" : 839 impr. (GSC)',
                   '"collecte de fonds" (S)'],
    "tag": "2 PROMPTS : N° 24, 27",
    "note": "(GSC) Search Console www, 29/06 au 28/09/2026. (S) expression Synomia 2016.",
}


def _render(props, w=W, h=None):
    return components.render("persona_sheet", props, PERISCOPE, w, h)


def _of(ops, role, kind=None):
    return [o for o in ops if o.get("role") == role and (kind is None or o["op"] == kind)]


def _bottom(o):
    return o["y"] + o["h"]


def _warnings(ops):
    return [o["text"] for o in ops if o["op"] == "warning"]


def test_the_sheet_fills_the_content_area_without_overflow_or_warning():
    ops, h = _render(MANON)
    assert 290 <= h <= 320 and _warnings(ops) == []
    drawn = [o for o in ops if o["op"] != "warning"]
    assert min(o["x"] for o in drawn) >= 0 and max(o["x"] + o["w"] for o in drawn) <= W + 0.01
    assert max(_bottom(o) for o in drawn) <= h + 0.01


def test_header_avatar_name_subtitle_badge():
    ops, _ = _render(MANON)
    (avatar,) = _of(ops, "avatar")
    assert avatar["shape"] == "ELLIPSE" and avatar["w"] == avatar["h"] == 46 and avatar["text"] == "M" and avatar["size"] == 18
    (name,) = _of(ops, "name")
    (title, dot), = name["runs"]
    assert title["text"] == "MANON – 48 ANS" and title["size"] == 20 and title["bold"] and title["color"] == "ink"
    assert dot == {"text": ".", "bold": True, "size": 20, "color": "accent"}
    (sub,) = _of(ops, "subtitle")
    assert sub["text"] == "PORTEURS DE PROJETS · FINANCEMENTS ET PARTENARIATS (PERSONA 2017 REVU)" and sub["size"] == 12
    (badge,) = _of(ops, "badge")
    assert badge["fill"] == "acid" and badge["h"] == 22 and abs(badge["x"] + badge["w"] - W) < 0.01
    assert name["x"] + name["w"] <= badge["x"]


def test_a_photo_replaces_the_initial():
    ops, _ = _render({**MANON, "photo": "screen-demo"})
    (avatar,) = _of(ops, "avatar")
    assert avatar["op"] == "image" and avatar["asset"] == "screen-demo"


def test_two_columns_aligned():
    ops, _ = _render(MANON)
    (ctx,) = _of(ops, "context_card")
    (exp,) = _of(ops, "expectations_card")
    (brk,) = _of(ops, "brakes_card")
    (side,) = _of(ops, "side_card")
    (tag,) = _of(ops, "tag")
    (note,) = _of(ops, "note")
    assert ctx["x"] == 0 and abs(ctx["w"] - 330) < 1 and ctx["h"] == 92 and ctx["shape"] == "ROUND_RECTANGLE"
    assert ctx["fill"] == "background" and ctx["line"]["color"] == "rule"
    assert exp["y"] == brk["y"] == _bottom(ctx) + 8 and exp["h"] == brk["h"] == 108
    assert exp["x"] == 0 and abs(_bottom(exp) - _bottom(brk)) < 0.01 and abs(brk["x"] + brk["w"] - ctx["w"]) < 0.01
    assert side["x"] == ctx["w"] + 12 and abs(side["x"] + side["w"] - W) < 0.01 and side["fill"] == "accent"
    assert side["y"] == ctx["y"] and abs(_bottom(side) - _bottom(exp)) < 0.01
    assert tag["y"] == _bottom(exp) + 8 and tag["h"] == 28 and tag["fill"] == "cyan" and tag["w"] == ctx["w"]
    assert note["x"] == side["x"] and note["y"] >= _bottom(side) and note["size"] == 10 and note["color"] == "muted"


def test_lists_carry_their_label_and_chevrons():
    ops, _ = _render(MANON)
    (exp,) = _of(ops, "expectations", "text")
    label, *items = exp["runs"]
    assert label[0]["text"] == "ATTENTES" and label[0]["size"] == 10 and label[0]["bold"]
    assert [p[1]["text"] for p in items] == MANON["expectations"] and items[0][0]["text"].startswith("›")
    (side,) = _of(ops, "side", "text")
    assert side["runs"][0][0]["text"] == "REQUÊTES GOOGLE TYPES" and side["runs"][1][0]["color"] == "ink"
    (ctx,) = _of(ops, "context", "text")
    assert [p[0]["text"] for p in ctx["runs"]] == ["CONTEXTE", MANON["context"], "Objectif : " + MANON["goal"]]
    assert ctx["runs"][2][0]["bold"] and all(p[0]["size"] >= 10 for p in ctx["runs"])


def test_without_side_items_the_left_column_takes_the_width():
    ops, _ = _render({**MANON, "side_items": [], "note": None})
    (ctx,) = _of(ops, "context_card")
    assert ctx["w"] == W and _of(ops, "side_card") == [] and _of(ops, "tag")[0]["w"] == W


def test_without_header_the_sheet_starts_at_the_cards():
    ops, h = _render({**MANON, "header": False})
    assert _of(ops, "name") == [] and _of(ops, "avatar") == [] and _of(ops, "context_card")[0]["y"] == 0
    assert h < _render(MANON)[1]


def test_a_long_text_grows_its_card_and_names_the_field():
    long_ctx = " ".join(["Responsable développement, chargée de projets et de partenariats institutionnels."] * 3)
    ops, h = _render({**MANON, "context": long_ctx})
    (ctx,) = _of(ops, "context_card")
    (exp,) = _of(ops, "expectations_card")
    (side,) = _of(ops, "side_card")
    assert ctx["h"] > 92 and exp["y"] == _bottom(ctx) + 8 and abs(_bottom(side) - _bottom(exp)) < 0.01
    (warning,) = _warnings(ops)
    assert "context" in warning and h > _render(MANON)[1]


def test_too_many_items_are_refused():
    with pytest.raises(ValueError, match="expectations"):
        _render({**MANON, "expectations": ["a", "b", "c", "d"]})
    with pytest.raises(ValueError, match="side_items"):
        _render({**MANON, "side_items": list("abcdef")})


def test_a_forced_height_never_overlaps():
    ops, h = _render(MANON, h=250)
    assert h > 250 and any("height_pt" in w for w in _warnings(ops))
    ops, h = _render(MANON, h=360)
    assert h == 360 and _warnings(ops) == []
    (tag,) = _of(ops, "tag")
    (exp,) = _of(ops, "expectations_card")
    assert tag["y"] >= _bottom(exp) + 8 and _bottom(tag) <= 360


def test_warning_ops_are_not_drawn_and_reach_insert_component(fake_slides):
    long_ctx = " ".join(["Responsable développement, chargée de projets et de partenariats institutionnels."] * 3)
    out = tools.insert_component("PRES1", "1", "persona_sheet", {**MANON, "context": long_ctx}, x_pt=78, y_pt=40, width_pt=W)
    assert len(out["warnings"]) == 1 and "context" in out["warnings"][0]
    assert {"avatar", "name", "subtitle", "badge", "context", "expectations", "brakes", "tag", "side", "note"} <= set(out["ids_by_role"])
    reqs, _ = draw.ops_to_requests("s1", [{"op": "warning", "text": "x"}], PERISCOPE, prefix="p")
    assert reqs == []


def test_example_and_variants_render():
    entry = next(e for e in components.catalogue() if e["name"] == "persona_sheet")
    assert entry["use"] and "personnes" in entry["intents"]
    ops, h = _render(entry["example"]["props"])
    assert h > 0 and _warnings(ops) == []
    titles = [v["title"] for v in entry["variants"]]
    assert len(titles) >= 2
    for v in entry["variants"]:
        ops, h = _render(v["props"])
        assert h > 0 and _warnings(ops) == []
