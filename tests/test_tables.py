"""Tables: create with data, structural edits, markdown into one cell."""

import pytest

from gslides_mcp.tools import tables


def _only(batch, kind):
    return [r[kind] for r in batch if kind in r]


# --- create_table -----------------------------------------------------------

def test_create_table_with_data_is_one_batch(fake_slides):
    out = tables.create_table(
        "PRES1", "2", rows=2, columns=3, x_pt=10, y_pt=20, width_pt=300, height_pt=100,
        data=[["a", "b"], ["", "d", "e"]],
    )
    assert len(fake_slides.batches) == 1
    batch = fake_slides.batches[0]
    create = _only(batch, "createTable")[0]
    assert create["rows"] == 2 and create["columns"] == 3
    props = create["elementProperties"]
    assert props["pageObjectId"] == "slide_2"
    assert props["size"] == {
        "width": {"magnitude": 300 * 12700, "unit": "EMU"},
        "height": {"magnitude": 100 * 12700, "unit": "EMU"},
    }
    assert props["transform"]["translateX"] == 10 * 12700
    assert props["transform"]["translateY"] == 20 * 12700
    table_id = create["objectId"]
    assert out == {"table_id": table_id, "slide_id": "slide_2", "rows": 2, "columns": 3, "cells_written": 4}
    cells = {(i["cellLocation"]["rowIndex"], i["cellLocation"]["columnIndex"]): i["text"]
             for i in _only(batch, "insertText")}
    assert cells == {(0, 0): "a", (0, 1): "b", (1, 1): "d", (1, 2): "e"}
    assert all(i["objectId"] == table_id for i in _only(batch, "insertText"))


def test_create_table_without_data_has_no_text_requests(fake_slides):
    tables.create_table("PRES1", "slide_3", rows=1, columns=1, x_pt=0, y_pt=0, width_pt=50, height_pt=20)
    assert [next(iter(r)) for r in fake_slides.batches[0]] == ["createTable"]


@pytest.mark.parametrize("rows, columns", [(21, 2), (2, 21), (0, 3)])
def test_create_table_rejects_out_of_range_dimensions(fake_slides, rows, columns):
    with pytest.raises(ValueError, match="20"):
        tables.create_table("PRES1", "2", rows=rows, columns=columns, x_pt=0, y_pt=0, width_pt=50, height_pt=20)
    assert fake_slides.batches == []


def test_create_table_rejects_data_larger_than_grid(fake_slides):
    with pytest.raises(ValueError, match="row 2"):
        tables.create_table("PRES1", "2", rows=2, columns=2, x_pt=0, y_pt=0, width_pt=50, height_pt=20,
                            data=[["a"], ["b"], ["c"]])
    with pytest.raises(ValueError, match="column"):
        tables.create_table("PRES1", "2", rows=2, columns=2, x_pt=0, y_pt=0, width_pt=50, height_pt=20,
                            data=[["a", "b", "c"]])
    assert fake_slides.batches == []


def test_create_table_custom_object_id(fake_slides):
    out = tables.create_table("PRES1", "2", rows=1, columns=1, x_pt=0, y_pt=0, width_pt=50, height_pt=20,
                              object_id="my_table_1")
    assert out["table_id"] == "my_table_1"


# --- edit_table -------------------------------------------------------------

def test_insert_rows_after(fake_slides):
    out = tables.edit_table("PRES1", "tbl_1", "insert_rows", index=0, count=2)
    assert fake_slides.batches == [[{"insertTableRows": {
        "tableObjectId": "tbl_1", "cellLocation": {"rowIndex": 0}, "insertBelow": True, "number": 2,
    }}]]
    assert out == {"table_id": "tbl_1", "action": "insert_rows", "index": 0, "count": 2, "position": "after"}


def test_insert_columns_before(fake_slides):
    tables.edit_table("PRES1", "tbl_1", "insert_columns", index=1, position="before")
    assert fake_slides.batches == [[{"insertTableColumns": {
        "tableObjectId": "tbl_1", "cellLocation": {"columnIndex": 1}, "insertRight": False, "number": 1,
    }}]]


def test_delete_rows_repeats_the_same_index(fake_slides):
    tables.edit_table("PRES1", "tbl_1", "delete_row", index=1, count=2)
    assert fake_slides.batches == [[
        {"deleteTableRow": {"tableObjectId": "tbl_1", "cellLocation": {"rowIndex": 1}}},
        {"deleteTableRow": {"tableObjectId": "tbl_1", "cellLocation": {"rowIndex": 1}}},
    ]]


def test_delete_column(fake_slides):
    tables.edit_table("PRES1", "tbl_1", "delete_column", index=0)
    assert fake_slides.batches == [[
        {"deleteTableColumn": {"tableObjectId": "tbl_1", "cellLocation": {"columnIndex": 0}}},
    ]]


