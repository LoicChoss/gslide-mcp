"""util.resolve_layout: id / display_name / API name, fuzzy fallback, no silent picks."""

import pytest

from gslides_mcp.util import resolve_layout


def test_exact_layout_id(pres):
    assert resolve_layout(pres, "lay_body")["objectId"] == "lay_body"


def test_exact_display_name(pres):
    assert resolve_layout(pres, "Titre et corps")["objectId"] == "lay_body"


def test_display_name_case_insensitive(pres):
    assert resolve_layout(pres, "titre ET corps")["objectId"] == "lay_body"


def test_display_name_accent_insensitive(pres):
    assert resolve_layout(pres, "resume")["objectId"] == "lay_summary"


def test_api_name_as_last_resort(pres):
    assert resolve_layout(pres, "TITLE_AND_BODY")["objectId"] == "lay_body"


def test_ambiguous_display_name_lists_candidates_with_masters(pres):
    with pytest.raises(ValueError) as exc:
        resolve_layout(pres, "Arborescence")
    msg = str(exc.value)
    assert "lay_dup_a" in msg and "lay_dup_b" in msg
    assert "m_main" in msg and "m_orphan" in msg
    assert "ambiguous" in msg


def test_unknown_layout_names_the_ref_and_lists_available(pres):
    with pytest.raises(ValueError) as exc:
        resolve_layout(pres, "Nope")
    msg = str(exc.value)
    assert "'Nope'" in msg
    assert "Titre et corps" in msg  # available display names are listed


def test_exact_match_wins_over_fuzzy_when_both_exist(pres):
    # "Résumé" exists exactly; a folded match must not turn it into an ambiguity
    assert resolve_layout(pres, "Résumé")["objectId"] == "lay_summary"
