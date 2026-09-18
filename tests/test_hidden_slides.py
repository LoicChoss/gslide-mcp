"""Hidden (skipped) slides are flagged on read and toggled by set_slide_hidden."""

from gslides_mcp.tools import deck, slides


def test_list_and_inspect_flag_hidden_slides(fake_slides):
    rows = deck.list_slides("PRES1")
    assert [r.get("hidden") for r in rows] == [None, None, True]
    assert deck.inspect_slide("PRES1", "3")["hidden"] is True
    assert "hidden" not in deck.inspect_slide("PRES1", "1")


def test_set_slide_hidden_updates_is_skipped(fake_slides):
    out = slides.set_slide_hidden("PRES1", ["1", "slide_2"])
    assert out == {"updated": ["slide_1", "slide_2"], "hidden": True}
    reqs = fake_slides.batches[-1]
    assert [r["updateSlideProperties"]["objectId"] for r in reqs] == ["slide_1", "slide_2"]
    assert all(r["updateSlideProperties"]["slideProperties"] == {"isSkipped": True}
               and r["updateSlideProperties"]["fields"] == "isSkipped" for r in reqs)
    out = slides.set_slide_hidden("PRES1", ["3"], hidden=False)
    assert out["hidden"] is False
    assert fake_slides.batches[-1][0]["updateSlideProperties"]["slideProperties"] == {"isSkipped": False}
