"""Default template and folder set in the Desktop bundle: get_defaults, and where new decks land."""

import pytest

from conftest import make_http_error
from gslides_mcp import defaults
from gslides_mcp.tools import cross_deck, deck, library

FOLDER = "application/vnd.google-apps.folder"
SLIDES = "application/vnd.google-apps.presentation"


@pytest.fixture
def drive(fake_drive):
    fake_drive.store_files += [
        {"id": "fold_tpl", "name": "Templates", "mimeType": FOLDER, "parents": ["root"]},
        {"id": "fold_out", "name": "Prez", "mimeType": FOLDER, "parents": ["root"]},
        {"id": "fold_dst", "name": "Archives", "mimeType": FOLDER, "parents": ["root"]},
        {"id": "tpl", "name": "Template Periscope", "mimeType": SLIDES, "parents": ["fold_tpl"]},
        {"id": "last", "name": "Bilan août", "mimeType": SLIDES, "parents": ["fold_dst"]},
        {"id": "sheet1", "name": "Données", "mimeType": "application/vnd.google-apps.spreadsheet", "parents": ["root"]},
    ]
    return fake_drive


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv(defaults.ENV_TEMPLATE, "https://docs.google.com/presentation/d/tpl/edit")
    monkeypatch.setenv(defaults.ENV_FOLDER, "https://drive.google.com/drive/folders/fold_out?usp=sharing")


@pytest.fixture(autouse=True)
def unset(monkeypatch):
    monkeypatch.delenv(defaults.ENV_TEMPLATE, raising=False)
    monkeypatch.delenv(defaults.ENV_FOLDER, raising=False)


def _calls(drv, name):
    return [kw for n, kw in drv.calls if n == name]


# --- settings -------------------------------------------------------------------------

def test_settings_take_an_id_or_a_url(monkeypatch):
    assert defaults.template_id() is None and defaults.folder_id() is None
    monkeypatch.setenv(defaults.ENV_TEMPLATE, " https://docs.google.com/presentation/d/1PrEs/edit#slide=id.p ")
    monkeypatch.setenv(defaults.ENV_FOLDER, "1FoLd")
    assert defaults.template_id() == "1PrEs" and defaults.folder_id() == "1FoLd"


def test_an_unfilled_desktop_field_counts_as_unset(monkeypatch):
    monkeypatch.setenv(defaults.ENV_TEMPLATE, "${user_config.default_template}")
    monkeypatch.setenv(defaults.ENV_FOLDER, "   ")
    assert defaults.template_id() is None and defaults.folder_id() is None


# --- get_defaults ---------------------------------------------------------------------

def test_get_defaults_without_settings_reads_nothing(drive):
    assert deck.get_defaults() == {"template": None, "folder": None}
    assert drive.calls == []


def test_get_defaults_names_the_template_and_the_folder(drive, configured):
    assert deck.get_defaults() == {
        "template": {"id": "tpl", "url": "https://docs.google.com/presentation/d/tpl/edit", "title": "Template Periscope"},
        "folder": {"id": "fold_out", "name": "Prez"},
    }


def test_get_defaults_reports_unusable_settings_without_failing(drive, monkeypatch):
    monkeypatch.setenv(defaults.ENV_TEMPLATE, "sheet1")
    monkeypatch.setenv(defaults.ENV_FOLDER, "gone")
    out = deck.get_defaults()
    assert out["template"]["id"] == "sheet1" and "not a presentation" in out["template"]["error"]
    assert out["folder"]["id"] == "gone" and "not found" in out["folder"]["error"]


def test_get_defaults_refuses_a_file_as_folder(drive, monkeypatch):
    monkeypatch.setenv(defaults.ENV_FOLDER, "tpl")
    assert "not a folder" in deck.get_defaults()["folder"]["error"]


# --- clone_deck -----------------------------------------------------------------------

def test_clone_of_the_default_template_lands_in_the_default_folder(drive, configured):
    out = deck.clone_deck("https://docs.google.com/presentation/d/tpl/edit", "Client · reco · 2026-10")
    assert _calls(drive, "files.copy")[0]["body"]["parents"] == ["fold_out"]
    assert out["placed"] == "default_folder" and out["folder_id"] == "fold_out" and out["folder_name"] == "Prez"


