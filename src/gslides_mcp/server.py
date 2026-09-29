"""Entry point. Imports tools (which registers them) and runs the MCP server.

stdio (default): one user, token.json on disk, launched by the MCP client.

HTTP (``GSLIDES_MCP_TRANSPORT=http``): one hosted server for a whole team. The
MCP client only needs the URL; the server runs the OAuth flow itself and each
user signs in with their own Google account. Settings (environment):

    GSLIDES_MCP_BASE_URL       public URL, e.g. https://slides.example.com
    GOOGLE_CLIENT_ID           OAuth client of type "Web application", whose
    GOOGLE_CLIENT_SECRET       redirect URI is <base url>/auth/callback
    GSLIDES_MCP_GOOGLE_DOMAIN  optional: preselect accounts of this Workspace domain
    GSLIDES_MCP_REDIRECT_HOSTS hosts an MCP client may register an https redirect
                               on (default claude.ai,claude.com; loopback always)
    GSLIDES_MCP_MAX_IN_FLIGHT  tool calls served at once across everyone (default 8)
    GSLIDES_MCP_HOST / _PORT   bind address (default 0.0.0.0:8000)
    FASTMCP_HOME               where sign-in sessions are kept (encrypted); a volume
"""

import asyncio
import os
import sys

from fastmcp.server.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .app import mcp
from . import tools  # noqa: F401  — side-effect: registers all @mcp.tool() handlers
from .auth import SCOPES, remote_mode


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"gslides-mcp: {name} is required when GSLIDES_MCP_TRANSPORT=http")
    return value


def redirect_patterns() -> list[str]:
    """Redirect URIs a client may register: Claude's hosts and loopback only.

    Registration is open (MCP clients need it), so without this list anybody
    could register their own redirect and collect a colleague's sign-in.
    """
    raw = os.environ.get("GSLIDES_MCP_REDIRECT_HOSTS", "claude.ai,claude.com")
    hosts = [h.strip().lower() for h in raw.split(",") if h.strip()]
    return [f"https://{h}/*" for h in hosts] + ["http://localhost:*", "http://127.0.0.1:*"]


class MaxInFlight(Middleware):
    """At most ``limit`` tool calls at once across everyone; the rest wait.

    Each call can hold large Google responses and thumbnails in memory, so this
    is what bounds the shared server's memory.
    """

    def __init__(self, limit: int):
        self._sem = asyncio.Semaphore(limit)

    async def on_call_tool(self, context, call_next):
        async with self._sem:
            return await call_next(context)


def google_auth():
    """OAuth proxy: Claude registers with this server, users sign in with Google."""
    from fastmcp.server.auth.providers.google import GoogleProvider

    extra = {}
    domain = os.environ.get("GSLIDES_MCP_GOOGLE_DOMAIN", "").strip()
    if domain:
        extra["hd"] = domain
    client_id = _require("GOOGLE_CLIENT_ID")
    client_secret = _require("GOOGLE_CLIENT_SECRET")
    # A value pasted into a UI that turns it into a link ("http://<id>/")
    # otherwise only shows up as Google's "OAuth client was not found".
    if "://" in client_id or not client_id.endswith(".apps.googleusercontent.com"):
        sys.exit("gslides-mcp: GOOGLE_CLIENT_ID must be the bare <n>-<id>.apps.googleusercontent.com")
    if "://" in client_secret or client_secret.endswith("/"):
        sys.exit("gslides-mcp: GOOGLE_CLIENT_SECRET looks like a URL; paste the secret alone")
    return GoogleProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=_require("GSLIDES_MCP_BASE_URL").rstrip("/"),
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            *SCOPES,
            # Not used by the tools: the hosted Apps Script (copy for gslides,
            # chart_png for google-sheets-mcp) lists it, and scripts.run wants
            # the caller's token to cover every scope of the script.
            "https://www.googleapis.com/auth/spreadsheets",
        ],
        extra_authorize_params=extra or None,
        allowed_client_redirect_uris=redirect_patterns(),
    )


# The component catalogue is shared by everyone on the hosted server, so it is
# edited locally only (stdio); the hosted server serves what is on its volume.
LOCAL_ONLY_TOOLS = ("save_component", "delete_component")


def hide_local_only_tools() -> None:
    for name in LOCAL_ONLY_TOOLS:
        mcp.local_provider.remove_tool(name)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def main() -> None:
    if not remote_mode():
        mcp.run()
        return
    mcp.auth = google_auth()
    hide_local_only_tools()
    mcp.add_middleware(MaxInFlight(max(1, int(os.environ.get("GSLIDES_MCP_MAX_IN_FLIGHT", "8")))))
    mcp.run(
        transport="http",
        host=os.environ.get("GSLIDES_MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("GSLIDES_MCP_PORT", "8000")),
        path="/mcp",
    )


if __name__ == "__main__":
    main()
