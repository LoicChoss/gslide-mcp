"""Hosted mode: cross-deck copy goes through scripts.run as the caller, never the web app."""

import io
import json

import pytest

from gslides_mcp.tools import cross_deck


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _capture(monkeypatch, answer):
    sent = {}

    def fake_urlopen(req, timeout=None, context=None):
        sent["url"] = req.full_url
        sent["auth"] = req.get_header("Authorization")
        sent["body"] = json.loads(req.data)
        return _Resp(json.dumps(answer).encode())

    monkeypatch.setattr(cross_deck.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(cross_deck, "access_token", lambda: "user-token")
    return sent


def test_copy_uses_scripts_run_with_the_callers_token(monkeypatch):
    monkeypatch.setenv("GSLIDES_MCP_APPSCRIPT_ID", "SCRIPT123")
    sent = _capture(monkeypatch, {"done": True, "response": {"result": {"newSlideId": "g1", "dstIndex": 3}}})
    out = cross_deck.copy_slide_cross_deck("SRC", "2", "DST")
    assert out == {"newSlideId": "g1", "dstIndex": 3}
    assert sent["url"] == "https://script.googleapis.com/v1/scripts/SCRIPT123:run"
    assert sent["auth"] == "Bearer user-token"
    assert sent["body"]["function"] == "api"
    params = sent["body"]["parameters"][0]
    assert params["op"] == "copy" and params["srcId"] == "SRC" and params["dstId"] == "DST"
    assert params["requestId"]


def test_script_errors_surface_their_message(monkeypatch):
    monkeypatch.setenv("GSLIDES_MCP_APPSCRIPT_ID", "SCRIPT123")
    _capture(monkeypatch, {"done": True, "error": {"details": [{"errorMessage": "src slide not found: 9"}]}})
    with pytest.raises(RuntimeError, match="src slide not found: 9"):
        cross_deck.copy_slide_cross_deck("SRC", "9", "DST")


def test_hosted_server_refuses_the_web_app(monkeypatch):
    monkeypatch.setenv("GSLIDES_MCP_TRANSPORT", "http")
    monkeypatch.delenv("GSLIDES_MCP_APPSCRIPT_ID", raising=False)
    monkeypatch.setenv("GSLIDES_MCP_APPSCRIPT_URL", "https://script.google.com/macros/s/X/exec")
    with pytest.raises(RuntimeError, match="API executable"):
        cross_deck.copy_slide_cross_deck("SRC", "1", "DST")
