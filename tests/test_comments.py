"""manage_comments: Drive v3 comments/replies on the presentation file."""

import pytest

from gslides_mcp.tools import comments


def _kw(drive, name):
    return next(kw for n, kw in drive.calls if n == name)


def test_list_passes_paging_and_asks_for_all_fields(fake_drive):
    fake_drive.comments_store["c1"] = {
        "id": "c1", "content": "Fix this", "resolved": False,
        "author": {"displayName": "Ana"}, "createdTime": "2026-09-01T10:00:00Z",
        "replies": [{"id": "r1", "content": "Done", "author": {"displayName": "Bo"}, "action": "resolve"}],
    }
    out = comments.manage_comments("PRES1", "list", page_size=10, include_deleted=True)
    kw = _kw(fake_drive, "comments.list")
    assert kw["fileId"] == "PRES1" and kw["pageSize"] == 10 and kw["includeDeleted"] is True
    assert kw["fields"] and "replies" in kw["fields"]
    assert out["comments"] == [{
        "id": "c1", "content": "Fix this", "author": "Ana", "resolved": False,
        "created": "2026-09-01T10:00:00Z", "modified": None, "deleted": False, "anchored": False,
        "replies": [{"id": "r1", "content": "Done", "author": "Bo", "action": "resolve", "created": None}],
    }]


def test_get_requires_comment_id_and_names_unknown(fake_drive):
    with pytest.raises(ValueError, match="comment_id"):
        comments.manage_comments("PRES1", "get")
    with pytest.raises(ValueError, match="'zzz'"):
        comments.manage_comments("PRES1", "get", comment_id="zzz")


def test_create_is_unanchored(fake_drive):
    out = comments.manage_comments("PRES1", "create", text="Please shorten slide 3")
    assert _kw(fake_drive, "comments.create")["body"] == {"content": "Please shorten slide 3"}
    assert out["comment"]["content"] == "Please shorten slide 3"
    assert out["comment"]["anchored"] is False
    assert "anchor" in out["note"]


def test_create_requires_text(fake_drive):
    with pytest.raises(ValueError, match="text"):
        comments.manage_comments("PRES1", "create")


def test_reply_and_resolve(fake_drive):
    comments.manage_comments("PRES1", "create", text="Typo")
    out = comments.manage_comments("PRES1", "reply", comment_id="c1", text="Fixed", resolve=True)
    assert _kw(fake_drive, "replies.create")["body"] == {"content": "Fixed", "action": "resolve"}
    assert out["reply"]["action"] == "resolve"
    assert out["comment_id"] == "c1"


def test_resolve_without_text_is_allowed(fake_drive):
    comments.manage_comments("PRES1", "create", text="Typo")
    comments.manage_comments("PRES1", "reply", comment_id="c1", resolve=True)
    assert _kw(fake_drive, "replies.create")["body"] == {"action": "resolve"}


def test_reply_without_text_or_resolve_rejected(fake_drive):
    with pytest.raises(ValueError, match="text"):
        comments.manage_comments("PRES1", "reply", comment_id="c1")


def test_delete(fake_drive):
    comments.manage_comments("PRES1", "create", text="Old")
    out = comments.manage_comments("PRES1", "delete", comment_id="c1")
    assert _kw(fake_drive, "comments.delete")["commentId"] == "c1"
    assert out == {"deleted": "c1"}


def test_unknown_action_lists_actions(fake_drive):
    with pytest.raises(ValueError, match="list, get, create, reply, delete"):
        comments.manage_comments("PRES1", "shout")
    assert fake_drive.calls == []
