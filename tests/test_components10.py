"""Training diagrams: cocon, cycle, formula, persona_card; checklist groups; tree third level."""

import pytest

from gslides_mcp import components, themes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=600, h=None):
    return components.render(name, props, PERISCOPE, w, h)


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


@pytest.mark.parametrize("name", ["cocon", "cycle", "formula", "persona_card"])
def test_new_components_render_their_example_and_have_a_use(name):
    entry = next(e for e in components.catalogue() if e["name"] == name)
    ops, h = _render(name, entry["example"]["props"], w=660)
    assert ops and h > 0 and entry["use"]
    for v in entry.get("variants", []):
        assert _render(name, v["props"], w=660)[1] > 0


def test_cocon_arc_puts_pages_left_actions_right_and_scales_into_the_box():
    ops, h = _render("cocon", {"center": "Aide alimentaire", "pages": ["A", "B", "C"], "actions": ["Nos actions"]}, w=500)
    (center,) = _of(ops, "box", "center")
    pages, actions = _of(ops, "box", "page"), _of(ops, "box", "action")
    assert len(pages) == 3 and len(actions) == 1 and len(_of(ops, "line", "link")) == 4
    cx = center["x"] + center["w"] / 2
    assert all(pg["x"] + pg["w"] / 2 < cx for pg in pages) and actions[0]["x"] + actions[0]["w"] / 2 > cx
    assert center["fill"] == "cyan" and pages[0]["fill"] == "accent" and actions[0]["fill"] == "ink" and actions[0]["color"] == "on_dark"
    assert min(o["x"] for o in pages + actions + [center]) >= -0.5 and max(o["x"] + o["w"] for o in pages + actions + [center]) <= 500.5
    assert min(o["y"] for o in pages + actions + [center]) >= -0.5 and max(o["y"] + o["h"] for o in pages + actions + [center]) <= h + 0.5
    ring, _ = _render("cocon", {"center": "X", "pages": ["A", "B", "C", "D"], "actions": ["E"], "layout": "ring"}, w=600)
    assert len(_of(ring, "box", "page")) == 4
    ops, h = _render("cocon", {"center": "X", "pages": ["A", "B"]}, w=300, h=220)
    assert h == 220 and max(o["x"] + o["w"] for o in _of(ops, "box")) <= 300.5


def test_cycle_four_steps_make_a_square_with_clockwise_arrows():
    steps = [{"title": f"Étape {i}", "text": "détail"} for i in range(1, 5)]
    ops, h = _render("cycle", {"steps": steps}, w=600)
    boxes = _of(ops, "box", "step")
    arrows = _of(ops, "line", "arrow")
    assert len(boxes) == 4 and len(arrows) == 4 and all(a["end_arrow"] == "arrow" for a in arrows)
    assert boxes[0]["y"] == boxes[1]["y"] and boxes[2]["y"] == boxes[3]["y"] and boxes[0]["x"] == boxes[3]["x"]
    assert boxes[1]["x"] > boxes[0]["x"] and boxes[2]["y"] > boxes[1]["y"]
    # arrows stop at the box edges: the first arrow runs left → right between the two top boxes
    a = arrows[0]
    assert a["x1"] >= boxes[0]["x"] + boxes[0]["w"] - 4 and a["x2"] <= boxes[1]["x"] + 4
    ring, h = _render("cycle", {"steps": steps[:3]}, w=600)
    assert len(_of(ring, "box", "step")) == 3 and len(_of(ring, "line", "arrow")) == 3


def test_formula_lays_out_operands_operators_and_the_result():
    ops, h = _render("formula", {"items": [{"title": "A", "text": "a"}, {"title": "B"}, {"title": "C"}, {"title": "D"}, {"title": "E"}],
                                 "result": {"title": "R", "text": "r"}, "operator": "×"}, w=660)
    assert len(_of(ops, "box", "head")) == 5 and [o["text"] for o in _of(ops, "text", "operator")] == ["×"] * 4
    assert [o["text"] for o in _of(ops, "box", "num")] == ["1", "2", "3", "4", "5"]
    (res,) = _of(ops, "box", "result_head")
    assert res["fill"] == "ink" and res["color"] == "on_dark" and _of(ops, "text", "equals")
    assert res["y"] > max(o["y"] + o["h"] for o in _of(ops, "box", "head")) and h > res["y"] + res["h"]
    heads = _of(ops, "box", "head")
    assert all(abs(hd["w"] - heads[0]["w"]) < 0.01 for hd in heads) and heads[-1]["x"] + heads[-1]["w"] <= 660.01