def test_edit_table_validates_inputs(fake_slides):
    with pytest.raises(ValueError, match="insert_rows"):
        tables.edit_table("PRES1", "tbl_1", "explode", index=0)
    with pytest.raises(ValueError, match="index"):
        tables.edit_table("PRES1", "tbl_1", "delete_row")
    with pytest.raises(ValueError, match="position"):
        tables.edit_table("PRES1", "tbl_1", "insert_rows", index=0, position="sideways")
    with pytest.raises(ValueError, match="count"):
        tables.edit_table("PRES1", "tbl_1", "insert_rows", index=0, count=0)
    assert fake_slides.batches == []


# --- set_table_cell ---------------------------------------------------------

def test_set_table_cell_clears_existing_text_then_writes_markdown(fake_slides):
    out = tables.set_table_cell("PRES1", "tbl_1", 0, 0, "**bold** x")
    batch = fake_slides.batches[0]
    assert batch[0] == {"deleteText": {
        "objectId": "tbl_1", "cellLocation": {"rowIndex": 0, "columnIndex": 0}, "textRange": {"type": "ALL"},
    }}
    for req in batch[1:]:
        (_, payload), = req.items()
        assert payload["objectId"] == "tbl_1"
        assert payload["cellLocation"] == {"rowIndex": 0, "columnIndex": 0}
    assert any("updateTextStyle" in r and r["updateTextStyle"]["style"].get("bold") for r in batch)
    assert out == {"table_id": "tbl_1", "row": 0, "column": 0, "content_length": len("**bold** x")}


def test_set_table_cell_on_empty_cell_skips_delete(fake_slides):
    tables.set_table_cell("PRES1", "tbl_1", 1, 1, "y")
    assert "deleteText" not in {next(iter(r)) for r in fake_slides.batches[0]}


def test_set_table_cell_treats_paragraph_marker_only_as_empty(fake_slides):
    tables.set_table_cell("PRES1", "tbl_1", 0, 1, "y")
    assert "deleteText" not in {next(iter(r)) for r in fake_slides.batches[0]}


def test_set_table_cell_out_of_range_names_dimensions(fake_slides):
    with pytest.raises(ValueError, match="2x2"):
        tables.set_table_cell("PRES1", "tbl_1", 2, 0, "y")
    assert fake_slides.batches == []


def test_set_table_cell_unknown_or_not_a_table(fake_slides):
    with pytest.raises(ValueError, match="'nope'"):
        tables.set_table_cell("PRES1", "nope", 0, 0, "y")
    with pytest.raises(ValueError, match="not a table"):
        tables.set_table_cell("PRES1", "s1_box", 0, 0, "y")


# --- resize_table -----------------------------------------------------------

def test_resize_table_rows_and_columns(fake_slides):
    out = tables.resize_table("PRES1", "tbl_1", row_height_pt=30, rows=[1], column_widths_pt=[120, None])
    (batch,) = fake_slides.batches
    assert _only(batch, "updateTableRowProperties") == [{
        "objectId": "tbl_1", "rowIndices": [1],
        "tableRowProperties": {"minRowHeight": {"magnitude": 30, "unit": "PT"}}, "fields": "minRowHeight",
    }]
    assert _only(batch, "updateTableColumnProperties") == [{
        "objectId": "tbl_1", "columnIndices": [0],
        "tableColumnProperties": {"columnWidth": {"magnitude": 120, "unit": "PT"}}, "fields": "columnWidth",
    }]
    assert out == {"table_id": "tbl_1", "rows": [1], "row_height_pt": 30, "column_widths_pt": [120, None]}


def test_resize_table_sets_every_row_by_default(fake_slides):
    tables.resize_table("PRES1", "tbl_1", row_height_pt=26)
    assert _only(fake_slides.batches[0], "updateTableRowProperties")[0]["rowIndices"] == [0, 1]
    assert _only(fake_slides.batches[0], "updateTableColumnProperties") == []


@pytest.mark.parametrize("kw, match", [
    ({}, "row_height_pt or column_widths_pt"),
    ({"column_widths_pt": [20, 100]}, "32"),
    ({"column_widths_pt": [100]}, "2 columns"),
    ({"row_height_pt": 20, "rows": [5]}, "outside"),
    ({"row_height_pt": 0}, "positive"),
])
def test_resize_table_validates_before_writing(fake_slides, kw, match):
    with pytest.raises(ValueError, match=match):
        tables.resize_table("PRES1", "tbl_1", **kw)
    assert fake_slides.batches == []


def test_resize_table_needs_a_table(fake_slides):
    with pytest.raises(ValueError, match="not a table"):
        tables.resize_table("PRES1", "s1_box", row_height_pt=30)
