"""User recipes: JSON components with templated ops, saved under ~/.gslides-mcp/components."""

import json

import pytest

from gslides_mcp import components, themes
from gslides_mcp.components import recipes

PERISCOPE = themes.load("periscope")

PILL_ROW = {
    "name": "pill_row",
    "description": "Rangée de pastilles espacées.",
    "props": {
        "items": {"type": "list", "description": "Textes des pastilles.", "required": True},
        "fill": {"type": "color", "description": "Fond.", "default": "accent"},
        "gap": {"type": "number", "description": "Espace entre pastilles.", "default": 6},
    },
    "height": "16",
    "ops": [
        {"each": "items", "ops": [
            {"op": "box", "x": "i * (64 + gap)", "y": 0, "w": 64, "h": 16, "fill": "{fill}",
             "text": "{item}", "style": "badge", "align": "CENTER", "valign": "MIDDLE"},
        ]},
        {"op": "text", "x": 0, "y": "16 + 4", "w": "w", "h": 12, "text": "{len(items)} pastilles", "style": "caption"},
    ],
}


@pytest.fixture(autouse=True)
def user_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recipes, "USER_COMPONENT_DIR", tmp_path)
    yield tmp_path
    for name in list(components.names()):
        if components._REGISTRY[name].source == "recipe":  # no get(): it would re-load the dir
            components.unregister(name)


def test_parse_renders_each_blocks_and_expressions():
    comp = recipes.parse(PILL_ROW)
    assert comp.source == "recipe" and comp.name == "pill_row"
    ops, height = comp.render(components.validate(comp, {"items": ["A", "B", "C"]}), PERISCOPE, 300, None)
    boxes = [o for o in ops if o["op"] == "box"]
    assert [b["x"] for b in boxes] == [0, 70, 140]
    assert [b["text"] for b in boxes] == ["A", "B", "C"]
    assert all(b["fill"] == "accent" for b in boxes)
    caption = [o for o in ops if o["op"] == "text"][0]
    assert caption == {"op": "text", "x": 0, "y": 20, "w": 300, "h": 12, "text": "3 pastilles", "style": "caption"}
    assert height == 16


def test_item_fields_and_prop_overrides():
    recipe = dict(PILL_ROW, ops=[{"each": "items", "as": "row", "ops": [
        {"op": "text", "x": 0, "y": "i * 20", "w": "w / 2", "h": 18, "text": "{row.name} : {row.value}"}]}])
    comp = recipes.parse(recipe)
    ops, _ = comp.render(components.validate(comp, {"items": [{"name": "CTR", "value": "3 %"}], "gap": 10}), PERISCOPE, 200, None)
    assert ops[0]["text"] == "CTR : 3 %" and ops[0]["w"] == 100


def test_parse_rejects_bad_recipes():
    with pytest.raises(ValueError, match="name"):
        recipes.parse({"description": "x", "ops": []})
    with pytest.raises(ValueError, match="'kpi'.*built-in"):
        recipes.parse(dict(PILL_ROW, name="kpi"))
    with pytest.raises(ValueError, match="ops\\[1\\].*'blob'"):
        recipes.parse(dict(PILL_ROW, ops=[{"op": "box", "x": 0, "y": 0, "w": 1, "h": 1}, {"op": "blob"}]))
    with pytest.raises(ValueError, match="ops\\[0\\].*undefined"):
        recipes.parse(dict(PILL_ROW, ops=[{"op": "box", "x": "nope * 2", "y": 0, "w": 1, "h": 1}]))
    with pytest.raises(ValueError, match="import"):
        recipes.parse(dict(PILL_ROW, ops=[{"op": "box", "x": "__import__('os').getcwd()", "y": 0, "w": 1, "h": 1}]))


def test_save_registers_and_persists(user_dir):
    path = recipes.save(PILL_ROW)
    assert path == user_dir / "pill_row.json"
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "pill_row"
    entry = next(c for c in components.catalogue() if c["name"] == "pill_row")
    assert entry["source"] == "recipe" and entry["use"] == ""
    assert {p["name"] for p in entry["props"]} == {"items", "fill", "gap"}
    recipes.save({**PILL_ROW, "name": "pill_row2", "use": "Rangée de leviers ; un seul → pill."})
    assert next(c for c in components.catalogue() if c["name"] == "pill_row2")["use"].startswith("Rangée")
    ops, _ = components.render("pill_row", {"items": ["x"]}, PERISCOPE, 100)
    assert ops


def test_user_recipes_are_loaded_on_demand(user_dir):
    (user_dir / "pill_row.json").write_text(json.dumps(PILL_ROW), encoding="utf-8")
    assert "pill_row" not in components.names()
    assert components.get("pill_row").source == "recipe"


def test_delete_unregisters_and_removes_file(user_dir):
    recipes.save(PILL_ROW)
    recipes.delete("pill_row")
    assert not (user_dir / "pill_row.json").exists()
    assert "pill_row" not in components.names()
    with pytest.raises(ValueError, match="built-in"):
        recipes.delete("kpi")


def test_delete_refuses_a_name_that_is_a_path():
    import pytest
    from gslides_mcp.components import recipes

    with pytest.raises(ValueError, match="invalid component name"):
        recipes.delete("../../fastmcp/session")


def test_expressions_cannot_stall_the_shared_server():
    import pytest
    from gslides_mcp.components import recipes

    assert recipes.evaluate("2 ** 10", {}) == 1024
    assert recipes.evaluate("len(items) * 26", {"items": [1, 2]}) == 52
    with pytest.raises(ValueError, match="exponent too large"):
        recipes.evaluate("9 ** 9 ** 9", {})
    with pytest.raises(ValueError, match="repetition too large"):
        recipes.evaluate("'a' * 10 ** 9", {})
