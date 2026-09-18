"""The API client is built from the server's credentials (granted scopes only), never from
gslides-api's own token loader, whose wider scope list breaks the first refresh."""

from gslides_mcp import auth


class _Creds:
    scopes = list(auth.SCOPES)
    valid = True


class _FakeClient:
    instances: list = []

    def __init__(self, auto_flush=True):
        self.set_with = None
        self.initialized_from = None
        _FakeClient.instances.append(self)

    def set_credentials(self, creds):
        self.set_with = creds

    def initialize_credentials(self, directory):
        self.initialized_from = directory


def test_client_injects_our_credentials_and_never_reloads_token_json(monkeypatch, tmp_path):
    creds = _Creds()
    monkeypatch.setenv("GSLIDES_MCP_CRED_DIR", str(tmp_path))
    monkeypatch.setattr(auth, "_load_or_refresh_creds", lambda d: creds)
    monkeypatch.setattr(auth, "GoogleAPIClient", _FakeClient)
    auth.client.cache_clear()
    try:
        c = auth.client()
        assert c.set_with is creds
        assert c.initialized_from is None  # gslides-api's loader would add the spreadsheets scope
        assert auth.client() is c  # cached: one OAuth + service build per process
    finally:
        auth.client.cache_clear()
