"""Title dot, card title, numbered stack, hub_spoke logos, diagram_compare, funnel_stages, fan_out, vertical tree."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.components.builtin import INSET_X, title_dot

PERISCOPE = themes.load("periscope")


def _assets(ref, tint=None):
    return ("file_" + str(ref), (100, 100))


def _render(name, props, w=600, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp", resolve_asset=_assets)
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def _caps_centre(text_op):
    return text_op["y"] + 7 + 0.6 * text_op["size"]


# --- lot A: title dot, card title, numbered stack -----------------------------------------

def test_title_dot_is_the_cap_height_and_sits_on_the_caps():
    op, advance = title_dot(10, 100, 15)
    assert op["shape"] == "ELLIPSE" and op["fill"] == "accent"
    assert op["w"] == op["h"] == pytest.approx(10.5)
    assert op["x"] == 10 and op["y"] + op["h"] / 2 == pytest.approx(100 + 7 + 0.6 * 15)
    assert advance == pytest.approx(10.5 * 1.9)
    small, _ = title_dot(0, 0, 11, d=10)
    assert small["w"] == 10 and small["y"] + 5 == pytest.approx(7 + 0.6 * 11)


def test_card_title_keeps_its_case_at_15pt_and_the_dot_follows_it():
    ops, _ = _render("card", {"variant": "dark", "title": "Sécuriser", "body": "Réduire la dépendance au trafic SEO froid", "dot": True}, w=260)
    title = next(o for o in _of(ops, "text") if o["style"] == "card_title")
    assert title["text"] == "Sécuriser" and title["size"] == 15 and title["color"] == "accent"
    dot = next(o for o in _of(ops, "box") if o.get("shape") == "ELLIPSE")
    assert dot["w"] == pytest.approx(10.5)
    assert dot["y"] + dot["h"] / 2 == pytest.approx(_caps_centre(title))
    # the title text starts about one diameter after the dot
    assert title["x"] + INSET_X - (dot["x"] + dot["w"]) == pytest.approx(0.9 * dot["w"])


def test_media_plan_dot_keeps_its_size_and_is_centred_on_the_lever_name():
    ops, _ = _render("media_plan", {"levers": [{"name": "Search", "budget": "16 000 € HT"}], "objective": None})
    (dot,) = _of(ops, "box", "dot")
    (lever,) = _of(ops, "text", "lever")
    assert dot["w"] == 10 and dot["y"] + 5 == pytest.approx(_caps_centre(lever))


def test_stack_numbers_its_layers_and_alternates_accents_on_dark_layers():
    items = [{"label": "Couverture", "sub": "Positions"}, {"label": "Engagement"}, {"label": "Conversion"}, {"label": "Valeur"}]
    ops, _ = _render("stack", {"items": items, "numbered": True, "palette": "brand"})
    layers = _of(ops, "box", "layer")
    assert [b["fill"] for b in layers] == ["surface_dark", "accent", "surface_dark", "accent_alt"]
    assert all(b["shape"] == "ROUND_RECTANGLE" for b in layers)
    nums = _of(ops, "text", "num")
    assert [n["text"] for n in nums] == ["01", "02", "03", "04"]
    assert [n["color"] for n in nums] == ["accent", "ink", "accent_alt", "ink"]
    assert all(n["x"] < b["x"] + 40 for n, b in zip(nums, layers))
    forced, _ = _render("stack", {"items": [{"label": "A", "num": "A1"}, {"label": "B"}], "numbered": True})
    assert [n["text"] for n in _of(forced, "text", "num")] == ["A1", "02"]
    plain, _ = _render("stack", {"items": items})
    assert not _of(plain, "text", "num") and _of(plain, "box", "layer")[0]["fill"] == "surface_dark"


# --- lot B: hub_spoke logos, single link, diagram_compare --------------------------------------

LOGOS = [{"logo": "chatgpt"}, {"logo": "claude"}, {"logo": "google"}, {"logo": "reddit"}, {"logo_url": "https://example.com/pinterest.png"}]


def test_hub_spoke_logo_satellites_on_a_dark_ground_around_a_disc():
    ops, h = _render("hub_spoke", {"center": "Marque", "sats": LOGOS, "hub_shape": "disc", "hub_h": 84, "sat_d": 60, "dark": True}, w=400, h=220)
    (hub,) = _of(ops, "box", "hub")
    assert hub["shape"] == "ELLIPSE" and hub["w"] == hub["h"] == 84 and hub["fill"] == "accent"
    sats = _of(ops, "box", "sat")
    assert len(sats) == 5 and all(s["fill"] == "background" and not s.get("line") and not s.get("text") for s in sats)
    logos = _of(ops, "image", "logo")
    assert len(logos) == 5 and logos[0]["asset"] == "chatgpt" and logos[4]["url"].endswith("pinterest.png")
    assert all(lg["w"] == pytest.approx(60 * 0.56) for lg in logos)
    links = _of(ops, "line", "link")
    assert len(links) == 5 and all(ln["color"] == "muted" for ln in links)
    assert h == 220


def test_hub_spoke_with_one_satellite_draws_a_dashed_link_in_line():
    ops, h = _render("hub_spoke", {"center": "GOOGLE", "hub_logo": "google", "hub_fill": "surface_dark", "sats": [{"label": "Votre site", "hl": True}],
                                   "link_dash": True, "link_color": "accent", "link_weight": 3}, w=360)
    (hub,) = _of(ops, "box", "hub")
    (sat,) = _of(ops, "box", "sat")
    (link,) = _of(ops, "line", "link")
    assert hub["x"] == 0 and sat["x"] + sat["w"] == pytest.approx(360)
    assert hub["y"] + hub["h"] / 2 == pytest.approx(sat["y"] + sat["h"] / 2) == pytest.approx(link["y1"]) == pytest.approx(link["y2"])
    assert link["dash"] == "DASH" and link["color"] == "accent" and link["weight"] == 3
    assert sat["line"]["color"] == "accent" and hub["shape"] == "ROUND_RECTANGLE"
    (logo,) = _of(ops, "image", "hub_logo")
    assert logo["asset"] == "google" and logo["tint"] == "on_dark"
    hub_text = next(o for o in _of(ops, "text", "hub_text"))
    assert hub_text["color"] == "on_dark" and hub_text["y"] >= logo["y"] + logo["h"] - 1


def test_diagram_compare_draws_each_component_in_its_panel_and_darkens_the_dark_one():
    panels = [
        {"eyebrow": "Modèle fragile", "component": "hub_spoke",
         "props": {"center": "GOOGLE", "sats": [{"label": "Votre site", "hl": True}], "link_dash": True},
         "text": "Tout le trafic dépend d'un seul canal."},
        {"ground": "dark", "eyebrow": "Modèle résilient", "component": "hub_spoke",
         "props": {"center": "Marque", "sats": LOGOS, "hub_shape": "disc"},
         "text": "Plusieurs points de contact se relaient."},
    ]
    ops, h = _render("diagram_compare", {"panels": panels}, w=640)
    boxes = _of(ops, "box", "panel")
    assert [b["fill"] for b in boxes] == ["surface", "surface_dark"]
    assert boxes[0]["h"] == boxes[1]["h"] == h
    assert boxes[1]["x"] > boxes[0]["x"] + boxes[0]["w"]
    eyebrows = _of(ops, "text", "eyebrow")
    assert [e["text"] for e in eyebrows] == ["MODÈLE FRAGILE", "MODÈLE RÉSILIENT"] and [e["color"] for e in eyebrows] == ["ink", "accent"]
    texts = _of(ops, "text", "panel_text")
    assert [t["color"] for t in texts] == ["text", "on_dark"]
    # the dark panel's hub_spoke got dark=True: muted links, inside the panel
    links = _of(ops, "line", "link")
    right = [ln for ln in links if ln["x1"] > boxes[1]["x"]]
    assert len(right) == 5 and all(ln["color"] == "muted" for ln in right)
    assert all(boxes[1]["x"] < ln["x2"] < boxes[1]["x"] + boxes[1]["w"] for ln in right)
    with pytest.raises(ValueError, match="panel 2.*hub_spoke"):
        components.render("diagram_compare", {"panels": [panels[0], {"component": "hub_spoke", "props": {}}]}, PERISCOPE, 640)


# --- lot C: funnel_stages ------------------------------------------------------------------------

STAGES = [
    {"title": "TOFU · informationnel, froid", "sub": "« grippe a », « hantavirus france »", "note": "-20 à -50 %", "note_sub": "clic capté par l'IA"},
    {"title": "MOFU · considération", "sub": "« comment déduire un don »", "note": "partiel", "note_sub": "clic préservé si réassurance"},
    {"title": "BOFU · transactionnel", "sub": "don · pétition · collecte", "text": "l'action se fait chez vous", "note": "résiste", "note_sub": "clic à forte valeur"},
]


def test_funnel_stages_join_into_one_funnel_with_notes_axis_and_conclusion():
    ops, h = _render("funnel_stages", {"stages": STAGES, "stage_header": "Étage du funnel", "note_header": "Impact de l'IA sur le clic",
                                       "axis": "Intention d'agir",
                                       "conclusion": {"title": "Le focus SEO de Pasteur", "text": "Là où le clic survit à l'IA\n**et où il rapporte : le bas de funnel**"}},
                     w=640)
    bodies = _of(ops, "box", "stage")
    sides = _of(ops, "box", "stage_side")
    assert [b["fill"] for b in bodies] == ["accent_alt", "surface", "accent"]
    assert len(sides) == 6 and {s["shape"] for s in sides} == {"RIGHT_TRIANGLE"}
    lefts, rights = sides[0::2], sides[1::2]
    assert all(lf["flip"] == "xy" and rt["flip"] == "y" for lf, rt in zip(lefts, rights))
    # one straight edge: the same slope for every stage, and each stage starts where the line has got to
    slopes = [lf["w"] / lf["h"] for lf in lefts]
    assert max(slopes) - min(slopes) < 1e-6
    tops = [lf["w"] * 2 + b["w"] for lf, b in zip(lefts, bodies)]
    assert tops == sorted(tops, reverse=True) and all(b["w"] < t for b, t in zip(bodies, tops))
    for upper, lower, lf in zip(lefts, lefts[1:], lefts[1:]):
        assert lower["x"] - upper["x"] == pytest.approx(slopes[0] * (lower["y"] - upper["y"]), abs=0.6)
    # notes on the right, each inside its stage's height
    notes = _of(ops, "text", "note")
    assert len(notes) == 3 and all(n["align"] == "END" and n["x"] + n["w"] == pytest.approx(640) for n in notes)
    assert all(b["y"] <= n["y"] + n["h"] / 2 <= b["y"] + b["h"] for n, b in zip(notes, bodies))
    assert all(n["x"] > b["x"] + b["w"] + lf["w"] for n, b, lf in zip(notes, bodies, lefts))
    headers = _of(ops, "text", "column_header")
    assert len(headers) == 2 and headers[0]["y"] == headers[1]["y"] and headers[0]["y"] + headers[0]["h"] <= bodies[0]["y"]
    (axis,) = _of(ops, "line", "axis")
    assert axis["end_arrow"] and axis["y1"] == pytest.approx(bodies[0]["y"]) and axis["y2"] == pytest.approx(bodies[-1]["y"] + bodies[-1]["h"])
    (label,) = _of(ops, "text", "axis_label")
    assert label["rotate"] == -90 and "I" in label["text"]
    (box,) = _of(ops, "box", "conclusion")
    assert box["fill"] == "surface_dark" and box["y"] > bodies[-1]["y"] + bodies[-1]["h"] and h == pytest.approx(box["y"] + box["h"])
    title = _of(ops, "text", "conclusion_title")[0]
    assert title["color"] == "accent" and title["align"] == "CENTER"


def test_funnel_stages_without_extras_takes_the_whole_width():
    ops, h = _render("funnel_stages", {"stages": ["Notoriété", "Considération", "Conversion", "Fidélisation"]}, w=400)
    bodies, sides = _of(ops, "box", "stage"), _of(ops, "box", "stage_side")
    assert len(bodies) == 4 and not _of(ops, "text", "note") and not _of(ops, "line", "axis")
    assert sides[0]["x"] == pytest.approx(0) and sides[1]["x"] + sides[1]["w"] == pytest.approx(400)
    assert [b["fill"] for b in bodies] == ["accent_alt", "surface", "accent", "surface_dark"]
    texts = _of(ops, "text", "stage_text")
    assert texts[3]["runs"][0][0]["color"] == "on_dark" and texts[0]["runs"][0][0]["color"] == "ink"
    assert h == pytest.approx(bodies[-1]["y"] + bodies[-1]["h"])


# --- lot D: vertical tree, fan_out -------------------------------------------------------------

COCON = {"root": {"label": "Pilier", "sub": "Faire un don à Pasteur"}, "children": ["Don & impôts (66 %)", "Votre reçu fiscal", "Ponctuel ou mensuel ?"]}


def test_tree_vertical_hangs_the_children_on_a_rail_under_the_root():
    ops, h = _render("tree", {"layout": "vertical", **COCON}, w=220)
    (root,) = _of(ops, "box", "root")
    kids = _of(ops, "box", "child")
    assert root["fill"] == "accent" and root["x"] == 0 and root["w"] == 220 and len(kids) == 3
    assert [r[0]["text"] for r in root["runs"]] == ["Pilier", "Faire un don à Pasteur"]
    assert all(k["x"] >= 18 and k["x"] + k["w"] == pytest.approx(220) for k in kids)
    assert [k["y"] for k in kids] == sorted(k["y"] for k in kids) and kids[0]["y"] > root["y"] + root["h"]
    (rail,) = _of(ops, "line", "rail")
    stubs = _of(ops, "line", "stub")
    assert rail["y1"] == pytest.approx(root["y"] + root["h"]) and rail["y2"] == pytest.approx(kids[-1]["y"] + kids[-1]["h"] / 2)
    assert len(stubs) == 3 and all(s["x1"] == rail["x1"] and s["x2"] == pytest.approx(k["x"]) and s["y1"] == pytest.approx(k["y"] + k["h"] / 2)
                                   for s, k in zip(stubs, kids))
    assert h == pytest.approx(kids[-1]["y"] + kids[-1]["h"])


def test_fan_out_curves_from_the_question_to_each_query_then_to_the_cocon():
    props = {"source": "« À quelle association donner pour un don ==déductible ?== »",
             "branches": ["don déductible 66 % ?", "reçu fiscal / cerfa", "plafond de déduction", "don ponctuel ou mensuel ?"],
             "target": COCON, "source_label": "Question posée à l'IA", "branches_label": "Query fan-out", "target_label": "Cocon « Faire un don »"}
    ops, h = _render("fan_out", props, w=700)
    (src,) = _of(ops, "box", "source")
    assert src["fill"] == "surface_dark"
    (src_text,) = _of(ops, "text", "source_text")
    runs = src_text["runs"][0]
    assert [r["text"] for r in runs] == ["« À quelle association donner pour un don ", "déductible ?", " »"]
    assert runs[1]["color"] == "accent" and runs[1]["bold"] and runs[0]["color"] == "on_dark"
    branches = _of(ops, "box", "branch")
    assert len(branches) == 4 and all(b["fill"] == "background" and b["line"]["color"] == "rule" for b in branches)
    curves = _of(ops, "line", "fan")
    assert len(curves) == 4 and all(c["curve"] and c["color"] == "accent" for c in curves)
    for c, b in zip(curves, branches):
        assert c["x1"] == pytest.approx(src["x"] + src["w"]) and c["y1"] == pytest.approx(src["y"] + src["h"] / 2)
        assert c["x2"] == pytest.approx(b["x"]) and c["y2"] == pytest.approx(b["y"] + b["h"] / 2)
    (dot,) = _of(ops, "box", "dot")
    assert dot["x"] + dot["w"] / 2 == pytest.approx(src["x"] + src["w"])
    (arrow,) = _of(ops, "line", "arrow")
    (root,) = _of(ops, "box", "root")
    assert arrow["end_arrow"] and branches[0]["x"] + branches[0]["w"] < arrow["x1"] < arrow["x2"] < root["x"]
    assert root["x"] + root["w"] <= 700.5
    labels = _of(ops, "text", "column_label")
    assert len(labels) == 3 and len({lb["y"] for lb in labels}) == 1 and labels[2]["x"] == pytest.approx(root["x"])
    assert labels[0]["y"] + labels[0]["h"] <= min(b["y"] for b in branches)
    alone, _ = _render("fan_out", {"source": "Question", "branches": ["a", "b"]}, w=500)
    assert not _of(alone, "line", "arrow") and not _of(alone, "box", "root") and not _of(alone, "text", "column_label")
    assert max(b["x"] + b["w"] for b in _of(alone, "box", "branch")) == pytest.approx(500)


@pytest.mark.parametrize("name", ["card", "card_grid", "stack", "hub_spoke", "tree", "diagram_compare", "funnel_stages", "fan_out"])
def test_examples_and_variants_render_in_both_themes(name):
    entry = next(e for e in components.catalogue() if e["name"] == name)
    assert entry["use"] and entry["variants"]
    for theme in (PERISCOPE, themes.load("default")):
        for props in [entry["example"]["props"]] + [v["props"] for v in entry["variants"]]:
            ops, height = components.render(name, props, theme, 640)
            draw.ops_to_requests("s", ops, theme, prefix="cmp", resolve_asset=_assets)
            assert height > 0


# --- steps: the disc on the first line of its text ------------------------------------------

@pytest.mark.parametrize("dark", [False, True])
def test_steps_disc_is_centred_on_the_capitals_of_the_first_line(dark):
    items = ["Audit technique", "Plan de **contenus**", "Netlinking : une phrase assez longue pour passer sur deux lignes dans une colonne étroite"]
    ops, h = _render("steps", {"items": items, "dark": dark}, w=260)
    discs = [o for o in _of(ops, "box") if o.get("shape") == "ELLIPSE"]
    texts = _of(ops, "text")
    texts = [t for t in texts if "markdown" in t]
    assert len(discs) == len(texts) == 3
    size = PERISCOPE.text_style("step_text")["size"]
    for d, t in zip(discs, texts):
        assert d["y"] + d["h"] / 2 == pytest.approx(_caps_centre({**t, "size": size}))
    # rows do not overlap and the height covers the last disc and text
    for (d, t), (d2, t2) in zip(zip(discs, texts), zip(discs[1:], texts[1:])):
        assert min(d2["y"], t2["y"]) >= max(d["y"] + d["h"], t["y"] + t["h"])
    assert h >= max(discs[-1]["y"] + discs[-1]["h"], texts[-1]["y"] + texts[-1]["h"]) - 0.01


# --- personas: text clear of the rounded corners, labels clear of their bars --------------------

def _clearance(card, text, size=10):
    """Distance from the first glyph of ``text`` to the rounded corner of ``card`` (Slides: radius = 1/6 of the smaller side)."""
    import math
    r = min(card["w"], card["h"]) / 6
    gx, gy = text["x"] + INSET_X - card["x"], _caps_centre({**text, "size": size}) - 0.35 * size - card["y"]
    if gx >= r or gy >= r:
        return min(gx, gy) if gx < r else gx
    return r - math.hypot(r - gx, r - gy)


def test_persona_sheet_card_texts_clear_their_rounded_corners():
    entry = next(e for e in components.catalogue() if e["name"] == "persona_sheet")
    for props in [entry["example"]["props"]] + [v["props"] for v in entry["variants"]]:
        ops, _ = _render("persona_sheet", props, w=660)
        cards = {o["role"][:-5]: o for o in ops if o["op"] == "box" and o.get("role", "").endswith("_card")}
        texts = {o["role"]: o for o in ops if o["op"] == "text" and o.get("role") in cards}
        assert cards and set(cards) == set(texts)
        for role, card in cards.items():
            assert _clearance(card, texts[role]) >= 8, role
            assert texts[role]["x"] + texts[role]["w"] <= card["x"] + card["w"] + 0.01


def test_persona_card_labels_clear_their_gauges_devices_and_logos():
    entry = next(e for e in components.catalogue() if e["name"] == "persona_card")
    ops, _ = _render("persona_card", {**entry["example"]["props"], "brands": ["google", "share"]}, w=600)
    for label_role, below_role, kind in (("gauge_label", "gauge_track", "box"), ("devices_label", "device", "box"), ("brands_label", "brand", "image")):
        labels = _of(ops, "text", label_role)
        belows = _of(ops, kind, below_role)
        assert labels and belows, label_role
        for lb in labels:
            baseline = _caps_centre({**lb, "size": 10}) + 0.35 * 10
            under = min((b for b in belows if b["y"] > lb["y"]), key=lambda b: b["y"])
            assert under["y"] - baseline >= 5.5, (label_role, under["y"] - baseline)


def test_persona_card_labels_start_on_the_left_edge_of_their_bars_and_chips():
    entry = next(e for e in components.catalogue() if e["name"] == "persona_card")
    ops, _ = _render("persona_card", entry["example"]["props"], w=600)
    track = _of(ops, "box", "gauge_track")[0]
    chip = _of(ops, "box", "device")[0]
    assert all(lb["x"] + INSET_X == pytest.approx(track["x"]) for lb in _of(ops, "text", "gauge_label"))
    assert _of(ops, "text", "devices_label")[0]["x"] + INSET_X == pytest.approx(chip["x"])
