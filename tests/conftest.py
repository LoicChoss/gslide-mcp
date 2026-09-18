"""Shared test doubles: an in-memory Slides/Drive "service" that records every
batchUpdate and answers reads from ``tests/fixtures/presentation.json``.

The fakes mimic the googleapiclient discovery surface the tools actually use
(``svc.presentations().get(...).execute()`` etc.) — nothing more.
"""

from __future__ import annotations

import copy
import importlib
import json
import pkgutil
from pathlib import Path

import httplib2
import pytest
from googleapiclient.errors import HttpError

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_http_error(status: int, message: str = "boom") -> HttpError:
    body = json.dumps({"error": {"code": status, "message": message}}).encode()
    return HttpError(httplib2.Response({"status": status}), body)


class _Exec:
    def __init__(self, result=None, error: Exception | None = None):
        self._result = result
        self._error = error

    def execute(self, num_retries=0):
        if self._error is not None:
            raise self._error
        return copy.deepcopy(self._result)


# --- Slides ---------------------------------------------------------------

_CREATE_REPLIES = {
    "createSlide": "gen_slide",
    "createShape": "gen_shape",
    "createTable": "gen_table",
    "createImage": "gen_image",
    "duplicateObject": "gen_dup",
}


class FakeHttp:
    """Stand-in for the discovery Resource's authorized ``_http`` transport."""

    def __init__(self):
        self.calls: list[dict] = []
        self.status = 200
        self.body = b'{"ok": true}'

    def request(self, uri, method="GET", body=None, headers=None, **_):
        self.calls.append({"uri": uri, "method": method, "body": body, "headers": headers})
        return httplib2.Response({"status": self.status}), self.body


class FakeSlides:
    """Records batches; ``fail_next_batch`` makes the next batchUpdate raise."""

    def __init__(self, pres: dict):
        self.pres = pres
        self._http = FakeHttp()
        self.batches: list[list[dict]] = []
        self.failed_batches: list[list[dict]] = []
        self.get_calls: list[dict] = []
        self.thumbnail_calls: list[dict] = []
        self.fail_next_batch: Exception | None = None
        self.fail_at: int | None = None  # 1-based ordinal of the batch to fail
        self._seq = 0

    def presentations(self):
        return _FakePresentations(self)

    def _reply(self, req: dict) -> dict:
        (kind, payload), = req.items()
        if kind not in _CREATE_REPLIES:
            return {}
        self._seq += 1
        oid = payload.get("objectId") or f"{_CREATE_REPLIES[kind]}_{self._seq}"
        return {kind: {"objectId": oid}}

    def _apply(self, req: dict, reply: dict) -> None:
        """Mirror createSlide / deleteObject on the in-memory deck so later
        reads (pages.get, getThumbnail) see the slides a tool just made."""
        if "createSlide" in req:
            p = req["createSlide"]
            oid = reply["createSlide"]["objectId"]
            slide = {
                "objectId": oid, "pageType": "SLIDE", "pageElements": [],
                "slideProperties": {
                    "layoutObjectId": p.get("slideLayoutReference", {}).get("layoutId"),
                    "notesPage": {
                        "objectId": f"{oid}_notespage", "pageType": "NOTES",
                        "notesProperties": {"speakerNotesObjectId": f"{oid}_notes"},
                        "pageElements": [],
                    },
                },
            }
            slides = self.pres.setdefault("slides", [])
            idx = p.get("insertionIndex")
            slides.insert(len(slides) if idx is None else idx, slide)
        elif "deleteObject" in req:
            oid = req["deleteObject"]["objectId"]
            self.pres["slides"] = [s for s in self.pres.get("slides", []) if s["objectId"] != oid]

    def find_page(self, page_id: str) -> dict | None:
        for key in ("slides", "layouts", "masters"):
            for page in self.pres.get(key, []):
                if page["objectId"] == page_id:
                    return page
                notes = page.get("slideProperties", {}).get("notesPage")
                if notes and notes.get("objectId") == page_id:
                    return notes
        return None


