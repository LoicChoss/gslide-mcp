"""The server tells Claude it is for Google Slides, and sends PowerPoint requests elsewhere."""

from gslides_mcp.app import mcp


def test_instructions_send_powerpoint_requests_elsewhere():
    assert "Google Slides only" in mcp.instructions
    assert "PowerPoint" in mcp.instructions
    assert "do not use this" in mcp.instructions
