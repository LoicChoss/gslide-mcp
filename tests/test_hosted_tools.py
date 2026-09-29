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


def test_redirects_are_limited_to_claude_and_loopback(monkeypatch):
    from fastmcp.server.auth.redirect_validation import validate_redirect_uri

    monkeypatch.delenv("GSLIDES_MCP_REDIRECT_HOSTS", raising=False)
    patterns = server.redirect_patterns()
    assert validate_redirect_uri("https://claude.ai/api/mcp/auth_callback", patterns)
    assert validate_redirect_uri("http://localhost:6274/callback", patterns)
    assert not validate_redirect_uri("https://evil.example/callback", patterns)
    assert not validate_redirect_uri("https://claude.ai.evil.example/cb", patterns)


def test_tool_calls_beyond_the_limit_wait():
    import asyncio

    limiter = server.MaxInFlight(2)
    running, peak = 0, 0

    async def call_next(_):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return "ok"

    async def main():
        return await asyncio.gather(*(limiter.on_call_tool(None, call_next) for _ in range(6)))

    assert asyncio.run(main()) == ["ok"] * 6
    assert peak == 2
