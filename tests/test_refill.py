"""refill_text keeps each target's style; replace_text(elements=…, dry_run=…); transform_element per axis."""

import pytest

from gslides_mcp.tools import content, refill
from gslides_mcp.tools.layout import transform_element

GREEN = {"opaqueColor": {"rgbColor": {"red": 0.1, "green": 0.6, "blue": 0.3}}}
RED = {"opaqueColor": {"rgbColor": {"red": 0.8, "green": 0.1, "blue": 0.1}}}
BARLOW = {"weightedFontFamily": {"fontFamily": "Barlow", "weight": 600}, "fontFamily": "Barlow",
          "fontSize": {"magnitude": 9, "unit": "PT"}, "bold": True}


def _text(content, style=None, align=None):
    if content is None:
        return {"textElements": [{"paragraphMarker": {"style": {"alignment": align} if align else {}}}]}
    marker = {"paragraphMarker": {"style": {"alignment": align} if align else {}}}
    return {"textElements": [marker, {"textRun": {"content": content + "\n", "style": style or {}}}]}


def _table(oid, rows):
    """rows: [[(content, style) | None, …], …]"""
    return {"objectId": oid, "table": {
        "rows": len(rows), "columns": len(rows[0]),
        "tableRows": [{"tableCells": [
            {"location": {"rowIndex": i, "columnIndex": j},
             **({"text": _text(c[0], c[1], "END")} if c else {"text": _text(None)})}
            for j, c in enumerate(row)]} for i, row in enumerate(rows)],
    }}


def _shape(oid, content, style=None):
    return {"objectId": oid, "shape": {"shapeType": "TEXT_BOX", "text": _text(content, style)}}


@pytest.fixture
def deck(fake_slides, pres):
    pres["slides"][2]["pageElements"] = [
        _table("tbl_b", [
            [("Régie", BARLOW), ("Dépenses", BARLOW), ("vs N-1", BARLOW)],
            [("Google", {}), ("46 811 €", {"fontSize": {"magnitude": 9, "unit": "PT"}}), ("+52 %", {**BARLOW, "foregroundColor": GREEN})],
            [("Meta", {}), ("12 000 €", {"fontSize": {"magnitude": 9, "unit": "PT"}}), ("-8 %", {**BARLOW, "foregroundColor": RED})],
            [("Bing", {}), None, None],
        ]),
        _shape("kpi_val", "12 400", {"fontSize": {"magnitude": 28, "unit": "PT"}, "bold": True}),
        _shape("kpi_delta", "+4 %", {"foregroundColor": GREEN}),
        _shape("analysis", "Le nouveau levier a porté la collecte : nouveau levier confirmé.", {"italic": True}),
        _shape("label", "Nouveau levier", {"bold": True}),
    ]
    return fake_slides


def _by_kind(batch, kind):
    return [r[kind] for r in batch if kind in r]


# --- refill_text ------------------------------------------------------------------------------

def test_refill_shape_keeps_its_style_in_one_batch(deck):
    out = refill.refill_text("PRES1", [{"element": "kpi_val", "text": "13 050"}])
    (batch,) = deck.batches
    assert [next(iter(r)) for r in batch] == ["deleteText", "insertText", "updateTextStyle"]
    st = _by_kind(batch, "updateTextStyle")[0]
    assert st["style"] == {"fontSize": {"magnitude": 28, "unit": "PT"}, "bold": True}
    assert set(st["fields"].split(",")) == {"fontSize", "bold"}  # never "*": nothing else is reset
    assert out["edits"] == [{"element": "kpi_val", "style_from": "self"}]


def test_refill_cell_keeps_weighted_family_without_plain_family(deck):
    refill.refill_text("PRES1", [{"element": "tbl_b", "row": 0, "column": 1, "text": "Coût"}])
    st = _by_kind(deck.batches[0], "updateTextStyle")[0]
    assert "fontFamily" not in st["style"] and st["style"]["weightedFontFamily"]["weight"] == 600
    assert st["cellLocation"] == {"rowIndex": 0, "columnIndex": 1}
    para = _by_kind(deck.batches[0], "updateParagraphStyle")[0]
    assert para["style"] == {"alignment": "END"}


