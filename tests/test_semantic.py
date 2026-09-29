"""swap_client: the logo is swapped in place, same element and frame."""

import pytest

from gslides_mcp.tools import images, semantic


@pytest.fixture
def raster(monkeypatch):
    ok = lambda url, timeout=4.0: (True, "image/png")  # noqa: E731
    monkeypatch.setattr(semantic, "_image_url_is_raster", ok)
    monkeypatch.setattr(images, "_image_url_is_raster", ok)


def test_swap_client_replaces_the_logo_in_place(fake_slides, raster):
    out = semantic.swap_client("PRES1", "Acme", "Globex", new_logo_url="https://cdn.test/globex.png")
    logo_batch = fake_slides.batches[-1]
    kinds = [next(iter(r)) for r in logo_batch]
    assert "deleteObject" not in kinds and "createImage" not in kinds
    (swap,) = [r["replaceImage"] for r in logo_batch if "replaceImage" in r]
    assert swap == {"imageObjectId": "s1_img", "url": "https://cdn.test/globex.png", "imageReplaceMethod": "CENTER_INSIDE"}
    # the logo's box becomes its frame, so the next swap fits the same place
    (alt,) = [r["updatePageElementAltText"] for r in logo_batch if "updatePageElementAltText" in r]
    assert alt["objectId"] == "s1_img" and alt["description"].startswith("slot:472.4,78.7,63.0,47.2")
    (entry,) = out["logo_swaps"]
    assert entry["swapped"] is True and entry["element"] == "s1_img" and entry["slide"] == "slide_1"
    assert "deleted_id" not in entry


def test_swap_client_refuses_an_svg_logo_before_writing_it(fake_slides, monkeypatch):
    monkeypatch.setattr(semantic, "_image_url_is_raster", lambda url, timeout=4.0: (False, "image/svg+xml"))
    with pytest.raises(ValueError, match="svg"):
        semantic.swap_client("PRES1", "Acme", "Globex", new_logo_url="https://cdn.test/globex.svg")
    assert not any("replaceImage" in r for batch in fake_slides.batches for r in batch)
