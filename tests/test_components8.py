"""Design-system brand components: button, button_row, hashtags, eyebrow, content_card(s),
section_header, client_ticker, do_dont."""

import pytest

from gslides_mcp import components, draw, themes
from gslides_mcp.components.brand import THIN

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None, theme=PERISCOPE):
    ops, height = components.render(name, props, theme, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, theme, prefix="cmp",
                                     resolve_asset=lambda name, tint=None: ("fid_" + name, (120, 120)))
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def test_button_follows_its_ground():
    (white,), _ = _render("button", {"text": "Contact"})
    assert white["shape"] == "ROUND_RECTANGLE" and white["fill"] == "ink" and white["color"] == "on_dark"
    (dark,), _ = _render("button", {"text": "Nos réalisations", "ground": "dark"})
    assert dark["fill"] is None and dark["line"]["color"] == "on_dark" and dark["color"] == "on_dark"
    (cyan,), _ = _render("button", {"text": "Voir le show reel", "ground": "cyan"})
    assert cyan["fill"] == "ink"
    (outline,), _ = _render("button", {"text": "En savoir plus", "variant": "outline"})
    assert outline["fill"] is None and outline["line"]["color"] == "ink"
    (accent,), _ = _render("button", {"text": "Et pourquoi pas vous ?", "ground": "dark", "color": "accent"})
    assert accent["line"]["color"] == "accent" and accent["w"] > white["w"]
    with pytest.raises(ValueError, match="ground"):
        components.render("button", {"text": "x", "ground": "pink"}, PERISCOPE, 100)


def test_button_row_lays_pills_side_by_side_and_can_centre():
    ops, h = _render("button_row", {"items": [{"text": "Contact"}, {"text": "En savoir plus", "variant": "outline"}]})
    assert len(ops) == 2 and ops[1]["x"] > ops[0]["x"] + ops[0]["w"] and ops[1]["fill"] is None and h == ops[0]["h"]
    centred, _ = _render("button_row", {"items": ["A", "B"], "align": "CENTER"}, w=600)
    assert centred[0]["x"] > 100 and centred[1]["x"] + centred[1]["w"] < 500


def test_hashtags_are_plain_uppercase_runs_ink_or_accent_on_dark():
    (op,), _ = _render("hashtags", {"items": ["IA", "#data", "Éco conception"]})
    tags = [r["text"] for r in op["runs"][0] if r["text"].strip()]
    assert tags == ["#IA", "#DATA", "#ÉCO CONCEPTION"] and all(r.get("color") == "ink" for r in op["runs"][0] if r["text"].strip())
    assert not op.get("fill") and op["op"] == "text"
    (dark,), _ = _render("hashtags", {"items": ["IA"], "dark": True})
    assert dark["runs"][0][0]["color"] == "accent"


def test_eyebrow_is_tracked_uppercase():
    (op,), h = _render("eyebrow", {"text": "Digitale depuis 1999"})
    assert op["text"] == THIN.join("DIGITALE DEPUIS 1999") and op["bold"] and op["color"] == "ink" and h > 0
    (plain,), _ = _render("eyebrow", {"text": "abc", "tracking": False, "dark": True})
    assert plain["text"] == "ABC" and plain["color"] == "accent"


def test_content_card_grounds_and_cta_rule():
    props = {"ground": "dark", "eyebrow": "Show reel", "title": "Nous sommes l'agence engagée.", "text": "2 minutes.", "tags": ["UX"],
             "cta": "Lire la vidéo"}
    ops, h = _render("content_card", props, w=220)
    (card,) = _of(ops, "box", "card")
    assert card["fill"] == "surface_dark" and card["line"] is None and card["shape"] == "ROUND_RECTANGLE" and card["h"] == h
    assert _of(ops, "text", "eyebrow")[0]["color"] == "accent" and _of(ops, "text", "title")[0]["color"] == "on_dark"
    assert _of(ops, "text", "tags")[0]["text"] == "#UX" and _of(ops, "text", "tags")[0]["color"] == "accent"
    (btn,) = _of(ops, "box", "button")
    assert btn["fill"] is None and btn["line"]["color"] == "on_dark" and btn["y"] + btn["h"] < h
    white, _ = _render("content_card", {"title": "Mirova", "cta": "Voir"}, w=220)
    assert _of(white, "box", "card")[0]["line"]["color"] == "rule" and _of(white, "box", "button")[0]["fill"] == "ink"
    cyan, _ = _render("content_card", {"ground": "cyan", "title": "Équipe", "cta": "L'équipe"}, w=220)
    assert _of(cyan, "box", "card")[0]["fill"] == "accent" and _of(cyan, "box", "button")[0]["fill"] == "ink"


