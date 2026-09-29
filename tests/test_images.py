"""replace_images: swap pictures in place, keep each element's id and frame."""

import pytest

from gslides_mcp.tools import images

PT = 12700


def _image(oid, x, y, w, h, base=(49000, 27600), description=None, shear=0.0):
    """An image element whose displayed box is (x, y, w, h) pt over a base size in EMU."""
    el = {"objectId": oid, "size": {"width": {"magnitude": base[0], "unit": "EMU"},
                                    "height": {"magnitude": base[1], "unit": "EMU"}},
          "transform": {"scaleX": w * PT / base[0], "scaleY": h * PT / base[1], "shearX": shear,
                        "translateX": x * PT, "translateY": y * PT, "unit": "EMU"},
          "image": {"sourceUrl": "https://x/old.png"}}
    if description:
        el["description"] = description
    return el


@pytest.fixture
def deck(fake_slides, pres, monkeypatch):
    pres["slides"][2]["pageElements"] = [
        _image("fresh", 40, 40, 100, 100),
        _image("slotted", 40, 201.8, 100, 56.3, description="slot:40.0,180.0,100.0,100.0"),
        _image("moved", 300, 300, 100, 56.3, description="slot:40.0,180.0,100.0,100.0"),
        _image("tilted", 10, 10, 50, 50, shear=0.2),
        {"objectId": "a_box", "shape": {"shapeType": "RECTANGLE"}},
    ]
    probes = []

    def probe(url, timeout=4.0):
        probes.append(url)
        return (False, "text/html") if "page" in url else (True, "image/png")

    monkeypatch.setattr(images, "_image_url_is_raster", probe)
    monkeypatch.setattr(images.assets, "ensure_asset", lambda ref, tint=None: "fid_" + ref)
    fake_slides.probes = probes
    return fake_slides


def _kinds(batch):
    return [next(iter(r)) for r in batch]


def _of(batch, kind):
    return [r[kind] for r in batch if kind in r]


def test_url_into_a_fresh_image_records_its_frame_then_replaces(deck):
    out = images.replace_images("PRES1", [{"element": "fresh", "source": "https://cdn.test/ad.png"}])
    (batch,) = deck.batches
    assert _kinds(batch) == ["updatePageElementAltText", "replaceImage"]
    assert _of(batch, "updatePageElementAltText")[0] == {"objectId": "fresh", "description": "slot:40.0,40.0,100.0,100.0"}
    assert _of(batch, "replaceImage")[0] == {"imageObjectId": "fresh", "url": "https://cdn.test/ad.png",
                                             "imageReplaceMethod": "CENTER_INSIDE"}
    assert deck.probes == ["https://cdn.test/ad.png"]
    assert out["replaced"][0]["frame_recorded"] is True and out["replaced"][0]["frame_restored"] is False


def test_a_shrunken_slot_gets_its_frame_back_before_the_new_picture(deck):
    out = images.replace_images("PRES1", [{"element": "slotted", "source": "post-video"}])
    (batch,) = deck.batches
    assert _kinds(batch) == ["updatePageElementTransform", "replaceImage"]
    t = _of(batch, "updatePageElementTransform")[0]
    assert t["objectId"] == "slotted" and t["applyMode"] == "ABSOLUTE"
    assert t["transform"]["scaleX"] == pytest.approx(100 * PT / 49000)
    assert t["transform"]["scaleY"] == pytest.approx(100 * PT / 27600)
    assert (t["transform"]["translateX"], t["transform"]["translateY"]) == (40 * PT, 180 * PT)
    assert _of(batch, "replaceImage")[0]["url"] == "https://drive.google.com/uc?export=view&id=fid_post-video"
    assert out["replaced"][0]["frame_restored"] is True


def test_a_slot_moved_by_hand_takes_its_current_box_as_frame(deck):
    images.replace_images("PRES1", [{"element": "moved", "source": "post-video", "fit": "crop"}])
    (batch,) = deck.batches
    assert _kinds(batch) == ["updatePageElementAltText", "replaceImage"]
    assert _of(batch, "updatePageElementAltText")[0]["description"] == "slot:300.0,300.0,100.0,56.3"
    assert _of(batch, "replaceImage")[0]["imageReplaceMethod"] == "CENTER_CROP"


def test_an_empty_source_puts_the_slot_placeholder_back(deck):
    out = images.replace_images("PRES1", [{"element": "slotted", "source": ""}])
    swap = _of(deck.batches[0], "replaceImage")[0]
    # the placeholder of the 100 × 100 frame, in the theme's surface / divider colours
    assert swap["url"].startswith("https://drive.google.com/uc?export=view&id=fid_slot:400x400:")
    assert swap["imageReplaceMethod"] == "CENTER_CROP"
    assert out["replaced"][0]["source"] == "slot"


def test_a_sheared_image_is_replaced_without_restoring_its_frame(deck):
    out = images.replace_images("PRES1", [{"element": "tilted", "source": "post-video"}])
    assert "updatePageElementTransform" not in _kinds(deck.batches[0])
    assert "rotated" in out["replaced"][0]["note"]


@pytest.mark.parametrize("items, match", [
    ([], "images is empty"),
    ([{"source": "x"}], "'element'"),
    ([{"element": "nope", "source": "x"}], "not found"),
    ([{"element": "a_box", "source": "x"}], "not an image"),
    ([{"element": "fresh", "source": "x", "fit": "stretch"}], "fit"),
    ([{"element": "fresh", "source": "x"}, {"element": "fresh", "source": "y"}], "twice"),
    ([{"element": "fresh", "source": "https://cdn.test/page"}], "text/html"),
    ([{"element": "fresh", "source": "https://cdn.test/" + "a" * 2100 + ".png"}], "2 kB"),
])
def test_refusals_come_before_any_write(deck, items, match):
    with pytest.raises(ValueError, match=match):
        images.replace_images("PRES1", items)
    assert deck.batches == []