def test_refill_delta_cell_flips_to_the_colour_the_table_uses_for_its_sign(deck):
    out = refill.refill_text("PRES1", [
        {"element": "tbl_b", "row": 1, "column": 2, "text": "-3,1 %"},
        {"element": "tbl_b", "row": 2, "column": 2, "text": "+12 %"},
    ])
    styles = _by_kind(deck.batches[0], "updateTextStyle")
    assert styles[0]["style"]["foregroundColor"] == RED and styles[1]["style"]["foregroundColor"] == GREEN
    assert styles[0]["style"]["bold"] is True  # the rest of the style stays
    assert [e["delta"] for e in out["edits"]] == ["down", "up"]
    assert out["colors"]["source"] == "table"


def test_refill_empty_cell_borrows_column_style_and_delta_colour(deck):
    out = refill.refill_text("PRES1", [
        {"element": "tbl_b", "row": 3, "column": 2, "text": "+1 %"},
        {"element": "tbl_b", "row": 3, "column": 1, "text": "800 €"},
    ])
    batch = deck.batches[0]
    assert "deleteText" not in {next(iter(r)) for r in batch}  # empty cells: a deleteText would fail the batch
    styles = _by_kind(batch, "updateTextStyle")
    assert styles[0]["style"]["foregroundColor"] == GREEN and styles[0]["style"]["bold"] is True
    assert styles[1]["style"] == {"fontSize": {"magnitude": 9, "unit": "PT"}}  # from 12 000 € / 46 811 €, not the header
    assert [e["style_from"] for e in out["edits"]] == ["column", "column"]


def test_refill_inverse_delta_takes_the_good_colour_for_a_minus(deck):
    out = refill.refill_text("PRES1", [{"element": "tbl_b", "row": 2, "column": 2, "text": "-0,12 €", "delta": "inverse"}])
    assert _by_kind(deck.batches[0], "updateTextStyle")[0]["style"]["foregroundColor"] == GREEN
    assert out["edits"][0]["delta"] == "up"


def test_refill_signed_shape_uses_deck_colours_and_plain_shape_is_not_coloured(deck):
    refill.refill_text("PRES1", [{"element": "kpi_delta", "text": "-2 %"}, {"element": "kpi_val", "text": "-2"}])
    styles = _by_kind(deck.batches[0], "updateTextStyle")
    assert styles[0]["style"]["foregroundColor"] == RED  # learnt from the table's « -8 % »
    assert "foregroundColor" not in styles[1]["style"]  # « 12 400 » was not a variation


def test_refill_explicit_colours_and_theme_fallback(deck, pres):
    refill.refill_text("PRES1", [{"element": "kpi_delta", "text": "-2 %"}], down_color="#FF0000")
    rgb = _by_kind(deck.batches[-1], "updateTextStyle")[0]["style"]["foregroundColor"]["opaqueColor"]["rgbColor"]
    assert rgb == {"red": 1.0, "green": 0.0, "blue": 0.0}
    pres["slides"][2]["pageElements"] = [_shape("solo", "+1 %")]  # nothing to learn from
    out = refill.refill_text("PRES1", [{"element": "solo", "text": "-1 %"}])
    assert out["colors"]["source"] == "theme"


def test_refill_leaves_colour_when_deck_shows_both_signs_alike(deck, pres):
    t = pres["slides"][2]["pageElements"][0]["table"]["tableRows"]
    t[2]["tableCells"][2]["text"] = _text("-8 %", {"foregroundColor": GREEN})
    out = refill.refill_text("PRES1", [{"element": "tbl_b", "row": 1, "column": 2, "text": "-1 %"}])
    assert _by_kind(deck.batches[0], "updateTextStyle")[0]["style"]["foregroundColor"] == GREEN
    assert out["edits"][0]["delta"] == "kept"


def test_refill_empty_text_only_clears(deck):
    refill.refill_text("PRES1", [{"element": "kpi_val", "text": ""}])
    assert [next(iter(r)) for r in deck.batches[0]] == ["deleteText"]


@pytest.mark.parametrize("edit, match", [
    ({"element": "nope", "text": "x"}, "not found"),
    ({"element": "tbl_b", "text": "x"}, "row and column"),
    ({"element": "tbl_b", "row": 9, "column": 0, "text": "x"}, "outside"),
    ({"element": "kpi_val", "row": 0, "column": 0, "text": "x"}, "not a table"),
    ({"element": "kpi_val"}, "'text'"),
    ({"element": "kpi_val", "text": "x", "delta": "maybe"}, "delta"),
])
def test_refill_validates_before_writing(deck, edit, match):
    with pytest.raises(ValueError, match=match):
        refill.refill_text("PRES1", [{"element": "kpi_delta", "text": "+1 %"}, edit])
    assert deck.batches == []


