"""The API client is built from the server's credentials (granted scopes only), never from
gslides-api's own token loader, whose wider scope list breaks the first refresh."""

import threading

import pytest

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


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setattr(auth, "GoogleAPIClient", _FakeClient)
    monkeypatch.setattr(auth, "_tls", threading.local())
    auth._local_creds.cache_clear()
    yield
    auth._local_creds.cache_clear()


def test_client_injects_our_credentials_and_never_reloads_token_json(monkeypatch, tmp_path, fresh):
    creds = _Creds()
    monkeypatch.delenv("GSLIDES_MCP_TRANSPORT", raising=False)
    monkeypatch.setenv("GSLIDES_MCP_CRED_DIR", str(tmp_path))
    monkeypatch.setattr(auth, "_load_or_refresh_creds", lambda d: creds)
    c = auth.client()
    assert c.set_with is creds
    assert c.initialized_from is None  # gslides-api's loader would add the spreadsheets scope
    assert auth.client() is c  # cached: one OAuth + service build per thread


def test_each_thread_gets_its_own_client(monkeypatch, tmp_path, fresh):
    monkeypatch.delenv("GSLIDES_MCP_TRANSPORT", raising=False)
    monkeypatch.setenv("GSLIDES_MCP_CRED_DIR", str(tmp_path))
    loads = []
    monkeypatch.setattr(auth, "_load_or_refresh_creds", lambda d: loads.append(d) or _Creds())
    main = auth.client()
    other = []
    t = threading.Thread(target=lambda: other.append(auth.client()))
    t.start()
    t.join()
    assert other[0] is not main  # httplib2 is not thread-safe
    assert other[0].set_with is main.set_with  # but token.json is read once
    assert len(loads) == 1


def test_remote_client_uses_the_request_users_token(monkeypatch, fresh):
    monkeypatch.setenv("GSLIDES_MCP_TRANSPORT", "http")
    monkeypatch.setattr(auth, "_load_or_refresh_creds", lambda d: pytest.fail("read token.json"))
    monkeypatch.setattr(auth, "request_token", lambda: "user-a-token")
    a = auth.client()
    assert a.set_with.token == "user-a-token"
    monkeypatch.setattr(auth, "request_token", lambda: "user-b-token")
    b = auth.client()
    assert b is not a and b.set_with.token == "user-b-token"


def test_remote_client_without_a_user_is_refused(monkeypatch, fresh):
    monkeypatch.setenv("GSLIDES_MCP_TRANSPORT", "http")
    monkeypatch.setattr(auth, "_load_or_refresh_creds", lambda d: pytest.fail("read token.json"))
    monkeypatch.setattr(auth, "request_token", lambda: None)
    with pytest.raises(RuntimeError, match="no signed-in Google user"):
        auth.client()
