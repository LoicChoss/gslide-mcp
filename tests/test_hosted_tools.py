"""The hosted server serves the component catalogue; only a local server edits it."""

import asyncio

from gslides_mcp import server


def _names():
    return {t.name for t in asyncio.run(server.mcp.list_tools())}


def test_hosted_server_hides_component_editing(monkeypatch):
    removed = []
    monkeypatch.setattr(server.mcp.local_provider, "remove_tool", removed.append)
    server.hide_local_only_tools()
    assert removed == ["save_component", "delete_component"]


def test_local_server_keeps_them():
    names = _names()
    assert {"save_component", "delete_component", "list_components", "insert_component"} <= names


def test_hosted_server_never_writes_a_library_file(monkeypatch, tmp_path):
    import pytest
    from gslides_mcp.tools import library

    monkeypatch.setenv("GSLIDES_MCP_TRANSPORT", "http")
    monkeypatch.setattr(library, "summarize_deck", lambda d: pytest.fail("ran before refusing"))
    with pytest.raises(ValueError, match="output_path"):
        library.build_template_library(["D1"], output_path=str(tmp_path / "x.json"))
    assert not (tmp_path / "x.json").exists()
