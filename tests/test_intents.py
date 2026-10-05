"""Slide intentions: the catalogue index by intention, details on demand, suggestions for a new deck."""

import json

import pytest

from gslides_mcp import components as registry
from gslides_mcp.components import intents, recipes
from gslides_mcp.tools import components as tools
from gslides_mcp.tools import harvest


@pytest.fixture(autouse=True)
def user_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recipes, "USER_COMPONENT_DIR", tmp_path)
    yield tmp_path
    for name in list(registry.names()):
        if registry._REGISTRY[name].source == "recipe":
            registry.unregister(name)


def _suggest(description, **kw):
    return harvest.suggest_components(description=description, **kw)


def _candidates(out, key):
    (group,) = [g for g in out["intents"] if g["intent"] == key]
    return [c["component"] for c in group["candidates"]]


# --- the table of intentions ----------------------------------------------------------

def test_every_component_serves_an_intention():
    listed = {n for i in intents.INTENTS for n in i.components}
    assert sorted(set(registry.names()) - listed) == []


def test_intentions_name_real_components():
    for i in intents.INTENTS:
        assert set(i.components) <= set(registry.names()), i.key
        assert len(set(i.components)) == len(i.components), i.key
    assert intents.USUAL <= set(registry.names())


def test_a_recipe_says_its_intentions_or_lands_in_others():
    op = {"op": "box", "x": 0, "y": 0, "w": "w", "h": 20, "fill": "accent"}
    recipes.save({"name": "versus_strip", "use": "Deux options face à face.", "intents": ["comparer"], "ops": [op]})
    recipes.save({"name": "rule_line", "use": "Un filet.", "ops": [op]})
    groups = {g["key"]: g["components"] for g in tools.list_components()["intents"]}
    assert "versus_strip" in groups["comparer"] and groups[intents.OTHER] == ["rule_line"]


def test_a_recipe_with_an_unknown_intention_is_refused():
    with pytest.raises(ValueError, match="intention"):
        recipes.parse({"name": "odd_one", "intents": ["nope"], "ops": [{"op": "box", "x": 0, "y": 0, "w": 10, "h": 10}]})


# --- list_components: index, then details ---------------------------------------------

def test_the_index_shows_the_whole_catalogue_by_intention(fake_slides):
    out = tools.list_components()
    assert [g["key"] for g in out["intents"]][:3] == ["chiffres", "comparer", "repartition"]
    assert set(out["components"]) == set(registry.names())
    card = out["components"]["card"]
    assert card["use"] and card["variants"] and all(isinstance(t, str) for t in card["variants"])
    assert "props" not in card and "example" not in card
    assert "periscope" in out["themes"] and out["default_theme"] == "periscope"


def test_the_index_stays_small(fake_slides):
    out = tools.list_components()
    out.pop("assets", None)
    out.pop("assets_error", None)
    assert len(json.dumps(out, ensure_ascii=False)) < 32_000


def test_details_for_the_chosen_components(fake_slides):
    out = tools.list_components(names=["mini_charts", "formula"])
    assert [c["name"] for c in out["components"]] == ["mini_charts", "formula"]
    mini = out["components"][0]
    assert mini["props"] and mini["example"]["props"] and "comparer" in mini["intents"]


def test_details_of_an_unknown_component_name_the_close_ones(fake_slides):
    with pytest.raises(ValueError, match="kpi_grid"):
        tools.list_components(names=["kpi_grids"])


# --- suggest_components(description=…) ------------------------------------------------

def test_a_split_of_a_total_suggests_shares():
    out = _suggest("Répartition du budget média par levier (Google, Meta, Bing)")
    assert out["intents"][0]["intent"] == "repartition"
    assert {"donut", "pie", "donut_row"} & set(_candidates(out, "repartition")[:3])
    first = out["intents"][0]["candidates"][0]
    assert first["use"] and "variants" in first


def test_findings_and_recommendations():
    out = _suggest("3 constats sur le trafic organique et une recommandation à retenir")
    keys = [g["intent"] for g in out["intents"]]
    assert keys[0] == "messages"
    assert "takeaways" in _candidates(out, "messages")


def test_comparing_actors_on_several_indicators():
    out = _suggest("Comparer Google et Bing sur 4 KPI : clics, impressions, CTR, position")
    assert "comparer" in [g["intent"] for g in out["intents"]]
    assert "mini_charts" in _candidates(out, "comparer")


def test_a_component_keyword_pulls_its_intention():
    out = _suggest("Fiche persona de Manon, porteuse de projets")
    assert _candidates(out, "personnes")[:2] == ["persona_sheet", "persona_card"]


def test_there_is_always_a_less_obvious_pick_when_something_matched():
    for text in ("Répartition du budget par levier", "3 constats et une reco", "Évolution des sessions mois par mois",
                 "Les étapes de la mission", "Résultats de la campagne : 12 400 clics, 3,2 % de CTR"):
        out = _suggest(text)
        pick = out["less_obvious"]
        assert pick and pick["component"] not in intents.USUAL, text
        assert all(pick["component"] != g["candidates"][0]["component"] for g in out["intents"]), text
        assert pick["use"] and pick["intent"]


def test_avoid_sends_planned_components_to_the_end():
    out = _suggest("Répartition du budget par levier", avoid=["donut", "pie"], top=20)
    names = _candidates(out, "repartition")
    assert names[-2:] == ["donut", "pie"]
    (group,) = [g for g in out["intents"] if g["intent"] == "repartition"]
    assert [c["component"] for c in group["candidates"] if c.get("avoid")] == ["donut", "pie"]
    assert out["less_obvious"]["component"] not in ("donut", "pie")


def test_nothing_recognised_returns_the_intentions_to_choose_from():
    out = _suggest("zzz")
    assert out["intents"] == [] and out["less_obvious"] is None
    assert [i["key"] for i in out["all_intents"]] == [i.key for i in intents.INTENTS]


def test_one_mode_at_a_time():
    with pytest.raises(ValueError, match="either"):
        harvest.suggest_components("PRES1", "3", description="x")
    with pytest.raises(ValueError, match="either"):
        harvest.suggest_components()
