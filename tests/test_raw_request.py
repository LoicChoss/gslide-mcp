"""raw_request: GET/POST under https://slides.googleapis.com/v1/presentations/<id>, nothing else."""

import json

import pytest

from gslides_mcp.tools import raw

BASE = "https://slides.googleapis.com/v1/presentations/PRES1"


def test_get_builds_url_under_the_presentation(fake_slides):
    fake_slides._http.body = b'{"pageType": "LAYOUT"}'
    out = raw.raw_request("PRES1", "GET", "/pages/p4")
    call = fake_slides._http.calls[0]
    assert call["uri"] == f"{BASE}/pages/p4"
    assert call["method"] == "GET" and call["body"] is None
    assert out == {"status": 200, "response": {"pageType": "LAYOUT"}}


def test_post_sends_json_body(fake_slides):
    fake_slides._http.body = b'{"replies": [{}]}'
    body = {"requests": [{"deleteObject": {"objectId": "x"}}]}
    out = raw.raw_request("https://docs.google.com/presentation/d/PRES1/edit", "POST", ":batchUpdate", body=body)
    call = fake_slides._http.calls[0]
    assert call["uri"] == f"{BASE}:batchUpdate"
    assert call["method"] == "POST"
    assert json.loads(call["body"]) == body
    assert call["headers"]["Content-Type"] == "application/json"
    assert out["response"] == {"replies": [{}]}


def test_empty_path_and_query_string(fake_slides):
    raw.raw_request("PRES1", "GET", "")
    raw.raw_request("PRES1", "get", "?fields=pageSize")
    assert [c["uri"] for c in fake_slides._http.calls] == [BASE, f"{BASE}?fields=pageSize"]


@pytest.mark.parametrize("path", [
    "https://evil.example/x",
    "//evil.example/x",
    "http",
    "/pages/x@evil.example",
    "/../../drive/v3/files",
    "pages/p4",          # must start with '/', ':' or '?'
    "/pages/p4\n",
    "/pages/p 4",
])
def test_rejects_paths_that_could_leave_the_presentation(fake_slides, path):
    with pytest.raises(ValueError):
        raw.raw_request("PRES1", "GET", path)
    assert fake_slides._http.calls == []


def test_rejects_drive_and_other_methods(fake_slides):
    with pytest.raises(ValueError, match="drive"):
        raw.raw_request("PRES1", "GET", "/drive/v3/files")
    with pytest.raises(ValueError, match="GET or POST"):
        raw.raw_request("PRES1", "DELETE", "/pages/p4")
    with pytest.raises(ValueError, match="body"):
        raw.raw_request("PRES1", "GET", "/pages/p4", body={"x": 1})
    assert fake_slides._http.calls == []


def test_non_2xx_raises_with_google_message(fake_slides):
    fake_slides._http.status = 403
    fake_slides._http.body = b'{"error": {"message": "The caller does not have permission"}}'
    with pytest.raises(RuntimeError, match="403.*does not have permission"):
        raw.raw_request("PRES1", "GET", "/pages/p4")


def test_empty_response_body(fake_slides):
    fake_slides._http.body = b""
    assert raw.raw_request("PRES1", "GET", "")["response"] == {}
