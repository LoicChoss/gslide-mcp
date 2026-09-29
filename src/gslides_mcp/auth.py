"""Auth + persistent client.

The whole MCP runs in one process, so OAuth + service Resources load ONCE at
startup and every tool reuses them. This is the single biggest win over the
CLI-script architecture (which cold-started Python+OAuth on every call).

On first run (no token.json), an interactive OAuth browser flow is launched.
The resulting token is saved to <cred_dir>/token.json (mode 0o600) and reused
on subsequent starts (with automatic refresh when expired).

Over HTTP (``GSLIDES_MCP_TRANSPORT=http``) there is no token.json: each request
carries the signed-in user's Google token and the client is built from it.

All user-facing messages go to sys.stderr — stdout is the JSON-RPC channel.
"""

from __future__ import annotations

import functools
import os
import sys
import threading
from collections import OrderedDict
from pathlib import Path

from gslides_api.client import GoogleAPIClient


def _write_token_atomic(token_path: Path, payload: str) -> None:
    """Write ``payload`` to ``token_path`` at mode 0o600 atomically.

    Plain ``write_text`` + ``chmod`` leaves a brief window where the file
    exists at the default umask (typically 0o644). On a shared host that's
    enough for a co-tenant to read the OAuth token. ``os.open`` with explicit
    0o600 mode closes that window.

    ``O_CREAT`` only sets the mode when the file is being created, so we
    also re-chmod in case ``token.json`` already existed at a permissive
    mode from a previous run.
    """
    fd = os.open(str(token_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(payload)
    os.chmod(str(token_path), 0o600)


SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_CRED_DIR = Path.home() / ".gslides-mcp" / "creds"

_SETUP_MESSAGE = """\
gslides-mcp: missing credentials.json at {creds_path}

To authenticate this MCP server you need an OAuth 2.0 Client ID:

  1. Open https://console.cloud.google.com/
  2. Create (or select) a project and enable the Google Slides API and Drive API.
  3. Go to "APIs & Services > Credentials" and click "Create Credentials >
     OAuth client ID".
  4. Choose Application type: Desktop app.
  5. Download the JSON file and save it to:
       {creds_path}
  6. Re-run the MCP server — a browser window will open to complete sign-in.

See docs/oauth-setup.md for step-by-step screenshots and troubleshooting.
"""


def cred_dir() -> Path:
    """Return the directory holding token.json + credentials.json.

    Override with the GSLIDES_MCP_CRED_DIR environment variable.
    The directory is created on first access if it does not exist.
    """
    d = Path(os.environ.get("GSLIDES_MCP_CRED_DIR", DEFAULT_CRED_DIR))
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


def _run_oauth_flow(creds_path: Path, token_path: Path):
    """Run the InstalledAppFlow and save the resulting token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    print(
        "gslides-mcp: opening browser for Google OAuth — "
        "follow the prompts then return here.",
        file=sys.stderr,
    )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token_atomic(token_path, creds.to_json())
    print(f"gslides-mcp: token saved to {token_path}", file=sys.stderr)
    return creds


def _load_or_refresh_creds(cred_directory: Path):
    """Return valid google.oauth2 Credentials, running OAuth if necessary."""
    import google.auth.transport.requests
    import google.oauth2.credentials

    token_path = cred_directory / "token.json"
    creds_path = cred_directory / "credentials.json"

    creds = None

    # --- Try to load an existing token ---
    if token_path.exists():
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )
        except Exception as exc:
            print(
                f"gslides-mcp: could not parse {token_path} ({exc}); re-authenticating.",
                file=sys.stderr,
            )
            creds = None

    # --- Refresh if expired ---
    if creds is not None and creds.expired and creds.refresh_token:
        try:
            creds.refresh(google.auth.transport.requests.Request())
            _write_token_atomic(token_path, creds.to_json())
            print("gslides-mcp: OAuth token refreshed.", file=sys.stderr)
        except Exception:
            creds = None  # fall through to full re-auth

    # --- Validate scopes — a token issued for a narrower scope set will
    # refresh successfully but fail at API call time. Force re-auth instead.
    if creds is not None and not all(s in (creds.scopes or []) for s in SCOPES):
        print(
            "gslides-mcp: token scopes do not cover required scopes; re-authenticating.",
            file=sys.stderr,
        )
        creds = None

    # --- Still not valid — run the full flow ---
    if creds is None or not creds.valid:
        if not creds_path.exists():
            raise RuntimeError(
                _SETUP_MESSAGE.format(creds_path=creds_path)
            )
        creds = _run_oauth_flow(creds_path, token_path)

    return creds


def remote_mode() -> bool:
    """True when the server runs over HTTP for several users (``GSLIDES_MCP_TRANSPORT=http``)."""
    return os.environ.get("GSLIDES_MCP_TRANSPORT", "stdio").lower() == "http"


def request_token() -> str | None:
    """Google access token of the user behind the current HTTP request, if any.

    The OAuth proxy swaps the token Claude holds for the user's upstream Google
    token (refreshing it when needed), so this is always a live Google token.
    """
    from fastmcp.server.dependencies import get_access_token

    tok = get_access_token()
    return tok.token if tok is not None else None


# googleapiclient Resources sit on httplib2, which is not thread-safe, and
# FastMCP runs sync tools in a thread pool. So each worker thread keeps its own
# clients, keyed by the credentials they carry ("local", or a user's token).
_tls = threading.local()
_PER_THREAD_MAX = 8


def _thread_client(key: str, make_creds) -> GoogleAPIClient:
    clients: OrderedDict[str, GoogleAPIClient] = getattr(_tls, "clients", None)
    if clients is None:
        clients = _tls.clients = OrderedDict()
    c = clients.get(key)
    if c is not None:
        clients.move_to_end(key)
        return c
    # Build the services from OUR credentials object. gslides-api's own
    # initialize_credentials() would reload token.json with its wider scope
    # list (it adds spreadsheets); the first refresh then trips Google's
    # "invalid_scope" — typically an hour after the server started, once the
    # access token issued at startup expires. Passing the credentials in
    # keeps every later refresh on the scopes the token was granted.
    c = GoogleAPIClient(auto_flush=True)
    c.set_credentials(make_creds())
    clients[key] = c
    while len(clients) > _PER_THREAD_MAX:  # user tokens rotate hourly
        clients.popitem(last=False)
    return c


def client() -> GoogleAPIClient:
    """API client for the caller: the signed-in user over HTTP, token.json over stdio.

    Over HTTP there is no fallback to a token on disk: a request without a user
    token is refused, so one person can never act with another's credentials.
    """
    if remote_mode():
        import google.oauth2.credentials

        token = request_token()
        if not token:
            raise RuntimeError("gslides-mcp: no signed-in Google user on this request")
        return _thread_client(
            token, lambda: google.oauth2.credentials.Credentials(token=token, scopes=SCOPES)
        )
    return _thread_client("local", _local_creds)


def access_token() -> str | None:
    """Live Google access token of the caller (for raw HTTPS calls outside the API client)."""
    if remote_mode():
        return request_token()
    import google.auth.transport.requests

    creds = _local_creds()
    with _LOCAL_REFRESH_LOCK:
        if not creds.valid:
            creds.refresh(google.auth.transport.requests.Request())
    return creds.token


_LOCAL_REFRESH_LOCK = threading.Lock()


@functools.lru_cache(maxsize=1)
def _local_creds():
    """token.json credentials, loaded (and refreshed or OAuth'd) once per process."""
    return _load_or_refresh_creds(cred_dir())


def slide_service():
    """Shortcut: googleapiclient discovery Resource for slides v1."""
    return client().slide_service


def drive_service():
    """Shortcut: googleapiclient discovery Resource for drive v3."""
    return client().drive_service


def sheets_service():
    """Shortcut: googleapiclient discovery Resource for sheets v4 (read-only use; the drive scope covers it)."""
    return client().sheet_service