def test_persona_card_sections_and_initials_without_photo():
    props = {"name": "Camille Dupont", "age": "34 ans", "location": "Lyon", "context": "Contexte.", "gauges": [{"label": "Priorité", "value": 0.8}],
             "devices": ["Mobile", {"label": "Tablette", "on": False}], "expectations": ["A"], "brakes": ["B"], "tag": "Et le Search ?"}
    ops, h = _render("persona_card", props, w=520)
    assert _of(ops, "box", "card")[0]["shape"] == "ROUND_RECTANGLE" and _of(ops, "box", "card")[0]["h"] == h
    assert _of(ops, "box", "photo")[0]["text"] == "CD"
    assert _of(ops, "text", "name")[0]["text"] == "Camille Dupont – 34 ans"
    (gauge,) = _of(ops, "box", "gauge")
    (track,) = _of(ops, "box", "gauge_track")
    assert abs(gauge["w"] - 0.8 * track["w"]) < 0.01
    devices = _of(ops, "box", "device")
    assert [d["fill"] for d in devices] == ["cyan", "surface"] and devices[0]["text"] == "Mobile"
    (tag,) = _of(ops, "box", "tag")
    # set in the card's corner, as far from its right edge as from its bottom (clear of the curve: test_components11)
    assert len(_of(ops, "text", "list")) == 2 and tag["shape"] == "ROUND_RECTANGLE"
    assert h - tag["y"] - tag["h"] == pytest.approx(520 - tag["x"] - tag["w"]) and 520 - tag["x"] - tag["w"] >= 12
    ops, _ = _render("persona_card", {"name": "Léa", "photo": "screen-demo"}, w=400)
    assert _of(ops, "image", "photo")[0]["asset"] == "screen-demo"


def test_checklist_groups_in_two_columns_and_plain_items_unchanged():
    groups = [{"title": f"Section {i}", "items": ["a", {"text": "b", "done": True}]} for i in range(1, 5)]
    ops, h = _render("checklist", {"groups": groups, "cols": 2}, w=600)
    nums = _of(ops, "box", "group_num")
    assert [n["text"] for n in nums] == ["1", "2", "3", "4"] and nums[0]["x"] == nums[1]["x"] and nums[2]["x"] > nums[0]["x"]
    assert len(_of(ops, "box", "check")) == 8 and all(c["w"] == 11 for c in _of(ops, "box", "check"))
    assert len([o for o in ops if o["op"] == "polyline"]) == 4
    plain, _ = _render("checklist", {"items": ["x", {"text": "y", "done": True}]}, w=300)
    assert all(c["w"] == 15 for c in _of(plain, "box", "check")) and not _of(plain, "box", "group_num")
    with pytest.raises(ValueError):
        components.render("checklist", {"groups": groups, "cols": "two"}, PERISCOPE, 300)


def test_tree_third_level_stacks_leaf_boxes_under_each_child():
    props = {"root": "Univers", "children": [{"label": "A", "children": ["a1", "a2"]}, {"label": "B", "children": ["b1"]},
                                             {"label": "C", "items": ["c1"]}, {"label": "D"}, {"label": "E"}]}
    ops, h = _render("tree", props, w=660)
    leaves = _of(ops, "box", "leaf")
    children = _of(ops, "box", "child")
    assert len(children) == 5 and len(leaves) == 3 and _of(ops, "text", "items")
    a = children[0]
    assert leaves[0]["x"] == a["x"] and leaves[0]["y"] > a["y"] + a["h"] and leaves[1]["y"] > leaves[0]["y"] + leaves[0]["h"]
    assert leaves[0]["fill"] == "surface" and h >= leaves[1]["y"] + leaves[1]["h"]


def test_cocon_explicit_angles_white_text_and_half_page_default():
    props = {"center": "X", "pages": ["A", "B", "C"], "actions": ["D"], "page_angles": [112, 168, 214], "action_angles": [-35], "text_color": "background"}
    ops, h = _render("cocon", props, w=420)
    pages = _of(ops, "box", "page")
    (center,) = _of(ops, "box", "center")
    cx, cy = center["x"] + center["w"] / 2, center["y"] + center["h"] / 2
    assert pages[0]["y"] + pages[0]["h"] / 2 < cy and pages[0]["x"] + pages[0]["w"] / 2 < cx        # 112°: up and left
    assert pages[2]["y"] + pages[2]["h"] / 2 > cy                                                 # 214°: below
    assert all(pg["color"] == "background" for pg in pages) and center["color"] == "background"
    # the default example fits on half a slide
    entry = next(e for e in components.catalogue() if e["name"] == "cocon")
    ops, h = _render("cocon", entry["example"]["props"], w=420)
    assert h <= 360 and max(o["x"] + o["w"] for o in _of(ops, "box")) <= 420.5


def test_cocon_disc_text_shrinks_so_no_word_breaks():
    from gslides_mcp.components.training import _disc_size
    assert _disc_size("Pourquoi donner", 70) < 9            # « Pourquoi » must fit 35 pt of usable width
    assert _disc_size("Don", 70) == 10
    ops, _ = _render("cocon", {"center": "Cataracte", "pages": ["Réglementation"], "page_d": 84, "center_d": 76}, w=400)
    assert all(o["size"] <= 10 and o.get("small_ok") == (o["size"] < 10) for o in _of(ops, "box") if o.get("text"))
