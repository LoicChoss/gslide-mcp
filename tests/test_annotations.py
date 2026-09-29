"""Every tool carries MCP annotations; the hints match what the tool does."""

import asyncio

import pytest

import gslides_mcp.tools  # noqa: F401  — registers the tools
from gslides_mcp.app import mcp

READ_ONLY = [
    "list_slides", "list_layouts", "get_page", "get_presentation", "get_speaker_notes",
    "inspect_slide", "find_elements", "screenshot", "screenshot_range", "screenshot_layout",
    "screenshot_layouts", "summarize_deck", "overlap_check", "cross_deck_ping", "export_pres",
    "fetch_logo_by_domain", "list_components",
]
DESTRUCTIVE = [
    "delete_slides", "delete_elements", "relayout_slide", "manage_comments", "edit_table",
    "batch_apply", "raw_request", "delete_component",
]
IDEMPOTENT = [
    "set_text", "set_speaker_notes", "set_background", "set_slide_hidden", "set_fill", "set_outline",
    "set_table_cell", "write_text_markdown", "batch_write_markdown", "style_text", "refill_text", "move_to_folder", "resize_table", "replace_images",
]


def _annotations():
    return {t.name: t.annotations for t in asyncio.run(mcp.list_tools())}


def test_every_tool_is_annotated():
    missing = sorted(name for name, a in _annotations().items() if a is None)
    assert missing == []


@pytest.mark.parametrize("name", READ_ONLY)
def test_read_only_hint(name):
    a = _annotations()[name]
    assert a.readOnlyHint is True
    assert not a.destructiveHint


@pytest.mark.parametrize("name", DESTRUCTIVE)
def test_destructive_hint(name):
    a = _annotations()[name]
    assert a.destructiveHint is True
    assert not a.readOnlyHint


@pytest.mark.parametrize("name", IDEMPOTENT)
def test_idempotent_hint(name):
    a = _annotations()[name]
    assert a.idempotentHint is True
    assert a.destructiveHint is False
    assert not a.readOnlyHint


def test_additive_writers_are_marked_non_destructive():
    ann = _annotations()
    for name in ("create_slide", "create_slide_from_layout", "build_from_outline", "create_table",
                 "insert_image", "insert_image_local", "create_shape", "duplicate_slide",
                 "clone_deck", "create_presentation", "copy_slide_cross_deck"):
        assert ann[name].destructiveHint is False, name
        assert not ann[name].readOnlyHint, name
