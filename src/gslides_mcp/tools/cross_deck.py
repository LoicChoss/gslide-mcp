"""Cross-deck slide copy via a deployed Apps Script web app.

The Slides REST API has NO cross-presentation copy. Apps Script does
(``SlidesApp.appendSlide(slide)``) — it carries layout, theme, fonts,
images, styles. We expose that as an HTTP endpoint and call it here.

Setup is one-time and manual: see ``appscript/cross_deck_copy.gs`` for the
deployment steps. The MCP reads the deployed URL from either:

    - env var ``GSLIDES_MCP_APPSCRIPT_URL``
    - file ``~/.gslides-mcp/appscript_url`` (one-line text)

If neither is set, the tool raises with deployment instructions.

Hosted (``GSLIDES_MCP_TRANSPORT=http``), the web app is never used: it runs as
whoever deployed it, so every user would copy with that person's rights. The
script is deployed as an API executable instead (``GSLIDES_MCP_APPSCRIPT_ID``)
and called through ``scripts.run`` with the signed-in user's token.
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import certifi

from ..app import ADDITIVE, READ_ONLY, mcp
from ..auth import access_token, remote_mode
from ..util import parse_pres_id


_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


_APPSCRIPT_URL_FILE = Path.home() / ".gslides-mcp" / "appscript_url"

# Apps Script web apps always serve from this host. We refuse to send an OAuth
# bearer token to anything else, even if the URL file or env var was mis-set.
_APPSCRIPT_HOST = "script.google.com"


# Every POST to an Apps Script /exec URL answers 302 to this host, where the
# real (JSON) response is served. That single hop is the ONLY redirect we
# follow, and we follow it the way browsers do: as a bare GET with no body and
# no Authorization header, so the bearer token never leaves script.google.com.
_ECHO_HOST = "script.googleusercontent.com"

_USER_AGENT = "gslides-mcp/0.1"


class _EchoOnlyRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 1

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):  # noqa: ARG002
        parts = urllib.parse.urlparse(newurl)
        if parts.scheme != "https" or parts.hostname != _ECHO_HOST:
            return None  # surfaces to the caller as HTTPError(code)
        return urllib.request.Request(
            newurl, headers={"User-Agent": _USER_AGENT}, method="GET"
        )


_OPENER = urllib.request.build_opener(
    _EchoOnlyRedirect(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def _appscript_id() -> str | None:
    """Script ID of the API-executable deployment, if configured."""
    sid = os.environ.get("GSLIDES_MCP_APPSCRIPT_ID", "").strip()
    return sid or None


def _appscript_url() -> str:
    """Resolve the deployed web-app URL or raise with setup help."""
    if remote_mode():
        raise RuntimeError(
            "cross-deck copy on the hosted server needs the Apps Script deployed "
            "as an API executable: set GSLIDES_MCP_APPSCRIPT_ID (see "
            "appscript/cross_deck_copy.gs)."
        )
    url = os.environ.get("GSLIDES_MCP_APPSCRIPT_URL")
    if url:
        return url.strip()
    if _APPSCRIPT_URL_FILE.exists():
        return _APPSCRIPT_URL_FILE.read_text().strip()
    raise RuntimeError(
        "cross-deck copy requires a deployed Apps Script web app. "
        "See appscript/cross_deck_copy.gs for setup steps. "
        f"Once deployed, save the URL to {_APPSCRIPT_URL_FILE} or "
        "set GSLIDES_MCP_APPSCRIPT_URL=<url>."
    )


# Google's response relay (the echo hop) intermittently serves a Drive
# "unable to open the file at this time" 404 for a result the script already
# produced. The user_content_key is single-use, so the only recovery is to
# replay the POST — which is safe for ping, and for copy only once the
# deployed script deduplicates by requestId (v0.4+).
_RELAY_ATTEMPTS = 4  # 1 initial + 3 replays, backoff 1s/2s/4s

_REPLAY_HINT = (
    "Google's response relay dropped the result (transient 404 on "
    "script.googleusercontent.com). Redeploy appscript/cross_deck_copy.gs "
    "v0.4 so the MCP can replay copies safely; until then, re-run the call."
)

# Deployed script version per URL, learned lazily via ping. Gates copy replay.
_SCRIPT_VERSION: dict[str, tuple[int, ...]] = {}


class _RelayError(RuntimeError):
    """The echo hop 404'd after the script ran; the response is lost."""


def _raise_for(e: urllib.error.HTTPError) -> None:
    """Translate an HTTPError from either hop into a RuntimeError."""
    # Truncate aggressively — Apps Script error bodies can be large and
    # we don't want any echoed request headers ending up in user output.
    msg = e.read().decode("utf-8", errors="replace")
    if e.code == 404 and urllib.parse.urlparse(e.url).hostname == _ECHO_HOST:
        raise _RelayError("appscript relay 404") from None
    if 300 <= e.code < 400:
        # A refused redirect: name the destination host so a private
        # deployment (accounts.google.com) or a /dev URL is obvious.
        target = urllib.parse.urlparse(e.headers.get("Location", "")).hostname
        msg = f"refused redirect to {target or '<no Location>'}"
    raise RuntimeError(f"appscript HTTP {e.code}: {msg[:500]}") from None