class _FakePresentations:
    def __init__(self, svc: FakeSlides):
        self.svc = svc

    def get(self, presentationId, fields=None):
        self.svc.get_calls.append({"presentationId": presentationId, "fields": fields})
        return _Exec(self.svc.pres)

    def batchUpdate(self, presentationId, body):
        reqs = body["requests"]
        ordinal = len(self.svc.batches) + len(self.svc.failed_batches) + 1
        if self.svc.fail_next_batch is not None or ordinal == self.svc.fail_at:
            err = self.svc.fail_next_batch or make_http_error(500, f"batch #{ordinal} failed")
            self.svc.fail_next_batch = None
            self.svc.failed_batches.append(reqs)
            return _Exec(error=err)
        self.svc.batches.append(reqs)
        replies = [self.svc._reply(r) for r in reqs]
        for req, reply in zip(reqs, replies):
            self.svc._apply(req, reply)
        return _Exec({"replies": replies})

    def pages(self):
        return _FakePages(self.svc)


class _FakePages:
    def __init__(self, svc: FakeSlides):
        self.svc = svc

    def get(self, presentationId, pageObjectId):
        page = self.svc.find_page(pageObjectId)
        if page is None:
            return _Exec(error=make_http_error(404, f"Requested entity was not found: {pageObjectId}"))
        return _Exec(page)

    def getThumbnail(self, presentationId, pageObjectId, thumbnailProperties_thumbnailSize):
        self.svc.thumbnail_calls.append({"page": pageObjectId, "size": thumbnailProperties_thumbnailSize})
        if self.svc.find_page(pageObjectId) is None:
            return _Exec(error=make_http_error(404, f"Requested entity was not found: {pageObjectId}"))
        return _Exec({
            "contentUrl": f"https://thumb.test/{pageObjectId}/{thumbnailProperties_thumbnailSize}",
            "width": 200, "height": 112,
        })


# --- Drive ----------------------------------------------------------------

