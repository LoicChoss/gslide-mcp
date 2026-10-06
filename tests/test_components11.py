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
