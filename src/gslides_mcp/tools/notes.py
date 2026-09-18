"""Speaker notes: read and rewrite the notes shape of a slide.

Every slide has a notes page whose ``notesProperties.speakerNotesObjectId``
names the shape holding the speaker notes. The shape itself may not exist
yet (Google creates it on the first insertText), so an empty-notes slide is
written with insertText alone — a deleteText on it would fail the batch.
"""

from __future__ import annotations

from ..app import IDEMPOTENT, READ_ONLY, mcp
from ..auth import slide_service
from ..util import parse_pres_id

_NOTES_FIELDS = (
    "slides(objectId,slideProperties(notesPage("
    "notesProperties(speakerNotesObjectId),"
    "pageElements(objectId,shape(text(textElements(textRun(content))))))))"
)


def _notes_shape(pres: dict, slide: str) -> tuple[str, str, str]:
    """(slide_id, notes shape objectId, current plain text) for ``slide``."""
    from .deck import _resolve_slide

    sl = _resolve_slide(pres, slide)
    notes_page = sl.get("slideProperties", {}).get("notesPage") or {}
    shape_id = notes_page.get("notesProperties", {}).get("speakerNotesObjectId")
    if not shape_id:
        raise ValueError(
            f"slide {sl['objectId']} has no speaker-notes shape "
            "(notesProperties.speakerNotesObjectId is missing)"
        )
    text = ""
    for el in notes_page.get("pageElements", []):
        if el.get("objectId") == shape_id:
            runs = (
                te.get("textRun", {}).get("content", "")
                for te in el.get("shape", {}).get("text", {}).get("textElements", [])
            )
            text = "".join(runs).rstrip("\n")
    return sl["objectId"], shape_id, text


@mcp.tool(annotations=READ_ONLY)
def get_speaker_notes(presentation: str, slide: str) -> dict:
    """Read a slide's speaker notes.

    Args:
        slide: 1-based index or objectId.

    Returns: ``{slide_id, notes_object_id, text}`` — ``text`` is the plain
    notes text (empty string when there are none); ``notes_object_id`` is the
    shape to target with ``write_text_markdown`` for styled notes.

    Example: ``get_speaker_notes(deck, 3)["text"]``
    """
    pid = parse_pres_id(presentation)
    pres = slide_service().presentations().get(
        presentationId=pid, fields=_NOTES_FIELDS
    ).execute()
    slide_id, shape_id, text = _notes_shape(pres, slide)
    return {"slide_id": slide_id, "notes_object_id": shape_id, "text": text}


@mcp.tool(annotations=IDEMPOTENT)
def set_speaker_notes(presentation: str, slide: str, text: str) -> dict:
    """Replace a slide's speaker notes with plain ``text`` (empty = clear).

    Atomic: the delete of the old text and the insert of the new one go in
    one batchUpdate. The delete is only sent when the shape already holds
    text — deleteText on an empty notes shape fails the whole batch.

    Args:
        slide: 1-based index or objectId.
        text: new notes content; ``""`` clears the notes.

    Returns: ``{slide_id, notes_object_id, length}``.

    Example: ``set_speaker_notes(deck, 3, "Rappeler le chiffre clé avant la transition.")``
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid, fields=_NOTES_FIELDS).execute()
    slide_id, shape_id, current = _notes_shape(pres, slide)

    reqs: list[dict] = []
    if current:
        reqs.append({"deleteText": {"objectId": shape_id, "textRange": {"type": "ALL"}}})
    if text:
        reqs.append({"insertText": {"objectId": shape_id, "text": text, "insertionIndex": 0}})
    if reqs:
        svc.presentations().batchUpdate(
            presentationId=pid, body={"requests": reqs}
        ).execute()
    return {"slide_id": slide_id, "notes_object_id": shape_id, "length": len(text)}
