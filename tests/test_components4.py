"""Lot 4 built-ins: agenda, numbered_list, big_numbers, phase_cards, compare_cards,
before_after, stat_pair, palette, person_card, team_grid, logo_grid, logo_wall,
kpi_cards, gauge, target, chart_stacked, tree, flowchart, phone; plus stats.sub and
card variant plain."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")
LOT4 = ("agenda", "numbered_list", "big_numbers", "phase_cards", "compare_cards", "before_after", "stat_pair", "palette",
        "person_card", "team_grid", "logo_grid", "logo_wall", "kpi_cards", "gauge", "target", "chart_stacked", "tree",
        "flowchart", "phone")


def _render(name, props, w=400, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp", resolve_asset=lambda n, t: ("fid", (100, 50)))
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


def test_lot4_components_are_listed_and_examples_render_in_both_themes():
    cat = {c["name"] for c in components.catalogue()}
    assert set(LOT4) <= cat
    default = themes.load("default")
    for entry in components.catalogue():
        for theme in (PERISCOPE, default):
            ops, height = components.render(entry["name"], entry["example"]["props"], theme, 400)
            draw.ops_to_requests("s", ops, theme, prefix="cmp", resolve_asset=lambda n, t: ("fid", (100, 50)))
            assert height > 0


# --- text / structure -------------------------------------------------------------------

def test_agenda_chips_and_titles():
    ops, height = _render("agenda", {"items": ["Contexte", {"num": "A", "title": "Annexes"}], "dark": True})
    chips = _of(ops, "box", "chip")
    assert [c["text"] for c in chips] == ["01", "A"] and chips[0]["fill"] == "chip"
    titles = [o for o in ops if o["op"] == "text"]
    assert titles[0]["color"] == "on_dark" and "Contexte" in _texts(ops)
    assert height == 48


def test_numbered_list_circle_markers_index_cards_and_connector():
    ops, height = _render("numbered_list", {"items": [{"title": "Un", "sub": "détail", "icon": "bolt"}, "Deux"],
                                            "card": True, "connector": True})
    markers = _of(ops, "box", "marker")
    assert len(markers) == 2 and markers[0]["shape"] == "ELLIPSE" and "text" not in markers[0]  # icon replaces the number
    assert markers[1]["text"] == "2"
    assert [o["text"] for o in _of(ops, "text", "index")] == ["#1", "#2"]
    assert len(_of(ops, "image")) == 1 and _of(ops, "image")[0]["tint"] == "ink"
    cards = _of(ops, "box", "card")
    assert len(cards) == 2 and cards[0]["fill"] == "surface"
    (conn,) = _of(ops, "line", "connector")
    assert conn["weight"] == 4 and ops.index(conn) < ops.index(markers[0])  # drawn under the discs
    assert height > 2 * 40
    # no icon anywhere: the number lives in the disc alone, no « #n » beside it
    ops, _ = _render("numbered_list", {"items": ["Un", "Deux"]})
    assert [m["text"] for m in _of(ops, "box", "marker")] == ["1", "2"] and not _of(ops, "text", "index")
    assert not [o for o in ops if o["op"] == "line"]


def test_numbered_list_square_markers_uppercase_titles():
    ops, _ = _render("numbered_list", {"items": ["sources", "médias"], "marker": "square", "start": 3})
    markers = _of(ops, "box", "marker")
    assert [m["text"] for m in markers] == ["3", "4"] and "shape" not in markers[0]
    assert [t["text"] for t in _of(ops, "text", "title")] == ["SOURCES", "MÉDIAS"]
    assert not _of(ops, "line")


def test_big_numbers_highlighted_titles():
    ops, height = _render("big_numbers", {"items": [{"title": "3 niveaux,\njamais 4", "text": "Toute page…"}, {"num": "B", "title": "Une page"}]})
    nums = _of(ops, "text", "number")
    assert [n["text"] for n in nums] == ["1", "B"] and nums[0]["size"] == 54 and nums[0]["align"] == "CENTER"
    (t1, t2) = _of(ops, "text", "title")
    assert len(t1["runs"]) == 2 and t1["runs"][0][0]["highlight"] == "highlight" and t1["runs"][0][0]["bold"]
    assert nums[1]["x"] == 200
    assert height > 66 + 30


def test_phase_cards_equal_heights_numbers_and_deliverables():
    phases = [{"title": "Cadrage", "text": "court", "deliverables": ["KPI", "Plan"]}, {"title": "Dev", "icon": "bolt", "note": "note"}]
    ops, height = _render("phase_cards", {"phases": phases, "gap": 10})
    cards = _of(ops, "box", "card")
    assert len(cards) == 2 and len({c["h"] for c in cards}) == 1 and cards[0]["line"]["color"] == "accent"
    assert [n["text"] for n in _of(ops, "text", "number")] == ["1", "2"]
    assert cards[1]["x"] == pytest.approx(205)
    assert "LIVRABLES" in _texts(ops) and "KPI" in _texts(ops)
    assert len(_of(ops, "image")) == 1
    assert height == pytest.approx(cards[0]["y"] + cards[0]["h"])


def test_compare_cards_kinds_and_bad_kind_rejected():
    ops, _ = _render("compare_cards", {"cards": [{"kind": "bad", "label": "Idée reçue", "title": "T1"},
                                                 {"kind": "good", "label": "Réponse", "title": "T2", "text": "x"}, {"title": "T3"}]})
    cards = _of(ops, "box", "card")
    assert [c["fill"] for c in cards] == ["surface", "accent", "surface"]
    labels = _of(ops, "text", "label")
    assert labels[0]["text"].startswith("✗") and labels[0]["color"] == "coral"
    assert labels[1]["text"].startswith("✓") and labels[1]["color"] == "ink"
    assert len({c["h"] for c in cards}) == 1
    with pytest.raises(ValueError, match="kind"):
        components.render("compare_cards", {"cards": [{"kind": "meh", "title": "x"}]}, PERISCOPE, 300)


def test_before_after_panels_rules_note_and_arrow():
    ops, height = _render("before_after", {"before": {"title": "Actuel", "items": ["a", "b", "c"], "note": "plat"},
                                           "after": {"title": "Cible", "items": ["==x=="]}, "gap": 20})
    panels = _of(ops, "box", "panel")
    assert [p["fill"] for p in panels] == ["surface", "accent"] and panels[0]["h"] == panels[1]["h"] == height
    assert panels[1]["x"] == 210 and panels[0]["w"] == 190
    titles = _of(ops, "text", "title")
    assert titles[0]["text"] == "✗  ACTUEL" and titles[1]["text"] == "✓  CIBLE"
    assert len(_of(ops, "line", "rule")) == 4
    assert _of(ops, "text", "note")[0]["italic"] is True
    (arrow,) = _of(ops, "text", "arrow")
    assert arrow["x"] == 190 and arrow["w"] == 20


def test_stat_pair_runs_before_muted_after_bold():
    ops, height = _render("stat_pair", {"pairs": [{"label": "Pages", "before": "16 913", "after": "15 588"}]})
    (values,) = _of(ops, "text", "values")
    runs = values["runs"][0]
    assert runs[0]["text"] == "16 913" and runs[0]["color"] == "muted"
    assert runs[-1]["text"] == "15 588" and runs[-1]["bold"]
    assert _of(ops, "text", "label")[0]["text"] == "PAGES" and height == 58


def test_palette_swatches_with_ratio():
    ops, height = _render("palette", {"swatches": [{"color": "surface_dark", "text": "on_dark", "name": "Blanc / navy", "ratio": "8.12:1"}, "accent"], "cols": 2})
    sw = _of(ops, "box", "swatch")
    assert sw[0]["fill"] == "surface_dark" and sw[0]["color"] == "on_dark" and sw[0]["text"] == "Aa"
    assert sw[1]["x"] == 200 and sw[1]["color"] == "ink"
    assert "8.12:1" in _texts(ops) and height == 30


LONG = "Une phrase nettement plus longue que prévu, qui oblige le bloc à passer sur plusieurs lignes"


def test_lot4_body_texts_hold_at_13_pt_and_rows_share_one_geometry():
    cards = [{"kind": "bad", "label": "Idée reçue", "title": "Un titre assez long pour passer sur deux lignes", "text": "court"},
             {"kind": "good", "title": "Court", "text": "Un texte"}]
    ops, _ = _render("compare_cards", {"cards": cards})
    titles, texts = _of(ops, "text", "title"), [o for o in _of(ops, "text") if o.get("style") == "body"]
    assert len({t["y"] for t in titles}) == 1 and len({t["y"] for t in texts}) == 1  # no label, a one-line title: still aligned
    assert all(t["size"] >= 13 for t in titles + texts)
    phases = [{"title": "Cadrage", "text": LONG, "note": "n", "deliverables": ["a"]}, {"title": "Dev", "text": "court", "note": "n", "deliverables": ["b"]}]
    ops, _ = _render("phase_cards", {"phases": phases})
    assert len({lb["y"] for lb in _of(ops, "text", "deliverables")}) == 1
    # before_after: item k of the before faces item k of the after
    ops, _ = _render("before_after", {"before": {"title": "Avant", "items": [LONG, "b"]}, "after": {"title": "Après", "items": ["x", "y"]}})
    rules = _of(ops, "line", "rule")
    assert [r["y1"] for r in rules[:2]] == [r["y1"] for r in rules[2:]]
    # a wrapped agenda title makes its row taller rather than smaller
    ops, h = _render("agenda", {"items": ["Court", LONG]}, w=300)
    assert h > 2 * 24 and all(t["size"] == 13 for t in _of(ops, "text"))


def test_lot4_grids_drop_a_column_rather_than_cut_a_word():
    cards = [{"kind": "bad", "title": "a", "text": "Les sous-intentions"}, {"kind": "good", "title": "b"}, {"kind": "bad", "title": "c"}]
    ops, _ = _render("compare_cards", {"cards": cards}, w=420)
    boxes = _of(ops, "box", "card")
    assert boxes[2]["x"] == 0 and boxes[2]["y"] > 0 and not [o for o in ops if o["op"] == "warning"]  # 2 + 1
    # columns asked by the caller are kept: the word is reported instead
    ops, _ = _render("compare_cards", {"cards": cards, "cols": 3}, w=420)
    assert len({b["y"] for b in _of(ops, "box", "card")}) == 1
    assert any("sous-intentions" in o["text"] for o in ops if o["op"] == "warning")


def test_before_after_stacks_when_a_url_does_not_hold_and_warns_under_a_forced_height():
    props = {"before": {"title": "Avant", "items": ["opc.fr/conseils/cataracte/l-operation-de-la-cataracte"]},
             "after": {"title": "Après", "items": ["opc.fr/x"]}}
    ops, h = _render("before_after", props, w=420)
    a, b = _of(ops, "box", "panel")
    assert a["w"] == b["w"] == 420 and b["x"] == 0 and b["y"] > a["y"] + a["h"]
    assert _of(ops, "text", "arrow")[0]["text"] == "↓" and h == pytest.approx(b["y"] + b["h"])
    ops, h = _render("before_after", props, w=420, h=60)
    assert h == 60 and _of(ops, "box", "panel")[1]["x"] > 0 and [o for o in ops if o["op"] == "warning"]


def test_lot4_forced_height_too_small_warns_instead_of_shrinking():
    ops, h = _render("numbered_list", {"items": [{"title": LONG, "sub": LONG}]}, w=300, h=40)
    (warn,) = [o for o in ops if o["op"] == "warning"]
    assert warn["text"].startswith("numbered_list : items «") and warn["text"].endswith("trop long, raccourcir") and h == 40
    assert all(o["size"] >= 13 and not o.get("small_ok") for o in _of(ops, "text"))


# --- people / logos / kpi cards ---------------------------------------------------------

def test_person_card_photo_cover_or_initials():
    ops, height = _render("person_card", {"photo": "aurelie", "name": "Aurélie M.", "role": "Directrice", "bio": "Pilote le projet.", "contact": "a@b.fr"})
    (photo,) = _of(ops, "image")
    assert photo["cover"] is True and photo["w"] == photo["h"] == 64
    name = _of(ops, "text", "name")[0]
    assert name["x"] == 76 and name["text"] == "Aurélie M."
    assert height >= 64
    ops, _ = _render("person_card", {"name": "Jean Dupont", "layout": "top"})
    (ph,) = _of(ops, "box", "photo")
    assert ph["text"] == "JD" and _of(ops, "text", "name")[0]["y"] > 64


def test_team_grid_equalises_rows():
    people = [{"name": "A", "bio": "- a\n- b\n- c\n- d"}, {"name": "B"}, {"name": "C"}]
    ops, height = _render("team_grid", {"people": people, "cols": 2, "gap": 20})
    names = _of(ops, "text", "name")
    assert [round(n["x"]) for n in names] == [76, 286, 76]
    assert names[2]["y"] > names[0]["y"] and height > 2 * 64


def test_logo_grid_dividers_and_highlighted_titles():
    items = [{"logo": "google", "name": "Google Drive", "title": "Pour le stockage", "text": "x"},
             {"logo_url": "https://x/y.png", "name": "Jira", "title": "Pour la recette"}, {"name": "Git", "title": "Versioning"}]
    ops, height = _render("logo_grid", {"items": items, "cols": 3, "gap": 12})
    imgs = _of(ops, "image")
    assert imgs[0]["contain"] is True and imgs[0]["asset"] == "google" and imgs[1]["url"].startswith("https://")
    titles = _of(ops, "text", "title")
    assert titles[0]["runs"][0][0]["highlight"] == "highlight"
    divs = _of(ops, "line", "divider")
    assert len(divs) == 2 and divs[0]["dash"] == "DASH" and divs[0]["y2"] == height
    ops, _ = _render("logo_grid", {"items": items, "cols": 2, "dividers": False})
    assert not _of(ops, "line")


def test_logo_wall_fits_each_logo_in_its_cell():
    ops, height = _render("logo_wall", {"logos": ["a", "b", {"logo_url": "https://x/c.png", "name": "C"}], "cols": 3, "gap": 10, "cell_h": 40, "logo_h": 20})
    imgs = _of(ops, "image")
    assert len(imgs) == 3 and imgs[0]["contain"] is True and imgs[0]["h"] == 20 and "tint" not in imgs[0]
    ops2, _ = _render("logo_wall", {"logos": ["a"], "tint": "ink"})
    assert _of(ops2, "image")[0]["tint"] == "ink"
    assert imgs[1]["x"] > imgs[0]["x"] and height == 40
    with pytest.raises(ValueError, match="logo"):
        components.render("logo_wall", {"logos": [{"name": "no image"}]}, PERISCOPE, 300)


def test_kpi_cards_delta_sign_and_series_dots():
    ops, height = _render("kpi_cards", {"items": [{"label": "ChatGPT", "value": "11 454", "delta": "+12 %", "icon": "google"},
                                                  {"label": "Claude", "value": "4 391", "delta": "-3 %", "color": "coral"}], "gap": 10})
    deltas = _of(ops, "text", "delta")
    assert deltas[0]["text"].endswith("▲") and deltas[0]["color"] == "positive"
    assert deltas[1]["text"].endswith("▼") and deltas[1]["color"] == "negative"
    dots = _of(ops, "box", "dot")
    assert [d["fill"] for d in dots] == ["series_1", "coral"]
    assert len(_of(ops, "image")) == 1 and "tint" not in _of(ops, "image")[0]
    assert height == 54


def test_team_grid_texts_at_the_charter_size_one_geometry_per_row():
    people = [{"name": "Sébastien Nouvel-Martin", "role": "Développeur web", "bio": "Intégration et développement WordPress, maintenance."},
              {"name": "Théo L.", "bio": "Maquettes."}]
    ops, height = _render("team_grid", {"people": people, "cols": 2}, w=360)
    names, bios = _of(ops, "text", "name"), _of(ops, "text", "bio")
    # the names and bios of a row start on the same lines, whatever each one's length
    assert names[0]["y"] == names[1]["y"] and names[0]["h"] == names[1]["h"] and bios[0]["y"] == bios[1]["y"]
    assert all(o.get("size") is None for o in names + bios)  # drawn at the theme's 13 pt, the boxes sized for it
    assert bios[0]["h"] >= 2 * PERISCOPE.size("body") * 1.35 + 8
    # a forced height too small: the texts keep their size, the grid its natural height, and the caller is told
    short, h2 = _render("team_grid", {"people": people, "cols": 2}, w=360, h=40)
    assert h2 == pytest.approx(height) and [o for o in short if o["op"] == "warning" and o["text"].startswith("team_grid : bio")]


def test_people_markers_sit_on_the_capitals_and_logo_grid_rows_align():
    from gslides_mcp.components.builtin import caps_centre
    ops, _ = _render("kpi_cards", {"items": [{"label": "A", "value": "11 454"}]})
    dot, value = _of(ops, "box", "dot")[0], _of(ops, "text", "value")[0]
    assert dot["y"] + dot["h"] / 2 == pytest.approx(caps_centre(value["y"], value["size"]))
    items = [{"logo": "google", "name": "Google Drive", "title": "T"}, {"name": "Jira", "title": "Pour la recette du site web"}]
    ops, _ = _render("logo_grid", {"items": items, "cols": 2}, w=300)
    logo, names, titles = _of(ops, "image")[0], _of(ops, "text", "name"), _of(ops, "text", "title")
    assert logo["y"] + logo["h"] / 2 == pytest.approx(caps_centre(names[0]["y"], PERISCOPE.size("card_title")))
    assert titles[0]["y"] == titles[1]["y"] and titles[0]["h"] == titles[1]["h"] and titles[0].get("size") is None


# --- charts -----------------------------------------------------------------------------

def test_gauge_is_a_half_ring_with_value_and_label():
    ops, height = _render("gauge", {"value": 43, "label": "Autorité", "size": 140})
    (ring,) = _of(ops, "ring")
    assert ring["span"] == 180 and ring["start"] == 180 and ring["r"] == 70
    assert [s["value"] for s in ring["segments"]] == pytest.approx([0.43, 0.57])
    assert ring["segments"][1]["color"] == "track"
    assert _of(ops, "text", "value")[0]["text"] == "43" and _of(ops, "text", "label")[0]["text"] == "Autorité"
    assert 70 < height < 110
    ops, _ = _render("gauge", {"value": 120, "max": 100, "text": "Max"})
    assert len(_of(ops, "ring")[0]["segments"]) == 1 and _of(ops, "text", "value")[0]["text"] == "Max"


def test_target_concentric_rings_shrink_inwards():
    ops, height = _render("target", {"rings": [{"label": "A", "value": 80}, {"label": "B", "value": 50}, {"label": "C", "value": 30}],
                                     "thickness": 10, "gap": 4})
    rings = _of(ops, "ring")
    assert [r["r"] for r in rings] == [80, 66, 52] and all(r["cx"] == 80 for r in rings)
    assert rings[0]["segments"][0]["value"] == pytest.approx(0.8) and rings[0]["segments"][0]["color"] == "series_1"
    assert _of(ops, "box", "center")[0]["shape"] == "ELLIPSE"
    assert [t["text"] for t in ops if t["op"] == "text" and t.get("align") == "END"] == ["80 %", "50 %", "30 %"]


def test_chart_stacked_horizontal_segments_scale_to_the_max_total():
    ops, height = _render("chart_stacked", {"labels": ["A", "B"], "series": [{"name": "s1", "values": [40, 10]}, {"name": "s2", "values": [10, 10]}],
                                            "show_values": True, "bar_h": 10, "gap": 5}, w=400)
    segs = _of(ops, "box", "segment")
    assert len(segs) == 4 and segs[0]["fill"] == "series_1" and segs[1]["fill"] == "series_2"
    assert segs[1]["x"] == pytest.approx(segs[0]["x"] + segs[0]["w"])  # stacked
    assert segs[0]["w"] / segs[2]["w"] == pytest.approx(4)  # 40 vs 10 on the same scale
    assert [t["text"] for t in _of(ops, "text", "total")] == ["50", "20"]
    assert len(_of(ops, "box", "swatch")) == 2
    assert height > 25


def test_chart_stacked_vertical_stacks_from_the_baseline():
    ops, height = _render("chart_stacked", {"labels": ["A"], "series": [{"name": "s1", "values": [30]}, {"name": "s2", "values": [20]}],
                                            "horizontal": False, "legend": False, "max": 50}, w=200, h=150)
    segs = _of(ops, "box", "segment")
    base = _of(ops, "line")[0]["y1"]
    assert segs[0]["y"] + segs[0]["h"] == pytest.approx(base) and segs[1]["y"] + segs[1]["h"] == pytest.approx(segs[0]["y"])
    assert segs[0]["h"] + segs[1]["h"] == pytest.approx(base)  # 50/50 fills the plot height
    assert height == 150


# --- diagrams ---------------------------------------------------------------------------

def test_tree_root_bus_children_and_items():
    ops, height = _render("tree", {"root": "Accueil", "children": [{"label": "A", "items": ["a1", "a2"]}, {"label": "B", "hl": True}, "C"], "gap_x": 10})
    (root,) = _of(ops, "box", "root")
    assert root["fill"] == "accent" and root["x"] + root["w"] / 2 == 200
    kids = _of(ops, "box", "child")
    assert len(kids) == 3 and kids[1]["line"]["color"] == "accent" and kids[2]["text"] == "C"
    assert kids[0]["w"] == pytest.approx((400 - 20) / 3)
    (bus,) = _of(ops, "line", "bus")
    assert bus["y1"] == bus["y2"] and root["h"] < bus["y1"] < kids[0]["y"]
    assert len(_of(ops, "line")) == 1 + 1 + 3  # trunk + bus + one drop per child
    assert _of(ops, "text", "items")[0]["markdown"] == "- a1\n- a2" and height > kids[0]["y"] + kids[0]["h"]


def test_flowchart_grid_layout_and_elbow_arrows():
    props = {"nodes": [{"id": "a", "label": "A", "col": 0, "row": 0}, {"id": "b", "label": "B", "sub": "s", "col": 1, "row": 0, "fill": "surface_dark"},
                       {"id": "c", "label": "C", "col": 1, "row": 1}],
             "edges": [["a", "b"], {"from": "b", "to": "c", "label": "oui"}, {"from": "c", "to": "a", "dash": True}], "gap_x": 20, "gap_y": 10, "node_h": 40}
    ops, height = _render("flowchart", props, w=220)
    nodes = _of(ops, "box", "node")
    # « B » and its sub-line at 13 pt need 43.1 pt: every row grows from 40 to 43.5
    assert all(n["h"] == 43.5 for n in nodes)
    assert [n["x"] for n in nodes] == [0, 120, 120] and nodes[2]["y"] == 53.5 and nodes[0]["w"] == 100
    assert nodes[1]["color"] == "on_dark" and nodes[1]["runs"][1][0]["text"] == "s"
    edges = _of(ops, "polyline", "edge")
    assert all(e["end_arrow"] == "arrow" for e in edges)
    assert edges[0]["points"] == [[100, 21.75], [120, 21.75]]  # same row: straight
    assert edges[1]["points"] == [[170, 43.5], [170, 53.5]]  # same column: straight down
    assert edges[2]["points"] == [[170, 97], [170, 109], [50, 109], [50, 43.5]] and edges[2]["dash"] == "DASH"  # lane under the grid, back up into A
    assert _of(ops, "text", "edge_label")[0]["text"] == "oui"
    assert height == 109
    with pytest.raises(ValueError, match="unknown node"):
        components.render("flowchart", {"nodes": [{"id": "a", "label": "A"}], "edges": [["a", "zz"]]}, PERISCOPE, 200)


# --- mockups / extensions ---------------------------------------------------------------

def test_phone_frame_screen_and_notch():
    ops, height = _render("phone", {"image": "screen-demo"}, w=120)
    (frame,) = _of(ops, "box", "frame")
    (img,) = _of(ops, "image")
    assert img["cover"] is True and img["h"] == pytest.approx(img["w"] / 0.4615)
    assert _of(ops, "box", "notch")[0]["fill"] == "device_frame"
    assert height == frame["h"] > 240
    ops, _ = _render("phone", {"screen_text": "App", "notch": False}, w=120)
    assert not _of(ops, "image") and not _of(ops, "box", "notch") and "App" in _texts(ops)


def test_stats_sub_and_card_plain():
    ops, height = _render("stats", {"items": [{"value": "25", "label": "ans", "sub": "d'expertise"}, {"value": "4", "label": "M€"}]})
    assert _of(ops, "text", "sub")[0]["text"] == "d'expertise" and height > 82
    ops, _ = _render("card", {"variant": "plain", "icon": "bolt", "title": "Pôle conseil", "body": "- a"})
    (bg,) = _of(ops, "box", "card")
    assert bg["fill"] is None and bg["line"] is None



def test_every_builtin_has_a_use_sentence_naming_alternatives():
    from gslides_mcp.components.uses import USES
    cat = {c["name"]: c for c in components.catalogue()}
    assert set(USES) == {n for n, c in cat.items() if c["source"] == "builtin"}
    for name, entry in cat.items():
        if entry["source"] != "builtin":
            continue
        use = entry["use"]
        assert len(use) > 40 and "→" in use, name  # says when, and points to a neighbour
        for alt in {w.strip(" ;.,") for w in use.split() if "_" in w and not w.startswith("`")}:  # `prop_names` are not components
            assert alt in cat, (name, alt)  # every named alternative exists


def test_component_sources_declare_charter_sizes():
    """Sizes written in the components (not just the theme clamp) respect the floors, so
    box heights computed from them are right."""
    for entry in components.catalogue():
        ops, _ = components.render(entry["name"], entry["example"]["props"], PERISCOPE, 400)
        for o in ops:
            if o["op"] == "table" or o.get("size") is None:
                continue
            if o.get("small_ok"):
                # under the floor only for chart internals, eyebrows, badges and sources
                assert PERISCOPE.small_ok(o.get("style"), o.get("role")), (entry["name"], o.get("style"), o.get("role"))
                continue
            floor = PERISCOPE.size_floor(o.get("style"))
            assert floor is None or o["size"] >= floor, (entry["name"], o.get("style"), o["size"])
            for para in o.get("runs", []):
                for r in para:
                    assert r.get("size") is None or r["size"] >= (floor or 0), (entry["name"], r)
