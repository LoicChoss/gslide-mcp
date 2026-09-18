"""Live round-trip against a real deck. Opt in with::

    GSLIDES_MCP_INTEGRATION_DECK=<presentation id> uv run --with pytest pytest tests/test_integration.py

The deck must be writable by the OAuth account; slides created here are
deleted again, layouts are only read.
"""

import os

import pytest

DECK = os.environ.get("GSLIDES_MCP_INTEGRATION_DECK")

pytestmark = pytest.mark.skipif(not DECK, reason="GSLIDES_MCP_INTEGRATION_DECK not set")


def test_layouts_screenshot_build_verify_delete():
    from gslides_mcp.auth import slide_service
    from gslides_mcp.tools import layout, slides

    listed = layout.list_layouts(DECK)
    assert listed["masters"] and listed["layouts"]
    with_body = [l for l in listed["layouts"] if any(p["type"] == "BODY" for p in l["placeholders"])]
    assert with_body, "need at least one layout with a BODY placeholder"
    body_layout = with_body[0]
    title_layout = listed["layouts"][0]

    img = layout.screenshot_layout(DECK, body_layout["layout_id"], size="SMALL")
    assert img.path and os.path.getsize(img.path) > 0

    created = layout.build_from_outline(DECK, [
        {"layout": title_layout["layout_id"], "fills": {}},
        {"layout": body_layout["layout_id"], "fills": _fills_for(body_layout)},
    ])
    try:
        assert len(created) == 2
        pres = slide_service().presentations().get(
            presentationId=DECK, fields="slides(objectId,slideProperties(layoutObjectId))"
        ).execute()
        by_id = {s["objectId"]: s["slideProperties"]["layoutObjectId"] for s in pres["slides"]}
        assert by_id[created[0]["slide_id"]] == title_layout["layout_id"]
        assert by_id[created[1]["slide_id"]] == body_layout["layout_id"]
    finally:
        slides.delete_slides(DECK, [c["slide_id"] for c in created])


def _fills_for(layout_entry: dict) -> dict:
    """TITLE + first BODY of the layout, addressed the way the tool expects."""
    types = [p["type"] for p in layout_entry["placeholders"]]
    fills = {}
    if types.count("TITLE") == 1:
        fills["TITLE"] = "Integration **test**"
    fills["BODY" if types.count("BODY") == 1 else "BODY[0]"] = "- one\n- two"
    return fills
