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
