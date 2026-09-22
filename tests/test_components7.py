"""Bilan média reporting blocks: analysis_block, source_note, stat_box, takeaways,
placeholder, ad_scoreboard, gallery, media_plan, timeline_arrow."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None, theme=PERISCOPE):
    ops, height = components.render(name, props, theme, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, theme, prefix="cmp",
                                     resolve_asset=lambda name, tint=None: ("fid_" + name, (120, 120)))
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


# --- reporting blocks ------------------------------------------------------------------------

def test_analysis_block_title_chevrons_or_paragraph_and_optional_box():
    ops, height = _render("analysis_block", {"items": ["Google porte 77 % de la collecte", "Le ROAS baisse"]}, w=500)
    (title,) = _of(ops, "text", "title")
    assert title["text"] == "Notre analyse :" and title["style"] == "callout_title"
    (body,) = _of(ops, "text", "body")
    assert body["y"] >= title["y"] + title["h"] - 2 and body["style"] == "list"
    assert body["runs"][0][0]["text"].startswith("›") and body["runs"][1][1]["text"] == "Le ROAS baisse"
    assert not _of(ops, "box") and height == pytest.approx(body["y"] + body["h"])
    para, _ = _render("analysis_block", {"text": "La CFA 2025 totalise **130 311 €**.", "title": "Lecture :", "box": True}, w=500)
    (body,) = _of(para, "text", "body")
    assert "markdown" in body and _of(para, "text", "title")[0]["text"] == "Lecture :"
    (box,) = _of(para, "box", "frame")
    assert box["line"]["color"] == "accent" and box["fill"] is None and box["x"] == 0 and body["x"] > 0


def test_source_note_caption_right_aligned_with_platform_line():
    ops, height = _render("source_note", {"text": "Google Ads du 01/12/2025 au 31/12/2025", "platform": "Google Ads"}, w=300)
    (src,) = _of(ops, "text", "source")
    assert src["text"] == "* Sources : Google Ads du 01/12/2025 au 31/12/2025" and src["align"] == "END" and src["italic"]
    (plat,) = _of(ops, "text", "platform")
    assert plat["text"] == "Google Ads" and plat["y"] > src["y"] and plat["color"] == "muted"
    assert height == pytest.approx(plat["y"] + plat["h"])
    logo, _ = _render("source_note", {"text": "* Sources : CMP", "logo": "google-ads", "platform": "Google Ads", "align": "START"}, w=300)
    assert _of(logo, "text", "source")[0]["text"] == "* Sources : CMP"
    (img,) = _of(logo, "image")
    assert img["asset"] == "google-ads" and _of(logo, "text", "platform")[0]["x"] > img["x"]


def test_stat_box_outlined_figures_with_an_operator():
    ops, height = _render("stat_box", {"boxes": [{"value": "63 %", "label": "Acceptation des cookies"},
                                                 {"value": "63 %", "label": "Des données sont remontées"}]}, w=500)
    boxes = _of(ops, "box", "stat_box")
    assert len(boxes) == 2 and boxes[0]["line"]["color"] == "accent" and boxes[0]["fill"] is None
    (op,) = _of(ops, "text", "operator")
    assert op["text"] == "=" and boxes[0]["x"] + boxes[0]["w"] < op["x"] + op["w"] / 2 < boxes[1]["x"]
    values = _of(ops, "text", "value")
    assert [v["text"] for v in values] == ["63 %", "63 %"] and values[0]["align"] == "CENTER"
    assert boxes[0]["x"] > 0 and boxes[1]["x"] + boxes[1]["w"] < 500  # centred as a group
    assert height == boxes[0]["h"]
    arrow, _ = _render("stat_box", {"boxes": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}, {"value": "3", "label": "c"}],
                                    "operator": "→"}, w=500)
    assert [o["text"] for o in _of(arrow, "text", "operator")] == ["→", "→"]


def test_takeaways_bold_titles_optionally_highlighted_and_paragraphs():
    items = [{"title": "Sécuriser le budget des derniers jours", "text": "Les 7 derniers jours concentrent 52 % de la collecte."},
             {"title": "Réévaluer le budget search", "text": "Environ 56 851 € de collecte potentielle perdue."}]
    ops, height = _render("takeaways", {"items": items}, w=500)
    titles = _of(ops, "text", "title")
    bodies = _of(ops, "text", "body")
    assert [t["text"] for t in titles] == [i["title"] for i in items] and titles[0]["bold"]
    assert titles[0]["y"] < bodies[0]["y"] < titles[1]["y"] < bodies[1]["y"] and height >= bodies[1]["y"] + bodies[1]["h"]
    hl, _ = _render("takeaways", {"items": items, "highlight": True}, w=500)
    assert _of(hl, "text", "title")[0]["markdown"] == "==Sécuriser le budget des derniers jours=="
    plain, _ = _render("takeaways", {"items": ["_ Un premier enseignement", "_ Un second"]}, w=500)
    assert not _of(plain, "text", "title") and len(_of(plain, "text", "body")) == 2


def test_placeholder_is_a_dashed_surface_box_with_centred_text():
    ops, height = _render("placeholder", {"text": "En attente des exports de dons (5 ans idéalement)"}, w=500)
    (box,) = _of(ops, "box", "placeholder")
    assert box["fill"] == "surface" and box["line"]["dash"] == "DASH" and box["h"] == 120 == height
    assert box["text"].startswith("En attente") and box["align"] == "CENTER" and box["valign"] == "MIDDLE" and box["color"] == "muted"
    solid, h = _render("placeholder", {"text": "x", "height": 80, "dash": False}, w=100)
    assert "dash" not in solid[0]["line"] and h == 80


# --- ad_scoreboard / gallery -----------------------------------------------------------------

def test_ad_scoreboard_transposed_table_with_image_row_and_placeholders():
    ads = [{"name": "Post vidéo", "image": "post-video",
            "values": {"Dépenses": "7 237,84 €", "CTR (clics)": "0,13 %", "Dons (régie)": "238", "CPA": "30,41 €"}},
           {"name": "Carrousel defisc",
            "values": {"Dépenses": "224,50 €", "CTR (clics)": "0,14 %", "Dons (régie)": "16", "CPA": "14,03 €"}}]
    metrics = ["Dépenses", "CTR (clics)", "Dons (régie)", "CPA"]
    ops, height = _render("ad_scoreboard", {"ads": ads, "metrics": metrics, "top_note": "Top annonce : Carrousel defisc"}, w=600)
    (t,) = _of(ops, "table")
    assert t["rows"][0] == ["Nom visuel", "Post vidéo", "Carrousel defisc"]
    assert t["rows"][1] == ["Visuel", "", ""] and t["rows"][2] == ["Dépenses", "7 237,84 €", "224,50 €"]
    assert t["rows"][-1][0] == "CPA" and len(t["rows"]) == 6
    assert t["header"]["fill"] == "ink" and t["cell_fills"][(1, 0)] == "accent" and t["cell_fills"][(5, 0)] == "accent"
    assert t["row_heights"][1] == 56 + 8 and t["row_heights"][2] == t["row_h"]
    (img,) = _of(ops, "image")
    assert img["asset"] == "post-video" and img["contain"] and t["row_heights"][0] < img["y"] < t["row_heights"][0] + 8
    assert t["col_w"][0] < img["x"] < t["col_w"][0] + t["col_w"][1]
    (ph,) = _of(ops, "box", "placeholder")
    assert ph["line"]["dash"] == "DASH" and ph["x"] > img["x"]
    (note,) = _of(ops, "text", "top_note")
    assert note["text"] == "Top annonce : Carrousel defisc" and note["align"] == "END" and note["y"] >= sum(t["row_heights"])
    assert height == pytest.approx(note["y"] + note["h"])


def test_gallery_fixed_ratio_cells_placeholders_and_captions():
    ops, height = _render("gallery", {"images": ["visuel-1", None, {"url": "https://x/y.png", "caption": "Post defisc"}],
                                      "captions": True}, w=600)
    imgs = _of(ops, "image")
    assert len(imgs) == 2 and imgs[0]["asset"] == "visuel-1" and imgs[0]["contain"] and imgs[1]["url"] == "https://x/y.png"
    assert imgs[0]["w"] / imgs[0]["h"] == pytest.approx(0.62, abs=0.01)
    (ph,) = _of(ops, "box", "placeholder")
    assert ph["line"]["dash"] == "DASH" and ph["text"].startswith("Capture de l") and imgs[0]["x"] < ph["x"] < imgs[1]["x"]
    caps = _of(ops, "text", "caption")
    assert [c["text"] for c in caps] == ["Post defisc"] and caps[0]["y"] >= imgs[1]["y"] + imgs[1]["h"]
    assert height > imgs[0]["h"]
    two, h2 = _render("gallery", {"images": [None, None], "cols": 2, "ratio": 1.0}, w=300)
    phs = _of(two, "box", "placeholder")
    assert all(b["w"] == pytest.approx(b["h"]) for b in phs) and h2 == pytest.approx(phs[0]["h"])


# --- media_plan / timeline_arrow -------------------------------------------------------------

def test_media_plan_levers_with_logos_budget_dates_and_objective_panel():
    props = {"levers": [{"name": "Search + Demand Gen", "logos": ["google-ads", "microsoft-ads"], "budget": "16 000 € HT",
                         "dates": "du 09/02/2026 au 08/03/2026"},
                        {"name": "Social", "logos": ["meta"], "budget": "18 000 € HT", "dates": "du 09/02/2026 au 08/03/2026"}],
             "objective": {"title": "Objectif à atteindre",
                           "items": ["Développer le nombre de demandes de brochures", "Accroître la notoriété sur le legs"]}}
    ops, height = _render("media_plan", props, w=800)
    names = _of(ops, "text", "lever")
    assert [n["text"] for n in names] == ["SEARCH + DEMAND GEN", "SOCIAL"] and names[0]["bold"]
    dots = _of(ops, "box", "dot")
    assert len(dots) == 2 and dots[0]["fill"] == "accent" and dots[0]["shape"] == "ELLIPSE"
    logos = _of(ops, "image")
    assert [lg["asset"] for lg in logos] == ["google-ads", "microsoft-ads", "meta"] and logos[0]["x"] > names[0]["x"]
    lines = _of(ops, "text", "detail")
    assert lines[0]["runs"][0][0]["text"] == "Ordre d'insertion : " and lines[0]["runs"][0][1] == {"text": "16 000 € HT", "bold": True}
    assert lines[1]["runs"][0][0]["text"] == "Date : "
    (panel,) = _of(ops, "box", "objective")
    assert panel["fill"] == "accent" and panel["x"] == pytest.approx(800 * 0.55) and panel["w"] == pytest.approx(800 * 0.45)
    assert panel["h"] == height and _of(ops, "text", "objective_title")[0]["text"] == "Objectif à atteindre"
    (chev,) = _of(ops, "text", "objective_items")
    assert chev["x"] > panel["x"] and chev["runs"][0][0]["text"].startswith("›")
    (head,) = _of(ops, "text", "heading")
    assert head["text"] == "Leviers déployés" and head["y"] < dots[0]["y"]
    alone, h2 = _render("media_plan", {"levers": props["levers"]}, w=800)
    assert not _of(alone, "box", "objective") and h2 <= height


def test_timeline_arrow_alternating_boxes_styles_and_connectors():
    events = [{"date": "11/04", "text": "Début de la campagne", "style": "filled"},
              {"date": "07/05", "text": "Basculer MDD IR « don cancer »"},
              {"date": "07/05", "text": "Ajout du widget « montant favoris »", "style": "dashed"},
              {"date": "15/05", "text": "Bascule Meta sur MDD IR", "style": "outline"}]
    ops, height = _render("timeline_arrow", {"events": events}, w=700)
    (arrow,) = _of(ops, "line", "arrow")
    assert arrow["end_arrow"] == "arrow" and arrow["color"] == "accent" and arrow["weight"] >= 6 and arrow["x2"] == 700
    boxes = _of(ops, "box", "event")
    assert len(boxes) == 4
    assert boxes[0]["y"] > arrow["y1"] and boxes[1]["y"] + boxes[1]["h"] < arrow["y1"]  # below, then above
    assert boxes[2]["y"] > arrow["y1"] and boxes[3]["y"] < arrow["y1"]
    assert boxes[0]["fill"] == "accent" and boxes[0]["line"] is None
    assert boxes[1]["line"]["dash"] == "DASH" and boxes[1]["fill"] is None  # default style: dashed
    assert boxes[2]["line"]["dash"] == "DASH" and "dash" not in boxes[3]["line"]
    assert boxes[0]["runs"][0][0] == {"text": "11/04", "bold": True} and boxes[0]["runs"][1][0]["text"] == "Début de la campagne"
    conns = _of(ops, "line", "connector")
    assert len(conns) == 4 and all(c["x1"] == c["x2"] for c in conns)
    assert boxes[0]["x"] < boxes[1]["x"] < boxes[2]["x"] < boxes[3]["x"] and height >= boxes[0]["y"] + boxes[0]["h"]
    forced, _ = _render("timeline_arrow", {"events": [{"date": "a", "text": "x", "above": True}, {"date": "b", "text": "y", "above": True}]}, w=400)
    assert all(b["y"] < _of(forced, "line", "arrow")[0]["y1"] for b in _of(forced, "box", "event"))


def test_every_component_has_a_use_and_its_example_renders_in_both_themes():
    for entry in components.catalogue():
        assert entry["use"], entry["name"]
        for theme in (PERISCOPE, themes.load("default")):
            ops, height = components.render(entry["name"], entry["example"]["props"], theme, 600)
            draw.ops_to_requests("s", ops, theme, prefix="cmp", resolve_asset=lambda name, tint=None: ("fid", (100, 100)))
            assert height > 0, entry["name"]
