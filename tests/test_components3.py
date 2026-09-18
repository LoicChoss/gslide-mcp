"""Lot 3 mockups: serp (Google result), browser frame, laptop frame."""

import pytest

from gslides_mcp import components, draw, themes

PERISCOPE = themes.load("periscope")


def _render(name, props, w=400, h=None):
    ops, height = components.render(name, props, PERISCOPE, w, h)
    reqs, ids = draw.ops_to_requests("slide_1", ops, PERISCOPE, prefix="cmp", resolve_asset=lambda n, t: "fid")
    assert reqs and ids
    return ops, height


def _of(ops, kind, role=None):
    return [o for o in ops if o["op"] == kind and (role is None or o.get("role") == role)]


def _texts(ops):
    return [o.get("text") or o.get("markdown") for o in ops if o.get("text") or o.get("markdown")]


def test_lot3_components_are_listed_and_examples_render():
    cat = {c["name"] for c in components.catalogue()}
    assert {"serp", "browser", "laptop"} <= cat
    for name in ("serp", "browser", "laptop"):
        entry = next(c for c in components.catalogue() if c["name"] == name)
        _render(name, entry["example"]["props"])


# --- serp -------------------------------------------------------------------------

def test_serp_mimics_google_colours_with_stars_and_frame():
    ops, height = _render("serp", {"site": "La Belle Adresse", "url": "labelleadresse.com › astuces",
                                   "title": "Comment détacher un vêtement blanc ?", "rating": 4.6, "reviews": "1 024 avis",
                                   "desc": "Nos astuces de grand-mère pour raviver le blanc."})
    frame = _of(ops, "box", "frame")[0]
    assert frame["shape"] == "ROUND_RECTANGLE" and frame["fill"] == "#FFFFFF" and frame["line"]["color"] == "#DADCE0"
    chip = _of(ops, "box", "favicon")[0]
    assert chip["shape"] == "ELLIPSE" and chip["text"] == "L"
    title = next(o for o in ops if o.get("role") == "title")
    assert title["color"] == "#1A0DAB" and title["text"].startswith("Comment")
    stars = [o for o in ops if o["op"] == "box" and o.get("shape") == "STAR_5"]
    assert len(stars) == 5 + 5  # 5 empty + 5 gold (the 5th partially masked)
    assert [s["fill"] for s in stars[:5]] == ["#DADCE0"] * 5
    masks = _of(ops, "box", "star_mask")
    assert len(masks) == 1 and masks[0]["fill"] == "#FFFFFF" and masks[0]["w"] == pytest.approx(11 * 0.4, abs=0.5)
    assert "4,6/5 · 1 024 avis" in _texts(ops)
    assert any("grand-mère" in t for t in _texts(ops))
    assert height == frame["h"] > 100


def test_serp_without_frame_rating_or_site():
    ops, _ = _render("serp", {"title": "Titre seul", "frame": False})
    assert not _of(ops, "box", "frame")
    assert not [o for o in ops if o.get("shape") == "STAR_5"]
    assert _of(ops, "box", "favicon")[0]["text"] == "?"


# --- browser / laptop -------------------------------------------------------------------

def test_browser_frame_with_screenshot_asset():
    ops, height = _render("browser", {"url": "periscope.digital", "image": "laptop-demo"}, w=300)
    frame = _of(ops, "box", "frame")[0]
    assert frame["shape"] == "ROUND_RECTANGLE" and frame["line"]["color"] == "rule"
    dots = [o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE"]
    assert [d["fill"] for d in dots] == ["ink", "accent", "accent_alt"]
    assert "periscope.digital" in _texts(ops)
    (img,) = _of(ops, "image")
    assert img["asset"] == "laptop-demo" and "tint" not in img
    assert img["w"] == pytest.approx(300 - 2 * 2.2) and img["h"] == pytest.approx(img["w"] / 1.6)
    assert height == frame["h"] == pytest.approx(img["y"] + img["h"] + 2.2)


def test_browser_without_image_shows_a_screen_colour_and_text():
    ops, _ = _render("browser", {"screen": "surface_dark", "screen_text": "Zone de démo"}, w=300, h=200)
    assert not _of(ops, "image")
    screen = _of(ops, "box", "screen")[0]
    assert screen["fill"] == "surface_dark"
    assert "Zone de démo" in _texts(ops)


def test_laptop_frame_screen_and_base():
    ops, height = _render("laptop", {"image": "laptop-demo"}, w=430)
    frame = _of(ops, "box", "frame")[0]
    assert frame["fill"] == "device_frame" and frame["shape"] == "ROUND_RECTANGLE"
    (img,) = _of(ops, "image")
    assert 0 < img["x"] < 12 and img["w"] == pytest.approx(430 - 2 * img["x"])
    base = _of(ops, "box", "base")[0]
    assert base["fill"] == "device_base" and base["x"] < 0 and base["w"] > 430
    assert height == pytest.approx(base["y"] + base["h"])
    ops, _ = _render("laptop", {"screen_text": "Dashboard"}, w=300)
    assert not _of(ops, "image") and "Dashboard" in _texts(ops)