def test_a_given_folder_beats_the_default_folder(drive, configured):
    out = deck.clone_deck("tpl", "x", parent_folder_id="fold_dst")
    assert _calls(drive, "files.copy")[0]["body"]["parents"] == ["fold_dst"] and out["placed"] == "given"


def test_a_copy_of_another_deck_stays_next_to_its_source(drive, configured):
    out = deck.clone_deck("last", "Bilan septembre")
    assert _calls(drive, "files.copy")[0]["body"]["parents"] == ["fold_dst"] and out["placed"] == "source_folder"


def test_without_a_default_folder_the_template_copy_stays_next_to_it(drive, monkeypatch):
    monkeypatch.setenv(defaults.ENV_TEMPLATE, "tpl")
    out = deck.clone_deck("tpl", "x")
    assert out["placed"] == "source_folder" and out["folder_id"] == "fold_tpl"


def test_a_default_folder_that_refuses_the_copy_falls_back_to_my_drive(drive, configured):
    drive.fail["files.copy#1"] = make_http_error(403, "insufficientFilePermissions")
    out = deck.clone_deck("tpl", "x")
    first, second = _calls(drive, "files.copy")
    assert first["body"]["parents"] == ["fold_out"] and "parents" not in second["body"]
    assert out["placed"] == "my_drive" and "default folder" in out["folder_note"]


# --- create_presentation --------------------------------------------------------------

def test_create_presentation_uses_the_default_folder(drive, configured, fake_slides):
    out = deck.create_presentation("Deck")
    (create,) = _calls(drive, "files.create")
    assert create["body"]["parents"] == ["fold_out"]
    assert out["folder_id"] == "fold_out" and out["folder_name"] == "Prez"


def test_create_presentation_given_folder_wins(drive, configured, fake_slides):
    deck.create_presentation("Deck", folder="fold_dst")
    assert _calls(drive, "files.create")[0]["body"]["parents"] == ["fold_dst"]


def test_create_presentation_names_a_broken_default_folder(drive, monkeypatch, fake_slides):
    monkeypatch.setenv(defaults.ENV_FOLDER, "gone")
    with pytest.raises(ValueError, match="default folder"):
        deck.create_presentation("Deck")
    assert _calls(drive, "files.create") == []


# --- assemble_from_template -----------------------------------------------------------

class _Exec:
    def __init__(self, result): self.result = result
    def execute(self, **_): return self.result


class _NewDeck:
    """Slides service for a freshly created deck: create, get (one blank slide + copies), batchUpdate."""

    def __init__(self): self.slides = [{"objectId": "blank"}]
    def presentations(self): return self
    def create(self, body): return _Exec({"presentationId": "new1"})
    def get(self, presentationId): return _Exec({"slides": self.slides})
    def batchUpdate(self, presentationId, body): return _Exec({})


@pytest.fixture
def assembly(drive, monkeypatch):
    svc = _NewDeck()
    drive.store_files.append({"id": "new1", "name": "Assemblé", "mimeType": SLIDES, "parents": ["root"]})
    monkeypatch.setattr(library, "slide_service", lambda: svc)

    def copy(src_presentation, src_slide, dst_presentation):
        svc.slides.append({"objectId": f"copied_{len(svc.slides)}"})
        return {"newSlideId": svc.slides[-1]["objectId"], "dstIndex": len(svc.slides) - 1}

    monkeypatch.setattr(cross_deck, "copy_slide_cross_deck", copy)
    return drive


def test_assemble_from_template_uses_the_default_folder(assembly, configured):
    out = library.assemble_from_template([{"deck": "tpl", "slide": "1"}], "Assemblé")
    (upd,) = _calls(assembly, "files.update")
    assert upd["addParents"] == "fold_out" and out["parent_folder_id"] == "fold_out" and out["folder_move"] == "ok"


def test_assemble_from_template_reads_a_folder_url(assembly):
    out = library.assemble_from_template([{"deck": "tpl", "slide": "1"}], "Assemblé",
                                         parent_folder_id="https://drive.google.com/drive/folders/fold_dst")
    assert _calls(assembly, "files.update")[0]["addParents"] == "fold_dst" and out["parent_folder_id"] == "fold_dst"


def test_assemble_from_template_without_any_folder_skips_the_move(assembly):
    out = library.assemble_from_template([{"deck": "tpl", "slide": "1"}], "Assemblé")
    assert _calls(assembly, "files.update") == [] and out["folder_move"] == "skipped"