def test_content_cards_equalise_heights_and_pin_ctas_to_the_bottom():
    cards = [{"ground": "white", "eyebrow": "Réalisation", "title": "Mirova", "text": "Un site carbone-light, accessible AA, qui double le temps passé sur les articles.", "tags": ["UX", "ÉCO"]},
             {"ground": "cyan", "title": "Équipe", "cta": "L'équipe"},
             {"ground": "dark", "title": "Show reel", "cta": "Lire"}]
    ops, h = _render("content_cards", {"cards": cards}, w=660)
    frames = _of(ops, "box", "card")
    assert len(frames) == 3 and len({f["h"] for f in frames}) == 1 and frames[0]["h"] == h
    assert [f["fill"] for f in frames] == ["background", "accent", "surface_dark"]
    btns = _of(ops, "box", "button")
    assert len(btns) == 2 and btns[0]["y"] == btns[1]["y"] and btns[0]["y"] + btns[0]["h"] < h


def test_section_header_highlight_eyebrow_text_and_tags():
    ops, h = _render("section_header", {"eyebrow": "Équipe", "title": "60 periscopers pour des expériences ==éco-conçues==.",
                                        "text": "De la stratégie au site.", "tags": ["IA", "DATA"]})
    (title,) = _of(ops, "text", "title")
    assert title["markdown"].count("==") == 2 and title["highlight"] == "highlight_alt" and title["style"] == "title"
    assert _of(ops, "text", "eyebrow")[0]["y"] < title["y"] < _of(ops, "text", "body")[0]["y"] < _of(ops, "text", "hashtags")[0]["y"]
    assert h >= _of(ops, "text", "hashtags")[0]["y"]
    dark, _ = _render("section_header", {"title": "x", "dark": True, "tags": ["IA"]})
    assert _of(dark, "text", "title")[0]["color"] == "on_dark" and _of(dark, "text", "hashtags")[0]["runs"][0][0]["color"] == "accent"


def test_client_ticker_is_a_dark_band_of_bold_names():
    ops, h = _render("client_ticker", {"names": ["MSF", "UCPA", "Mirova"]}, w=600)
    (band,) = _of(ops, "box", "band")
    (names,) = _of(ops, "text", "names")
    assert band["fill"] == "surface_dark" and band["h"] == h and names["color"] == "on_dark" and names["align"] == "CENTER"
    runs = names["runs"][0]
    assert [r["text"] for r in runs if r.get("bold")] == ["MSF", "UCPA", "Mirova"] and "·" in runs[1]["text"] and runs[1]["color"] == "accent"
    light, _ = _render("client_ticker", {"names": ["A"], "dark": False})
    assert _of(light, "box", "band")[0]["fill"] == "surface"


def test_do_dont_pairs_side_by_side_with_equal_heights():
    pairs = [{"do": "« Digitale depuis 1999. »", "do_note": "Trois mots.", "dont": "« Fort de plus de 25 ans d'expertise dans le domaine du digital, nous… »"},
             {"do": "« Nous. »", "dont": "« Je. »"}]
    ops, h = _render("do_dont", {"pairs": pairs}, w=600)
    dos, donts = _of(ops, "box", "do"), _of(ops, "box", "dont")
    assert len(dos) == len(donts) == 2 and dos[0]["fill"] == "success_bg" and donts[0]["fill"] == "danger_bg"
    assert dos[0]["h"] == donts[0]["h"] and dos[0]["y"] == donts[0]["y"] and donts[0]["x"] > dos[0]["x"] + dos[0]["w"]
    assert dos[1]["y"] > dos[0]["y"] + dos[0]["h"] and h == pytest.approx(dos[1]["y"] + dos[1]["h"])
    assert _of(ops, "text", "do_label")[0]["text"].startswith("✓") and _of(ops, "text", "dont_label")[0]["color"] == "danger_ink"
    assert len(_of(ops, "text", "do_note")) == 1 and _of(ops, "text", "do_text")[0]["style"] == "quote"


def test_brand_components_have_use_and_render_in_both_themes():
    names = {"button", "button_row", "hashtags", "eyebrow", "content_card", "content_cards", "section_header", "client_ticker", "do_dont"}
    for entry in components.catalogue():
        if entry["name"] not in names:
            continue
        names.discard(entry["name"])
        assert entry["use"], entry["name"]
        for theme in (PERISCOPE, themes.load("default")):
            ops, height = components.render(entry["name"], entry["example"]["props"], theme, 600)
            draw.ops_to_requests("s", ops, theme, prefix="cmp")
            assert height > 0, entry["name"]
    assert not names
