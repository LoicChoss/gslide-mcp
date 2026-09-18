"""relayout_slide: rebuild a slide on another layout, then delete the original."""

import pytest
from conftest import make_http_error

from gslides_mcp.tools import layout


def _reqs(batch, kind):
    return [r[kind] for r in batch if kind in r]


def test_refuses_groups_tables_and_videos_before_writing(fake_slides):
    with pytest.raises(ValueError) as exc:
        layout.relayout_slide("PRES1", "slide_2", "lay_title")
    msg = str(exc.value)
    assert "tbl_1" in msg and "s2_group" in msg
    assert fake_slides.batches == []


def test_rebuilds_slide_on_target_layout_then_deletes_original(fake_slides):
    out = layout.relayout_slide("PRES1", "1", "Titre et corps")

    assert len(fake_slides.batches) == 3
    build, notes_batch, cleanup = fake_slides.batches

    create = _reqs(build, "createSlide")[0]
    assert create["slideLayoutReference"] == {"layoutId": "lay_body"}
    assert create["insertionIndex"] == 1  # right after the original (index 0)
    mapped = {m["layoutPlaceholderObjectId"]: m["objectId"] for m in create["placeholderIdMappings"]}
    assert "lay_body_t" in mapped  # CENTERED_TITLE → TITLE

    texts = {t["objectId"]: t["text"] for t in _reqs(build, "insertText")}
    assert texts[mapped["lay_body_t"]] == "Hello title"

    shape = _reqs(build, "createShape")[0]
    assert shape["shapeType"] == "RECTANGLE"
    assert shape["elementProperties"]["pageObjectId"] == create["objectId"]
    assert shape["elementProperties"]["size"]["width"]["magnitude"] == 1000000
    assert shape["elementProperties"]["transform"]["translateX"] == 5000000
    assert texts[shape["objectId"]] == "Box"
    fill = _reqs(build, "updateShapeProperties")[0]
    assert fill["shapeProperties"]["shapeBackgroundFill"]["solidFill"]["color"]["rgbColor"]["red"] == 1

    image = _reqs(build, "createImage")[0]
    assert image["url"] == "https://lh7.googleusercontent.com/img1"
    assert image["elementProperties"]["size"]["height"]["magnitude"] == 600000

    assert "deleteText" not in {next(iter(r)) for r in build}
    assert notes_batch == [{"insertText": {
        "objectId": f"{create['objectId']}_notes", "text": "Existing note", "insertionIndex": 0,
    }}]
    assert cleanup == [{"deleteObject": {"objectId": "slide_1"}}]

    assert out["new_slide_id"] == create["objectId"]
    assert out["deleted_slide_id"] == "slide_1"
    assert out["index"] == 1  # 1-based, same position as the original
    assert out["notes_copied"] is True
    assert out["layout_name"] == "Titre et corps"
    assert out["placeholders_copied"] == ["CENTERED_TITLE->TITLE"]
    assert out["unplaced_text"] == [{"type": "SUBTITLE", "text": "Sub"}]
    assert sorted(out["elements_recreated"]) == ["s1_box", "s1_img"]


def test_original_kept_when_deletion_fails(fake_slides):
    fake_slides.fail_at = 3
    with pytest.raises(RuntimeError, match="slide_1"):
        layout.relayout_slide("PRES1", "slide_1", "lay_body")
    assert len(fake_slides.batches) == 2  # rebuild + notes went through


def test_nothing_happens_when_build_fails(fake_slides):
    fake_slides.fail_next_batch = make_http_error(400, "bad createShape")
    with pytest.raises(Exception, match="createShape"):
        layout.relayout_slide("PRES1", "slide_1", "lay_body")
    assert fake_slides.batches == []


def test_unknown_slide_and_layout_named(fake_slides):
    with pytest.raises(ValueError, match="'99'"):
        layout.relayout_slide("PRES1", "99", "lay_body")
    with pytest.raises(ValueError, match="'Nope'"):
        layout.relayout_slide("PRES1", "slide_1", "Nope")


def test_slide_without_notes_needs_no_notes_batch(fake_slides):
    out = layout.relayout_slide("PRES1", "slide_3", "lay_title")
    assert len(fake_slides.batches) == 2
    assert out["notes_copied"] is False


def test_original_kept_when_notes_copy_fails(fake_slides):
    fake_slides.fail_at = 2
    with pytest.raises(RuntimeError, match="notes.*slide_1"):
        layout.relayout_slide("PRES1", "slide_1", "lay_body")
    assert len(fake_slides.batches) == 1