class FakeDrive:
    """Minimal Drive v3: files.create/delete, permissions, comments, replies."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.fail: dict[str, Exception] = {}  # e.g. {"files.delete": HttpError}
        self.comments_store: dict[str, dict] = {}
        self.store_files: list[dict] = []  # {id, name, mimeType, parents, bytes?}
        self._seq = 0

    def _call(self, name: str, result, **kw):
        self.calls.append((name, kw))
        if name in self.fail:
            return _Exec(error=self.fail[name])
        return _Exec(result)

    def files(self):
        return _FakeDriveFiles(self)

    def permissions(self):
        return _FakeDrivePermissions(self)

    def comments(self):
        return _FakeDriveComments(self)

    def replies(self):
        return _FakeDriveReplies(self)


class _FakeDriveFiles:
    def __init__(self, d): self.d = d
    def create(self, body=None, media_body=None, fields=None, supportsAllDrives=None):
        self.d._seq += 1
        fid = f"drive_file_{self.d._seq}"
        if body and body.get("name"):
            self.d.store_files.append({"id": fid, "name": body["name"], "mimeType": body.get("mimeType", "image/png"),
                                       "parents": body.get("parents", [])})
        return self.d._call("files.create", {"id": fid}, body=body, has_media=media_body is not None,
                            media_path=getattr(media_body, "_filename", None), fields=fields,
                            supportsAllDrives=supportsAllDrives)
    def delete(self, fileId, supportsAllDrives=None):
        return self.d._call("files.delete", "", fileId=fileId)
    def list(self, q="", fields=None, pageSize=None, supportsAllDrives=None, includeItemsFromAllDrives=None, pageToken=None):
        import re
        folder = re.search(r"'([^']+)' in parents", q)
        files = [f for f in self.d.store_files if not folder or folder.group(1) in f.get("parents", [])]
        return self.d._call("files.list", {"files": [{k: f[k] for k in ("id", "name", "mimeType")} for f in files]}, q=q)
    def get_media(self, fileId, supportsAllDrives=None):
        f = next((f for f in self.d.store_files if f["id"] == fileId), None)
        return self.d._call("files.get_media", (f or {}).get("bytes", b""), fileId=fileId)


class _FakeDrivePermissions:
    def __init__(self, d): self.d = d
    def create(self, fileId, body, fields=None, supportsAllDrives=None):
        return self.d._call("permissions.create", {"id": "anyoneWithLink", **body}, fileId=fileId, body=body)
    def delete(self, fileId, permissionId):
        return self.d._call("permissions.delete", "", fileId=fileId, permissionId=permissionId)


class _FakeDriveComments:
    def __init__(self, d): self.d = d
    def list(self, fileId, fields=None, pageSize=None, includeDeleted=None, pageToken=None):
        return self.d._call("comments.list", {"comments": list(self.d.comments_store.values())},
                            fileId=fileId, pageSize=pageSize, includeDeleted=includeDeleted, fields=fields)
    def get(self, fileId, commentId, fields=None, includeDeleted=None):
        c = self.d.comments_store.get(commentId)
        if c is None:
            return self.d._call("comments.get", None, fileId=fileId, commentId=commentId) if "comments.get" in self.d.fail \
                else _Exec(error=make_http_error(404, f"Comment not found: {commentId}"))
        return self.d._call("comments.get", c, fileId=fileId, commentId=commentId, fields=fields)
    def create(self, fileId, body, fields=None):
        self.d._seq += 1
        c = {"id": f"c{self.d._seq}", "content": body["content"], "resolved": False, "replies": []}
        self.d.comments_store[c["id"]] = c
        return self.d._call("comments.create", c, fileId=fileId, body=body, fields=fields)
    def delete(self, fileId, commentId):
        self.d.comments_store.pop(commentId, None)
        return self.d._call("comments.delete", "", fileId=fileId, commentId=commentId)


class _FakeDriveReplies:
    def __init__(self, d): self.d = d
    def create(self, fileId, commentId, body, fields=None):
        self.d._seq += 1
        r = {"id": f"r{self.d._seq}", "content": body.get("content", ""), "action": body.get("action")}
        c = self.d.comments_store.get(commentId)
        if c is not None:
            c["replies"].append(r)
            if body.get("action") == "resolve":
                c["resolved"] = True
        return self.d._call("replies.create", r, fileId=fileId, commentId=commentId, body=body, fields=fields)


# --- fixtures -------------------------------------------------------------

def _patch_everywhere(monkeypatch, name: str, value) -> None:
    """Rebind ``name`` in every gslides_mcp.tools module that imported it."""
    import gslides_mcp.tools as tools_pkg

    modules = [importlib.import_module(f"gslides_mcp.tools.{info.name}") for info in pkgutil.iter_modules(tools_pkg.__path__)]
    modules.append(importlib.import_module("gslides_mcp.assets"))
    for mod in modules:
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, value)


@pytest.fixture
def pres() -> dict:
    return load_fixture("presentation.json")


@pytest.fixture
def fake_slides(monkeypatch, pres) -> FakeSlides:
    svc = FakeSlides(pres)
    _patch_everywhere(monkeypatch, "slide_service", lambda: svc)
    return svc


@pytest.fixture
def fake_drive(monkeypatch) -> FakeDrive:
    drv = FakeDrive()
    _patch_everywhere(monkeypatch, "drive_service", lambda: drv)
    return drv


@pytest.fixture
def fake_download(monkeypatch):
    """Replace the thumbnail downloader with one that writes a tiny PNG."""
    from PIL import Image as PILImage

    from gslides_mcp.tools import qa

    urls: list[str] = []

    def _fake(url: str, dst: str, timeout: float = 30.0) -> None:
        urls.append(url)
        PILImage.new("RGB", (200, 112), (200, 220, 240)).save(dst, "PNG")

    monkeypatch.setattr(qa, "_download_to", _fake)
    return urls
