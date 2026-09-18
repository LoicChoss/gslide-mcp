"""create_slide_from_layout / build_from_outline: one batch, no deleteText."""

import pytest

from gslides_mcp.tools import layout


def _kinds(reqs):
    return [next(iter(r)) for r in reqs]


def _create(reqs):
    return next(r["createSlide"] for r in reqs if "createSlide" in r)


# --- create_slide_from_layout ------------------------------------------------

def test_creates_slide_and_fills_in_one_batch(fake_slides):
    out = layout.create_slide_from_layout(
        "PRES1", "Titre et corps", fills={"TITLE": "Hi", "BODY": "- a\n- b"}
    )
    assert len(fake_slides.batches) == 1
    reqs = fake_slides.batches[0]
    create = _create(reqs)
    assert reqs[0] == {"createSlide": create}
    assert create["slideLayoutReference"] == {"layoutId": "lay_body"}
    mapped = {m["layoutPlaceholderObjectId"]: m["objectId"] for m in create["placeholderIdMappings"]}
    assert set(mapped) == {"lay_body_t", "lay_body_b"}
    assert "deleteText" not in _kinds(reqs)
    inserted = {r["insertText"]["objectId"] for r in reqs if "insertText" in r}
    assert inserted == set(mapped.values())
    assert "createParagraphBullets" in _kinds(reqs)
    assert out["slide_id"] == create["objectId"]
    assert out["index"] == 4  # 1-based: appended after the 3 fixture slides
    assert out["layout_id"] == "lay_body"
    assert out["layout_name"] == "Titre et corps"
    assert out["placeholders_filled"] == ["TITLE", "BODY"]
    assert out["placeholders_left_empty"] == ["SLIDE_NUMBER"]


def test_indexed_keys_target_each_body_placeholder(fake_slides):
    out = layout.create_slide_from_layout(
        "PRES1", "A_Retenir", fills={"TITLE": "T", "BODY[0]": "left", "BODY[1]": "right"}
    )
    create = _create(fake_slides.batches[0])
    mapped = {m["layoutPlaceholderObjectId"]: m["objectId"] for m in create["placeholderIdMappings"]}
    texts = {r["insertText"]["objectId"]: r["insertText"]["text"] for r in fake_slides.batches[0] if "insertText" in r}
    assert texts[mapped["lay_two_b1"]] == "left"
    assert texts[mapped["lay_two_b2"]] == "right"
    assert out["placeholders_left_empty"] == []


def test_bare_key_on_layout_with_two_bodies_is_rejected(fake_slides):
    with pytest.raises(ValueError, match=r"BODY\[0\].*BODY\[1\]"):
        layout.create_slide_from_layout("PRES1", "A_Retenir", fills={"BODY": "x"})
    assert fake_slides.batches == []


def test_unknown_fill_key_lists_available_placeholders(fake_slides):
    with pytest.raises(ValueError, match="FOOTER") as exc:
        layout.create_slide_from_layout("PRES1", "Titre et corps", fills={"FOOTER": "x"})
    assert "TITLE" in str(exc.value) and "BODY" in str(exc.value)
    assert fake_slides.batches == []


def test_insertion_index_and_custom_object_id(fake_slides):
    out = layout.create_slide_from_layout(
        "PRES1", "lay_title", insertion_index=1, object_id="my_slide_1"
    )
    create = _create(fake_slides.batches[0])
    assert create["insertionIndex"] == 1
    assert create["objectId"] == "my_slide_1"
    assert out["slide_id"] == "my_slide_1"
    assert out["index"] == 2  # insertion_index 1 (0-based) -> 2nd slide
    assert out["placeholders_filled"] == []
    assert create.get("placeholderIdMappings", []) == []


def test_invalid_object_id_rejected_before_any_call(fake_slides):
    with pytest.raises(ValueError, match="object_id"):
        layout.create_slide_from_layout("PRES1", "lay_title", object_id="s1")
    assert fake_slides.get_calls == []


def test_markdown_bold_becomes_text_style_request(fake_slides):
    layout.create_slide_from_layout("PRES1", "lay_title", fills={"CENTERED_TITLE": "**Bold** title"})
    styles = [r["updateTextStyle"] for r in fake_slides.batches[0] if "updateTextStyle" in r]
    assert any(s["style"].get("bold") for s in styles)


def test_empty_fill_leaves_placeholder_untouched(fake_slides):
    out = layout.create_slide_from_layout("PRES1", "lay_title", fills={"CENTERED_TITLE": "  ", "SUBTITLE": "s"})
    assert out["placeholders_filled"] == ["SUBTITLE"]
    assert "CENTERED_TITLE" in out["placeholders_left_empty"]


# --- build_from_outline ----------------------------------------------------

def test_outline_builds_every_slide_in_one_batch(fake_slides):
    out = layout.build_from_outline("PRES1", [
        {"layout": "A_Retenir", "fills": {"TITLE": "One", "BODY[0]": "a"}},
        {"layout": "Titre et corps", "fills": {"TITLE": "Two"}},
    ], insertion_index=1)
    assert len(fake_slides.batches) == 1
    creates = [r["createSlide"] for r in fake_slides.batches[0] if "createSlide" in r]
    assert [c["insertionIndex"] for c in creates] == [1, 2]
    assert [c["slideLayoutReference"]["layoutId"] for c in creates] == ["lay_two", "lay_body"]
    assert out == [
        {"index": 2, "slide_id": creates[0]["objectId"], "layout_name": "A_Retenir"},
        {"index": 3, "slide_id": creates[1]["objectId"], "layout_name": "Titre et corps"},
    ]


def test_outline_appends_at_end_by_default(fake_slides):
    out = layout.build_from_outline("PRES1", [{"layout": "lay_title"}, {"layout": "lay_body"}])
    assert [s["index"] for s in out] == [4, 5]
    creates = [r["createSlide"] for r in fake_slides.batches[0] if "createSlide" in r]
    assert all("insertionIndex" not in c for c in creates)


def test_outline_reports_every_problem_before_writing(fake_slides):
    with pytest.raises(ValueError) as exc:
        layout.build_from_outline("PRES1", [
            {"layout": "Nope"},
            {"layout": "Arborescence"},
            {"layout": "lay_body", "fills": {"FOOTER": "x"}},
            {"fills": {}},
        ])
    msg = str(exc.value)
    assert "outline[0]" in msg and "'Nope'" in msg
    assert "outline[1]" in msg and "ambiguous" in msg
    assert "outline[2]" in msg and "FOOTER" in msg
    assert "outline[3]" in msg and "layout" in msg
    assert fake_slides.batches == []


def test_outline_google_rejection_creates_nothing(fake_slides):
    from conftest import make_http_error

    fake_slides.fail_next_batch = make_http_error(400, "Invalid requests[1].createSlide")
    with pytest.raises(Exception, match="createSlide"):
        layout.build_from_outline("PRES1", [{"layout": "lay_title"}, {"layout": "lay_body"}])
    assert fake_slides.batches == []
