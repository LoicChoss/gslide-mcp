"""raw_request: GET/POST any Slides API endpoint under the presentation.

Escape hatch for endpoints no typed tool covers. The path is appended
verbatim to ``https://slides.googleapis.com/v1/presentations/<id>`` and
nothing that could point elsewhere is accepted: no scheme, no host, no
``//``, no ``@``, no ``..``, no whitespace. The OAuth token therefore never
leaves slides.googleapis.com. Drive endpoints are refused — they have
dedicated tools (clone_deck, export_pres, insert_image_local,
manage_comments).
"""

from __future__ import annotations

import json
import re

from ..app import DESTRUCTIVE, mcp
from ..auth import slide_service
from ..util import parse_pres_id

_BASE = "https://slides.googleapis.com/v1/presentations/"

# Path characters we allow after the presentation id: URL-safe, no '@',
# no whitespace, no backslash.
_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./:?=,&%()+*]*$")


def _safe_path(path: str) -> str:
    if path == "":
        return ""
    if path[0] not in "/:?":
        raise ValueError(
            f"path {path!r} must be empty or start with '/', ':' or '?' — it is "
            "appended to https://slides.googleapis.com/v1/presentations/<id>"
        )
    lowered = path.lower()
    if (
        "//" in path or "@" in path or ".." in path
        or "http" in lowered or not _PATH_RE.fullmatch(path)
    ):
        raise ValueError(
            f"unsafe path {path!r}: no scheme, host, '//', '@', '..' or whitespace allowed"
        )
    if "drive" in lowered:
        raise ValueError(
            "drive endpoints are not reachable from raw_request; use clone_deck, "
            "export_pres, insert_image_local or manage_comments"
        )
    return path


@mcp.tool(annotations=DESTRUCTIVE)
def raw_request(presentation: str, method: str, path: str, body: dict | None = None) -> dict:
    """GET or POST a Slides API path under this presentation.

    Args:
        method: ``GET`` or ``POST``.
        path: appended to ``.../v1/presentations/<id>``. Examples: ``""``
            (the presentation), ``"/pages/p4"``, ``":batchUpdate"``,
            ``"?fields=pageSize"``. Absolute URLs, hosts and Drive paths are
            refused.
        body: JSON body, POST only.

    Returns: ``{status, response}`` — ``response`` is the parsed JSON body.
    Non-2xx answers raise with Google's error message. POST is potentially
    destructive (``:batchUpdate`` can delete anything).

    Example: ``raw_request(deck, "GET", "/pages/p4?fields=pageElements(objectId)")``
    """
    m = method.upper()
    if m not in ("GET", "POST"):
        raise ValueError(f"method must be GET or POST, got {method!r}")
    if body is not None and m != "POST":
        raise ValueError("body is only allowed with POST")
    pid = parse_pres_id(presentation)
    url = _BASE + pid + _safe_path(path)

    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if m == "POST" else {}
    resp, content = slide_service()._http.request(url, method=m, body=data, headers=headers)
    status = int(resp.status)
    text = content.decode("utf-8", errors="replace") if content else ""
    try:
        parsed = json.loads(text) if text.strip() else {}
    except ValueError:
        parsed = {"raw": text[:2000]}
    if not 200 <= status < 300:
        message = parsed.get("error", {}).get("message") if isinstance(parsed, dict) else None
        raise RuntimeError(f"Slides API HTTP {status} on {m} {path or '/'}: {message or text[:500]}")
    return {"status": status, "response": parsed}