def _post_json(
    url: str, payload: dict, timeout: float = 180.0, retry: bool = True
) -> dict:
    """POST to the Apps Script web app, replaying on relay 404s if ``retry``.

    ``retry=False`` is for calls that would have a side effect twice if the
    script has already run — i.e. copy against a pre-0.4 script.
    """
    for attempt in range(1, _RELAY_ATTEMPTS + 1):
        try:
            return _post_json_once(url, payload, timeout)
        except _RelayError:
            if not retry:
                raise RuntimeError(_REPLAY_HINT) from None
            if attempt == _RELAY_ATTEMPTS:
                raise RuntimeError(
                    f"appscript relay 404 on {attempt} consecutive attempts; "
                    "Google's response relay is degraded — retry later."
                ) from None
            time.sleep(2 ** (attempt - 1))
    raise AssertionError("unreachable")


def _post_json_once(url: str, payload: dict, timeout: float) -> dict:
    """One POST to the Apps Script web app; returns parsed JSON.

    Security: the OAuth bearer token is attached ONLY when the destination
    host is script.google.com. A misconfigured ``GSLIDES_MCP_APPSCRIPT_URL``
    (typo, hostile takeover of the URL file, swap to a dev tunnel) would
    otherwise leak a usable Google access token to an arbitrary endpoint.
    Apps Script always 302s a POST to script.googleusercontent.com; that hop
    is followed as a token-less GET (see ``_EchoOnlyRedirect``). Any other
    redirect is refused so the token can't be replayed to another host.
    """
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }
    host = urllib.parse.urlparse(url).hostname or ""
    if host == _APPSCRIPT_HOST:
        try:
            token = _maybe_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        except Exception:
            pass
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        _raise_for(e)
    raise AssertionError("unreachable")


def _script_supports_replay(url: str) -> bool:
    """True if the deployed script dedupes copies by requestId (v0.4+).

    One ping per server lifetime and URL; ping itself is replay-safe.
    """
    if url not in _SCRIPT_VERSION:
        raw = str(cross_deck_ping().get("version", "0"))
        _SCRIPT_VERSION[url] = tuple(int(p) for p in raw.split(".") if p.isdigit())
    return _SCRIPT_VERSION[url] >= (0, 4)


def _maybe_token() -> str | None:
    """Fresh OAuth access token of the caller for outbound Apps Script calls."""
    try:
        return access_token()
    except Exception:
        return None


_SCRIPTS_RUN = "https://script.googleapis.com/v1/scripts/{}:run"


def _run_script(script_id: str, payload: dict, timeout: float = 180.0) -> dict:
    """Call ``api(payload)`` through scripts.run, as the calling user.

    No relay hop here: the result comes back on the same response, so a copy
    is never replayed. Errors raised in the script arrive as ``error`` with
    the message in ``details[0].errorMessage``.
    """
    token = access_token()
    if not token:
        raise RuntimeError("cross-deck copy: no Google token for this request")
    body = json.dumps({"function": "api", "parameters": [payload]}).encode("utf-8")
    req = urllib.request.Request(
        _SCRIPTS_RUN.format(urllib.parse.quote(script_id, safe="")),
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"scripts.run HTTP {e.code}: {msg[:500]}") from None
    if "error" in out:
        details = (out["error"].get("details") or [{}])[0]
        raise RuntimeError(f"appscript error: {details.get('errorMessage') or out['error']}")
    return out.get("response", {}).get("result") or {}


@mcp.tool(annotations=ADDITIVE)
def copy_slide_cross_deck(
    src_presentation: str,
    src_slide: str,
    dst_presentation: str,
    insertion_index: int | None = None,
) -> dict:
    """Copy ONE slide from src to dst, preserving layout/theme/fonts/styles.

    Routes through a deployed Apps Script web app (``SlidesApp.appendSlide``)
    because the Slides REST API has no cross-presentation copy. Setup is
    one-time and manual — see ``appscript/cross_deck_copy.gs`` and the
    error message thrown when the URL isn't configured.

    Args:
        src_presentation: source deck ID or full URL.
        src_slide: 1-based index OR objectId of the slide to copy.
        dst_presentation: destination deck ID or full URL.
        insertion_index: optional 0-based insertion index in dst (default
            appends to the end).

    Returns: ``{newSlideId, dstIndex}`` — the new slide's objectId in dst,
    and its 0-based final position. Use the objectId to address it in
    follow-up replace_text / write_text_markdown calls.

    First call after server start: ~2-4s (Apps Script cold-start). Steady
    state: ~700ms-1.5s per slide.
    """
    payload: dict = {
        "op": "copy",
        "srcId": parse_pres_id(src_presentation),
        "dstId": parse_pres_id(dst_presentation),
        "srcSlide": src_slide,
    }
    if insertion_index is not None:
        payload["insertionIndex"] = insertion_index
    # requestId lets a v0.4+ script answer a replayed POST from cache instead
    # of appending the slide a second time (see _RELAY_ATTEMPTS).
    payload["requestId"] = uuid.uuid4().hex
    script_id = _appscript_id()
    if script_id:
        return _run_script(script_id, payload)
    url = _appscript_url()
    result = _post_json(url, payload, retry=_script_supports_replay(url))
    if "error" in result:
        raise RuntimeError(f"appscript error: {result['error']}")
    return result


@mcp.tool(annotations=READ_ONLY)
def cross_deck_ping() -> dict:
    """Health-check the deployed Apps Script web app.

    Verifies the URL is configured, reachable, and the script is the right
    version. Use this to debug deployment before relying on
    ``copy_slide_cross_deck``.

    Returns: ``{ok: True, version: "0.5", url: "..."}`` on success
    (``script_id`` instead of ``url`` for an API-executable deployment).
    """
    script_id = _appscript_id()
    if script_id:
        return {"script_id": script_id, **_run_script(script_id, {"op": "ping"})}
    url = _appscript_url()
    result = _post_json(url, {"op": "ping"})
    return {"url": url, **result}
