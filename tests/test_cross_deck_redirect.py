"""Redirect policy for the Apps Script POST -> echo hop (see cross_deck.py)."""

import io
import urllib.request

import pytest

from gslides_mcp.tools import cross_deck


def _req(headers=None):
    return urllib.request.Request(
        "https://script.google.com/macros/s/AKfycbX/exec",
        data=b'{"op":"ping"}',
        headers=headers or {"Authorization": "Bearer secret", "Content-Type": "application/json"},
        method="POST",
    )


def _redirect(newurl):
    handler = cross_deck._EchoOnlyRedirect()
    return handler.redirect_request(_req(), io.BytesIO(), 302, "Found", {}, newurl)


def test_follows_apps_script_echo_host_as_bare_get():
    new = _redirect("https://script.googleusercontent.com/macros/echo?user_content_key=abc&lib=xyz")
    assert new is not None
    assert new.get_method() == "GET"
    assert new.data is None
    assert not new.has_header("Authorization")
    assert new.full_url.startswith("https://script.googleusercontent.com/macros/echo?")


@pytest.mark.parametrize(
    "newurl",
    [
        "https://evil.example.com/macros/echo",
        "http://script.googleusercontent.com/macros/echo",  # plain http
        "https://script.googleusercontent.com.evil.example/echo",
        "https://accounts.google.com/ServiceLogin?continue=x",  # private deployment
    ],
)
def test_refuses_any_other_destination(newurl):
    assert _redirect(newurl) is None


def test_at_most_one_hop():
    assert cross_deck._EchoOnlyRedirect.max_redirections == 1


# --- transient relay 404 (script.googleusercontent.com) -------------------

import email.message
import urllib.error


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "x", email.message.Message(), io.BytesIO(b""))


def _relay_404():
    return _http_error("https://script.googleusercontent.com/macros/echo?user_content_key=k", 404)


def test_relay_404_is_retried_for_idempotent_calls(monkeypatch):
    calls = []

    def fake_once(url, payload, timeout):
        calls.append(payload)
        if len(calls) < 3:
            cross_deck._raise_for(_relay_404())
        return {"ok": True}

    monkeypatch.setattr(cross_deck, "_post_json_once", fake_once)
    monkeypatch.setattr(cross_deck.time, "sleep", lambda s: None)
    assert cross_deck._post_json("https://script.google.com/x/exec", {"op": "ping"}) == {"ok": True}
    assert len(calls) == 3


def test_relay_404_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(cross_deck, "_post_json_once", lambda *a: cross_deck._raise_for(_relay_404()))
    monkeypatch.setattr(cross_deck.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="relay"):
        cross_deck._post_json("https://script.google.com/x/exec", {"op": "ping"})


def test_relay_404_not_retried_when_replay_unsafe(monkeypatch):
    calls = []

    def fake_once(url, payload, timeout):
        calls.append(payload)
        cross_deck._raise_for(_relay_404())

    monkeypatch.setattr(cross_deck, "_post_json_once", fake_once)
    with pytest.raises(RuntimeError, match="v0.4"):
        cross_deck._post_json("https://script.google.com/x/exec", {"op": "copy"}, retry=False)
    assert len(calls) == 1


def test_404_from_exec_itself_is_not_a_relay_error():
    with pytest.raises(RuntimeError, match="appscript HTTP 404"):
        cross_deck._raise_for(_http_error("https://script.google.com/macros/s/old/exec", 404))


def test_copy_sends_request_id_and_retries_only_on_v04(monkeypatch):
    seen = {}

    def fake_post(url, payload, timeout=180.0, retry=True):
        seen["payload"], seen["retry"] = payload, retry
        return {"newSlideId": "s1", "dstIndex": 0}

    monkeypatch.setattr(cross_deck, "_post_json", fake_post)
    monkeypatch.setattr(cross_deck, "_appscript_url", lambda: "https://script.google.com/x/exec")
    for version, expected in (("0.3", False), ("0.4", True), ("1.0", True)):
        cross_deck._SCRIPT_VERSION.clear()
        monkeypatch.setattr(cross_deck, "cross_deck_ping", lambda: {"ok": True, "version": version})
        cross_deck.copy_slide_cross_deck("a", 1, "b")
        assert len(seen["payload"]["requestId"]) == 32
        assert seen["retry"] is expected, version
