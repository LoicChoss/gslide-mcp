"""Themes: one place for palette, roles, font and named text styles."""

import json

import pytest

from gslides_mcp import themes
from gslides_mcp.themes import Theme


def test_color_accepts_hex_token_role_and_rgb_dict():
    t = Theme(name="t", colors={"mint": "#00F6B5"}, roles={"accent": "mint"})
    assert t.color("#FF0000") == {"red": 1, "green": 0, "blue": 0}
    assert t.color("mint")["green"] == pytest.approx(0.965, abs=0.01)
    assert t.color("accent") == t.color("mint")
    assert t.color({"red": 0.5, "green": 0.5, "blue": 0.5}) == {"red": 0.5, "green": 0.5, "blue": 0.5}
    with pytest.raises(ValueError, match="'teal'"):
        t.color("teal")


def test_text_style_merges_named_style_with_overrides():
    t = Theme(name="t", colors={"navy": "#002B3C"}, roles={"ink": "navy"}, font="Barlow",
              text_styles={"label": {"size": 10.5, "color": "ink"}, "kpi_value": {"size": 28, "bold": True, "color": "ink"}})
    s = t.text_style("kpi_value")
    assert s == {"size": 28, "bold": True, "color": "ink", "font": "Barlow"}
    assert t.text_style("label", size=9)["size"] == 9
    assert t.text_style(None)["font"] == "Barlow"
    with pytest.raises(ValueError, match="'nope'"):
        t.text_style("nope")


def test_periscope_theme_ships_with_roles_and_styles():
    t = themes.load("periscope")
    assert t.font == "Barlow"
    for role in ("accent", "ink", "muted", "surface", "surface_dark", "positive", "negative", "background"):
        assert role in t.roles, role
    for style in ("title", "body", "label", "caption", "kpi_value", "kpi_label", "card_big", "table_header", "table_cell"):
        assert style in t.text_styles, style
    assert t.color("accent")["green"] == pytest.approx(0.965, abs=0.01)   # #00F6B5
    assert t.color("ink")["blue"] == pytest.approx(0.235, abs=0.01)       # #002B3C


def test_default_theme_is_neutral():
    t = themes.load("default")
    assert t.font == "Arial"
    assert t.color("accent") != t.color("ink")


def test_user_theme_dir_overrides_and_extends(tmp_path, monkeypatch):
    monkeypatch.setattr(themes, "USER_THEME_DIR", tmp_path)
    (tmp_path / "acme.json").write_text(json.dumps({
        "extends": "periscope",
        "colors": {"acme_red": "#AA0000"},
        "roles": {"accent": "acme_red"},
        "text_styles": {"label": {"size": 12}},
    }), encoding="utf-8")
    t = themes.load("acme")
    assert t.color("accent") == {"red": pytest.approx(0.667, abs=0.01), "green": 0, "blue": 0}
    assert t.color("ink")["blue"] == pytest.approx(0.235, abs=0.01)  # inherited
    assert t.text_style("label")["size"] == 12
    assert t.text_style("label")["color"] == "text"  # merged, not replaced
    assert "acme" in themes.available() and "periscope" in themes.available()


def test_unknown_theme_lists_available():
    with pytest.raises(ValueError, match="periscope"):
        themes.load("nope")


def test_text_rules_floor_sizes_except_tables():
    t = themes.load("periscope")
    assert t.text_style("body", size=8)["size"] == 11        # body text never under 11 pt
    assert t.text_style("caption", size=7)["size"] == 10     # labels never under 10 pt
    assert t.text_style("table_cell", size=9)["size"] == 9   # tables keep their charter size
    assert t.text_style(None, size=8)["size"] == 11
    assert t.text_style("kpi_value")["size"] == 28           # nothing shrinks
    for name, st in t.text_styles.items():
        floor = t.size_floor(name)
        assert floor is None or st["size"] >= floor, name
    bare = themes.Theme(name="bare", font="Arial")
    assert bare.size_floor("body") is None and bare.text_style("x" if False else None, size=6)["size"] == 6


def test_regie_roles_resolve_in_every_theme():
    for name in ("periscope", "default"):
        t = themes.load(name)
        for role in ("regie_google", "regie_bing", "regie_meta", "regie_facebook", "regie_instagram",
                     "regie_pinterest", "regie_linkedin", "regie_tiktok", "regie_ga4", "chart_grid", "chart_axis"):
            assert role in t.roles, (name, role)
            t.color(role)
    p = themes.load("periscope")
    assert p.color("regie_google") == p.color("#00E5C3")
    assert p.color("regie_facebook") == p.color("regie_meta") == p.color("#FA00A6")


def test_tint_mixes_with_white_and_is_dark_reads_luminance():
    t = themes.load("periscope")
    assert t.tint("#000000", 0.5) == "#808080"
    assert t.tint("regie_meta", 0) == "#FA00A6"
    lighter = t.tint("regie_meta", 0.55)
    assert lighter.startswith("#") and len(lighter) == 7 and lighter != "#FA00A6"
    assert t.color(lighter)["green"] > t.color("regie_meta")["green"]
    assert t.is_dark("navy") and t.is_dark("#000000")
    assert not t.is_dark("mint") and not t.is_dark("#FFFFFF")
    assert t.is_dark("surface_dark") and not t.is_dark("acid")
