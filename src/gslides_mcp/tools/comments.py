"""manage_comments: Drive comments and replies on the presentation file.

Slides has no comment API of its own; comments live on the Drive file
(``drive.comments`` / ``drive.replies``), which the ``drive`` scope already
covers. Drive can't anchor a new comment to a slide through the API, so
``create`` produces an unanchored comment visible in the deck's comment list.
"""

from __future__ import annotations

from googleapiclient.errors import HttpError

from ..app import DESTRUCTIVE, mcp
from ..auth import drive_service
from ..util import parse_pres_id

_ACTIONS = ("list", "get", "create", "reply", "delete")

_REPLY_FIELDS = "id,content,author(displayName),action,createdTime"
_COMMENT_FIELDS = (
    "id,content,author(displayName),resolved,createdTime,modifiedTime,deleted,anchor,"
    f"replies({_REPLY_FIELDS})"
)
_LIST_FIELDS = f"nextPageToken,comments({_COMMENT_FIELDS})"

_UNANCHORED_NOTE = (
    "Drive comments on a Slides file can't be anchored to a slide through the "
    "API; this comment is unanchored (it shows in the deck's comment list, not "
    "on a slide)."
)


def _slim_reply(r: dict) -> dict:
    return {
        "id": r.get("id"),
        "content": r.get("content", ""),
        "author": r.get("author", {}).get("displayName"),
        "action": r.get("action"),
        "created": r.get("createdTime"),
    }


def _slim(c: dict) -> dict:
    return {
        "id": c.get("id"),
        "content": c.get("content", ""),
        "author": c.get("author", {}).get("displayName"),
        "resolved": bool(c.get("resolved")),
        "created": c.get("createdTime"),
        "modified": c.get("modifiedTime"),
        "deleted": bool(c.get("deleted")),
        "anchored": bool(c.get("anchor")),
        "replies": [_slim_reply(r) for r in c.get("replies", [])],
    }


@mcp.tool(annotations=DESTRUCTIVE)
def manage_comments(
    presentation: str,
    action: str,
    comment_id: str | None = None,
    text: str | None = None,
    resolve: bool = False,
    include_deleted: bool = False,
    page_size: int = 50,
) -> dict:
    """List, read, create, reply to or delete Drive comments on the deck.

    Args:
        action: ``list`` | ``get`` | ``create`` | ``reply`` | ``delete``.
        comment_id: required for ``get``, ``reply``, ``delete``.
        text: comment body for ``create``; reply body for ``reply``
            (optional there when ``resolve=True``).
        resolve: with ``reply``, also marks the comment resolved.
        include_deleted: ``list``/``get`` include deleted comments.
        page_size: ``list`` page size (max 100); ``next_page_token`` is
            returned when there are more.

    ``create`` is unanchored — Drive offers no way to pin a new comment to a
    slide. ``delete`` is destructive and permanent.

    Returns: ``list`` → ``{comments: [...], next_page_token}``; ``get`` →
    ``{comment}``; ``create`` → ``{comment, note}``; ``reply`` →
    ``{comment_id, reply}``; ``delete`` → ``{deleted}``.

    Example: ``manage_comments(deck, "reply", comment_id="AAAB…", text="Corrigé", resolve=True)``
    """
    if action not in _ACTIONS:
        raise ValueError(f"action must be one of {', '.join(_ACTIONS)}, got {action!r}")
    pid = parse_pres_id(presentation)
    drv = drive_service()

    if action == "list":
        resp = drv.comments().list(
            fileId=pid, fields=_LIST_FIELDS, pageSize=page_size, includeDeleted=include_deleted
        ).execute()
        return {
            "comments": [_slim(c) for c in resp.get("comments", [])],
            "next_page_token": resp.get("nextPageToken"),
        }

    if action == "create":
        if not text:
            raise ValueError("create needs text")
        c = drv.comments().create(fileId=pid, body={"content": text}, fields=_COMMENT_FIELDS).execute()
        return {"comment": _slim(c), "note": _UNANCHORED_NOTE}

    if not comment_id:
        raise ValueError(f"{action} needs comment_id (find ids with action='list')")

    if action == "get":
        try:
            c = drv.comments().get(
                fileId=pid, commentId=comment_id, fields=_COMMENT_FIELDS, includeDeleted=include_deleted
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"comment not found: {comment_id!r} on {pid}") from None
            raise
        return {"comment": _slim(c)}

    if action == "reply":
        if not text and not resolve:
            raise ValueError("reply needs text, or resolve=True to resolve without a message")
        body: dict = {}
        if text:
            body["content"] = text
        if resolve:
            body["action"] = "resolve"
        r = drv.replies().create(
            fileId=pid, commentId=comment_id, body=body, fields=_REPLY_FIELDS
        ).execute()
        return {"comment_id": comment_id, "reply": _slim_reply(r)}

    drv.comments().delete(fileId=pid, commentId=comment_id).execute()
    return {"deleted": comment_id}