def test_refill_refuses_the_same_target_twice(deck):
    with pytest.raises(ValueError, match="twice"):
        refill.refill_text("PRES1", [{"element": "kpi_val", "text": "1"}, {"element": "kpi_val", "text": "2"}])


def test_sign_of():
    assert refill.sign_of("+8 %") == "up" and refill.sign_of(" ▲ 3") == "up"
    assert refill.sign_of("−2 pts") == "down" and refill.sign_of("-0,5") == "down"
    assert refill.sign_of("-") is None and refill.sign_of("12") is None


# --- replace_text: element scope and dry run --------------------------------------------------

def test_replace_dry_run_lists_every_match_and_writes_nothing(deck):
    out = content.replace_text("PRES1", find="nouveau levier", replace="levier Meta", slides=["3"], dry_run=True)
    assert deck.batches == [] and out["dry_run"] is True
    where = out["results"][0]["where"]
    assert [(w["element"], w["count"]) for w in where] == [("analysis", 2), ("label", 1)]
    assert "a porté la collecte" in where[0]["context"]
    assert out["total"] == 3


def test_replace_in_elements_touches_only_them_and_keeps_style(deck):
    out = content.replace_text("PRES1", find="nouveau levier", replace="Levier Meta", elements=["label"])
    (batch,) = deck.batches
    assert {r[next(iter(r))]["objectId"] for r in batch} == {"label"}
    assert _by_kind(batch, "deleteText")[0]["textRange"] == {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": 14}
    assert _by_kind(batch, "updateTextStyle")[0]["style"] == {"bold": True}
    assert out["results"][0]["occurrences"] == 1


def test_replace_in_elements_goes_from_last_match_to_first_with_utf16_indexes(deck, pres):
    pres["slides"][2]["pageElements"].append(_shape("emoji", "🚀 ab 🚀 ab", {"italic": True}))
    content.replace_text("PRES1", find="AB", replace="xyz", elements=["emoji"])
    deletes = _by_kind(deck.batches[0], "deleteText")
    assert [(d["textRange"]["startIndex"], d["textRange"]["endIndex"]) for d in deletes] == [(9, 11), (3, 5)]
    inserts = _by_kind(deck.batches[0], "insertText")
    assert [i["insertionIndex"] for i in inserts] == [9, 3]


def test_replace_in_table_cells_and_pairs_in_order(deck):
    out = content.replace_text("PRES1", pairs=[{"find": "Google", "replace": "Google Ads"},
                                               {"find": "Google Ads", "replace": "GAds"}], elements=["tbl_b"])
    assert [r["occurrences"] for r in out["results"]] == [1, 1]
    cells = {tuple(d["cellLocation"].values()) for d in _by_kind(deck.batches[0], "deleteText")}
    assert cells == {(1, 0)}


def test_replace_elements_and_slides_together_is_refused(deck):
    with pytest.raises(ValueError, match="not both"):
        content.replace_text("PRES1", find="a", replace="b", slides=["3"], elements=["label"])


def test_replace_elements_near_miss_when_absent(deck):
    out = content.replace_text("PRES1", find="Nouveau  levier", replace="x", elements=["label"])
    assert out["total"] == 0 and deck.batches == []


# --- transform_element: one axis at a time ----------------------------------------------------

def test_transform_x_alone_keeps_y(fake_slides, pres):
    el = pres["slides"][0]["pageElements"][2]
    ty = el["transform"].get("translateY", 0)
    transform_element("PRES1", el["objectId"], x_pt=50)
    t = fake_slides.batches[-1][0]["updatePageElementTransform"]["transform"]
    assert t["translateX"] == 50 * 12700 and t["translateY"] == int(ty)


def test_transform_mixes_absolute_and_relative_axes(fake_slides, pres):
    el = pres["slides"][0]["pageElements"][2]
    tx = el["transform"].get("translateX", 0)
    ty = el["transform"].get("translateY", 0)
    transform_element("PRES1", el["objectId"], dx_pt=10)
    t = fake_slides.batches[-1][0]["updatePageElementTransform"]["transform"]
    assert t["translateX"] == int(tx + 10 * 12700) and t["translateY"] == int(ty)
    transform_element("PRES1", el["objectId"], x_pt=5, dy_pt=-4)
    t = fake_slides.batches[-1][0]["updatePageElementTransform"]["transform"]
    assert t["translateX"] == 5 * 12700 and t["translateY"] == int(ty - 4 * 12700)
    with pytest.raises(ValueError, match="horizontally"):
        transform_element("PRES1", el["objectId"], x_pt=5, dx_pt=3)
