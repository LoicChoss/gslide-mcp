"""MCP tools: draw, list_components, insert_component, save_component, delete_component."""

import pytest

from gslides_mcp import components as registry
from gslides_mcp.components import recipes
from gslides_mcp.tools import components as tools

PT = 12700


@pytest.fixture(autouse=True)
def user_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recipes, "USER_COMPONENT_DIR", tmp_path)
    yield tmp_path
    for name in list(registry.names()):
        if registry._REGISTRY[name].source == "recipe":  # no get(): it would re-load the dir
            registry.unregister(name)


def _kinds(batch):
    return [next(iter(r)) for r in batch]


def test_list_components_returns_catalogue_and_themes(fake_slides):
    out = tools.list_components()
    names = {c["name"] for c in out["components"]}
    assert {"kpi", "card", "table", "donut"} <= names
    assert "periscope" in out["themes"] and "default" in out["themes"]
    assert out["default_theme"] == "periscope"
    assert "save_component" in out["how_to_add"]


def test_insert_component_offsets_groups_and_reports(fake_slides):
    out = tools.insert_component("PRES1", "1", "kpi", {"value": "12", "label": "Sessions", "delta": "+3 %"},
                                 x_pt=40, y_pt=60, width_pt=200)
    assert len(fake_slides.batches) == 1
    batch = fake_slides.batches[0]
    bar = next(r["createShape"] for r in batch if "createShape" in r)
    assert bar["elementProperties"]["pageObjectId"] == "slide_1"
    assert bar["elementProperties"]["transform"]["translateX"] == 40 * PT
    assert bar["elementProperties"]["transform"]["translateY"] == 60 * PT
    (grp,) = [r["groupObjects"] for r in batch if "groupObjects" in r]
    assert grp["childrenObjectIds"] == out["element_ids"]
    assert out["group_id"] == grp["groupObjectId"]
    assert out["component"] == "kpi" and out["theme"] == "periscope"
    assert 60 <= out["height_pt"] <= 80 and out["slide_id"] == "slide_1"
    assert out["requests"] == len(batch)


def test_insert_component_theme_and_height(fake_slides):
    out = tools.insert_component("PRES1", "slide_2", "card", {"title": "T", "body": "b"},
                                 x_pt=0, y_pt=0, width_pt=200, height_pt=120, theme="default")
    assert out["height_pt"] == 120 and out["theme"] == "default"


def test_insert_component_fails_before_any_write(fake_slides):
    with pytest.raises(ValueError, match="'nope'"):
        tools.insert_component("PRES1", "1", "nope", {}, x_pt=0, y_pt=0, width_pt=100)
    with pytest.raises(ValueError, match="required"):
        tools.insert_component("PRES1", "1", "kpi", {"label": "x"}, x_pt=0, y_pt=0, width_pt=100)
    with pytest.raises(ValueError, match="theme"):
        tools.insert_component("PRES1", "1", "kpi", {"value": "1", "label": "x"}, x_pt=0, y_pt=0, width_pt=100, theme="nope")
    assert fake_slides.batches == []


def test_draw_ops_grouped_with_hint(fake_slides):
    ops = [{"op": "box", "x": 0, "y": 0, "w": 50, "h": 20, "fill": "accent"},
           {"op": "line", "x1": 0, "y1": 25, "x2": 50, "y2": 25, "color": "ink"}]
    out = tools.draw("PRES1", "1", ops, x_pt=10, y_pt=10)
    batch = fake_slides.batches[0]
    assert "groupObjects" in _kinds(batch)
    assert len(out["element_ids"]) == 2 and out["group_id"]
    assert "save_component" in out["hint"]
    tools.draw("PRES1", "1", ops[:1], group=False)
    assert "groupObjects" not in _kinds(fake_slides.batches[1])


def test_draw_rejects_bad_ops_before_writing(fake_slides):
    with pytest.raises(ValueError, match="'blob'"):
        tools.draw("PRES1", "1", [{"op": "blob"}])
    assert fake_slides.batches == []


def test_save_then_insert_a_recipe(fake_slides, user_dir):
    recipe = {"name": "rule", "description": "Un filet.", "props": {"weight": {"type": "number", "description": "épaisseur", "default": 1}},
              "height": "weight", "ops": [{"op": "line", "x1": 0, "y1": 0, "x2": "w", "y2": 0, "color": "rule", "weight": "weight"}]}
    out = tools.save_component(recipe)
    assert out["saved"].endswith("rule.json") and out["component"]["source"] == "recipe"
    assert "rule" in {c["name"] for c in tools.list_components()["components"]}
    ins = tools.insert_component("PRES1", "1", "rule", {"weight": 2}, x_pt=0, y_pt=100, width_pt=300)
    assert ins["height_pt"] == 2 and len(ins["element_ids"]) == 1
    assert tools.delete_component("rule") == {"deleted": "rule"}
    assert "rule" not in registry.names()


def test_save_component_rejects_invalid_recipe(fake_slides):
    with pytest.raises(ValueError, match="built-in"):
        tools.save_component({"name": "kpi", "description": "x", "ops": []})
