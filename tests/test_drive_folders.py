"""Where decks land in Drive: create_presentation(folder), clone_deck next to its source, move_to_folder."""

import pytest

from conftest import make_http_error
from gslides_mcp.tools import deck
from gslides_mcp.util import parse_drive_id

FOLDER = "application/vnd.google-apps.folder"


@pytest.fixture
def drive(fake_drive):
    fake_drive.store_files += [
        {"id": "fold_src", "name": "Bilans CFA", "mimeType": FOLDER, "parents": ["root"]},
        {"id": "fold_dst", "name": "Archives", "mimeType": FOLDER, "parents": ["root"]},
        {"id": "tpl", "name": "Template", "mimeType": "application/vnd.google-apps.presentation", "parents": ["fold_src"]},
        {"id": "sheet1", "name": "Données", "mimeType": "application/vnd.google-apps.spreadsheet", "parents": ["root"]},
    ]
    return fake_drive


def _calls(drv, name):
    return [kw for n, kw in drv.calls if n == name]


def test_parse_drive_id_reads_every_kind_of_link():
    assert parse_drive_id("https://drive.google.com/drive/folders/1AbC_d-9?usp=sharing") == "1AbC_d-9"
    assert parse_drive_id("https://docs.google.com/spreadsheets/d/1XyZ/edit#gid=0") == "1XyZ"
    assert parse_drive_id("https://docs.google.com/presentation/d/1PrEs/edit") == "1PrEs"
    assert parse_drive_id("https://drive.google.com/open?id=1OpEn") == "1OpEn"
    assert parse_drive_id(" 1bare ") == "1bare"


def test_clone_deck_lands_in_the_source_folder(drive):
    out = deck.clone_deck("https://docs.google.com/presentation/d/tpl/edit", "Client · bilan · 2026-09")
    (copy,) = _calls(drive, "files.copy")
    assert copy["body"] == {"name": "Client · bilan · 2026-09", "parents": ["fold_src"]}
    assert out["placed"] == "source_folder" and out["folder_id"] == "fold_src" and out["folder_name"] == "Bilans CFA"
    assert "folder_note" not in out


def test_clone_deck_given_folder_wins(drive):
    out = deck.clone_deck("tpl", "x", parent_folder_id="https://drive.google.com/drive/folders/fold_dst")
    assert _calls(drive, "files.copy")[0]["body"]["parents"] == ["fold_dst"]
    assert out["placed"] == "given" and out["folder_name"] == "Archives"


def test_clone_deck_falls_back_to_my_drive_when_the_source_folder_refuses(drive):
    drive.fail["files.copy#1"] = make_http_error(403, "insufficientFilePermissions")
    out = deck.clone_deck("tpl", "x")
    first, second = _calls(drive, "files.copy")
    assert first["body"]["parents"] == ["fold_src"] and "parents" not in second["body"]
    assert out["placed"] == "my_drive" and "move_to_folder" in out["folder_note"]


def test_clone_deck_of_a_deck_whose_folder_is_hidden(drive):
    drive.store_files.append({"id": "shared", "name": "Shared", "mimeType": "x", "parents": []})
    out = deck.clone_deck("shared", "x")
    assert "parents" not in _calls(drive, "files.copy")[0]["body"]
    assert out["placed"] == "my_drive" and "not visible" in out["folder_note"]


def test_clone_deck_does_not_retry_an_explicit_folder(drive):
    drive.fail["files.copy#1"] = make_http_error(403, "no")
    with pytest.raises(Exception):
        deck.clone_deck("tpl", "x", parent_folder_id="fold_dst")
    assert len(_calls(drive, "files.copy")) == 1


def test_create_presentation_in_a_folder_is_one_drive_create(drive, fake_slides):
    out = deck.create_presentation("Deck", folder="https://drive.google.com/drive/folders/fold_dst")
    (create,) = _calls(drive, "files.create")
    assert create["body"] == {"name": "Deck", "mimeType": "application/vnd.google-apps.presentation", "parents": ["fold_dst"]}
    assert out["folder_id"] == "fold_dst" and out["folder_name"] == "Archives"


def test_create_presentation_refuses_a_file_as_folder(drive, fake_slides):
    with pytest.raises(ValueError, match="not a folder"):
        deck.create_presentation("Deck", folder="sheet1")
    with pytest.raises(ValueError, match="not found"):
        deck.create_presentation("Deck", folder="nope")
    assert _calls(drive, "files.create") == []


def test_move_to_folder_swaps_parents(drive):
    out = deck.move_to_folder("https://docs.google.com/spreadsheets/d/sheet1/edit", "fold_src")
    (upd,) = _calls(drive, "files.update")
    assert upd["addParents"] == "fold_src" and upd["removeParents"] == "root"
    assert out == {"file_id": "sheet1", "name": "Données", "folder_id": "fold_src", "folder_name": "Bilans CFA",
                   "previous_folders": ["root"]}


def test_move_to_folder_twice_is_harmless(drive):
    deck.move_to_folder("tpl", "fold_src")
    assert _calls(drive, "files.update") == []


def test_move_to_folder_unknown_file(drive):
    with pytest.raises(ValueError, match="not found"):
        deck.move_to_folder("nope", "fold_dst")
