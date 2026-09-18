"""Speaker notes: read the notes shape, rewrite it without deleteText on empty."""

import pytest

from gslides_mcp.tools import notes


def test_get_speaker_notes_returns_text_and_shape_id(fake_slides):
    out = notes.get_speaker_notes("PRES1", "1")
    assert out == {"slide_id": "slide_1", "notes_object_id": "notes_1_shape", "text": "Existing note"}
    assert "notesPage" in fake_slides.get_calls[-1]["fields"]


def test_get_speaker_notes_empty_shape(fake_slides):
    out = notes.get_speaker_notes("PRES1", "slide_2")
    assert out["text"] == ""
    assert out["notes_object_id"] == "notes_2_shape"


def test_get_speaker_notes_unknown_slide(fake_slides):
    with pytest.raises(ValueError, match="'9'"):
        notes.get_speaker_notes("PRES1", "9")


def test_set_speaker_notes_replaces_existing_text(fake_slides):
    out = notes.set_speaker_notes("PRES1", "slide_1", "New note")
    assert fake_slides.batches == [[
        {"deleteText": {"objectId": "notes_1_shape", "textRange": {"type": "ALL"}}},
        {"insertText": {"objectId": "notes_1_shape", "text": "New note", "insertionIndex": 0}},
    ]]
    assert out == {"slide_id": "slide_1", "notes_object_id": "notes_1_shape", "length": 8}


def test_set_speaker_notes_on_empty_shape_only_inserts(fake_slides):
    notes.set_speaker_notes("PRES1", "2", "First")
    assert fake_slides.batches == [[
        {"insertText": {"objectId": "notes_2_shape", "text": "First", "insertionIndex": 0}},
    ]]


def test_set_speaker_notes_empty_text_clears(fake_slides):
    out = notes.set_speaker_notes("PRES1", "slide_1", "")
    assert fake_slides.batches == [[
        {"deleteText": {"objectId": "notes_1_shape", "textRange": {"type": "ALL"}}},
    ]]
    assert out["length"] == 0


def test_set_speaker_notes_empty_on_empty_is_a_noop(fake_slides):
    out = notes.set_speaker_notes("PRES1", "slide_2", "")
    assert fake_slides.batches == []
    assert out["length"] == 0


def test_slide_without_notes_shape_is_reported(fake_slides):
    with pytest.raises(ValueError, match="slide_3"):
        notes.get_speaker_notes("PRES1", "slide_3")
