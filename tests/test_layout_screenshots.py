"""screenshot_layout / screenshot_layouts and the strip compositor they share."""

import os
import tempfile

import pytest
from PIL import Image as PILImage

from gslides_mcp.tools import layout, qa


def _png(w, h):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    PILImage.new("RGB", (w, h), (10, 20, 30)).save(path, "PNG")
    return path


def test_composite_strip_stacks_thumbs_with_label_bands_and_gaps():
    a, b = _png(200, 100), _png(160, 80)
    out = qa._composite_strip([("first", a), ("second", b)])
    with PILImage.open(out) as im:
        assert im.width == 200
        assert im.height == (100 + 24) + 8 + (80 + 24)
    assert not os.path.exists(a) and not os.path.exists(b)  # inputs cleaned up
    os.unlink(out)


def test_screenshot_layout_uses_the_layout_id_directly(fake_slides, fake_download):
    img = layout.screenshot_layout("PRES1", "Titre et corps", size="MEDIUM")
    assert fake_slides.thumbnail_calls == [{"page": "lay_body", "size": "MEDIUM"}]
    assert fake_slides.batches == []  # no temporary slide created
    assert img.data or img.path


def test_screenshot_layout_unknown_layout(fake_slides, fake_download):
    with pytest.raises(ValueError, match="layout not found"):
        layout.screenshot_layout("PRES1", "Nope")


def test_screenshot_layouts_defaults_to_layouts_of_used_masters(fake_slides, fake_download):
    img = layout.screenshot_layouts("PRES1")
    pages = [c["page"] for c in fake_slides.thumbnail_calls]
    assert pages == ["lay_title", "lay_body", "lay_two", "lay_summary", "lay_dup_a"]
    assert all(c["size"] == "SMALL" for c in fake_slides.thumbnail_calls)
    with PILImage.open(img.path) as im:
        assert im.height >= 5 * 112


def test_screenshot_layouts_subset_in_given_order(fake_slides, fake_download):
    layout.screenshot_layouts("PRES1", layouts=["A_Retenir", "lay_title"], size="MEDIUM")
    assert [c["page"] for c in fake_slides.thumbnail_calls] == ["lay_two", "lay_title"]


def test_screenshot_layouts_rejects_unknown_before_any_fetch(fake_slides, fake_download):
    with pytest.raises(ValueError, match="'Nope'"):
        layout.screenshot_layouts("PRES1", layouts=["lay_title", "Nope"])
    assert fake_slides.thumbnail_calls == []


def test_annotate_builds_a_temp_slide_labelled_with_keys_then_deletes_it(fake_slides, fake_download):
    img = layout.screenshot_layout("PRES1", "A_Retenir", annotate=True)
    build, cleanup = fake_slides.batches
    create = build[0]["createSlide"]
    assert create["slideLayoutReference"] == {"layoutId": "lay_two"}
    assert "insertionIndex" not in create
    texts = sorted(r["insertText"]["text"] for r in build if "insertText" in r)
    assert texts == ["BODY[0]", "BODY[1]", "TITLE"]
    assert fake_slides.thumbnail_calls == [{"page": create["objectId"], "size": "MEDIUM"}]
    assert cleanup == [{"deleteObject": {"objectId": create["objectId"]}}]
    assert img.path


def test_annotate_skips_placeholders_that_take_no_text(fake_slides, fake_download):
    layout.screenshot_layout("PRES1", "Titre et corps", annotate=True)
    texts = sorted(r["insertText"]["text"] for r in fake_slides.batches[0] if "insertText" in r)
    assert texts == ["BODY", "TITLE"]  # SLIDE_NUMBER left alone


def test_annotate_deletes_the_temp_slide_even_when_the_render_fails(fake_slides, fake_download, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("net down")
    monkeypatch.setattr(qa, "_download_to", boom)
    with pytest.raises(RuntimeError, match="net down"):
        layout.screenshot_layout("PRES1", "lay_title", annotate=True)
    assert "deleteObject" in fake_slides.batches[-1][0]
