"""rename_element: duplicate with the new id, delete the original, put it back in the z-order."""

import pytest

from gslides_mcp.tools.layout import rename_element


def _kinds(batch):
    return [next(iter(r)) for r in batch]


def test_rename_is_one_batch_that_restores_the_stacking_order(fake_slides):
    # slide 1 stacks s1_title, s1_sub, s1_box, s1_img; the copy lands on top (verified live)
    out = rename_element("PRES1", [{"element": "s1_sub", "new_id": "subtitle_main"}])
    (batch,) = fake_slides.batches
    assert batch[0] == {"duplicateObject": {"objectId": "s1_sub", "objectIds": {"s1_sub": "subtitle_main"}}}
    assert batch[1] == {"deleteObject": {"objectId": "s1_sub"}}
    assert batch[2:] == [{"updatePageElementsZOrder": {"pageElementObjectIds": ["subtitle_main"],
                                                       "operation": "SEND_BACKWARD"}}] * 2
    assert out == {"renamed": [{"element": "s1_sub", "new_id": "subtitle_main", "slide_id": "slide_1"}], "z_moves": 2}


def test_several_renames_on_one_slide_each_find_their_place(fake_slides):
    out = rename_element("PRES1", [{"element": "s1_title", "new_id": "title_main"},
                                   {"element": "s1_img", "new_id": "visual_main"}])
    (batch,) = fake_slides.batches
    assert _kinds(batch) == ["duplicateObject", "deleteObject", "duplicateObject", "deleteObject",
                             "updatePageElementsZOrder", "updatePageElementsZOrder"]
    # after the copies: sub, box, title_main, visual_main → title_main goes back 2 steps, visual_main stays last
    assert {r["updatePageElementsZOrder"]["pageElementObjectIds"][0] for r in batch[4:]} == {"title_main"}
    assert out["z_moves"] == 2


def test_the_top_element_needs_no_move(fake_slides):
    out = rename_element("PRES1", [{"element": "s1_img", "new_id": "visual_main"}])
    assert _kinds(fake_slides.batches[0]) == ["duplicateObject", "deleteObject"] and out["z_moves"] == 0


@pytest.mark.parametrize("renames, match", [
    ([], "renames is empty"),
    ([{"element": "s1_sub"}], "new_id"),
    ([{"element": "nope", "new_id": "abcdef"}], "not found"),
    ([{"element": "s1_sub", "new_id": "ab"}], "invalid object_id"),
    ([{"element": "s1_sub", "new_id": "tbl_1"}], "already used"),
    ([{"element": "s1_sub", "new_id": "slide_2"}], "already used"),
    ([{"element": "s2_child", "new_id": "child_main"}], "inside a group"),
    ([{"element": "s2_group", "new_id": "group_main"}], "group"),
    ([{"element": "s1_sub", "new_id": "abcdef"}, {"element": "s1_box", "new_id": "abcdef"}], "twice"),
    ([{"element": "s1_sub", "new_id": "abcdef"}, {"element": "s1_sub", "new_id": "ghijkl"}], "twice"),
])
def test_refusals_come_before_any_write(fake_slides, renames, match):
    with pytest.raises(ValueError, match=match):
        rename_element("PRES1", renames)
    assert fake_slides.batches == []
