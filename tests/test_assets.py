"""Assets: named PNGs in a shared Drive folder, uploaded once, tinted on demand; card icons."""

import json

import pytest
from PIL import Image as PILImage

from gslides_mcp import assets, components, draw, themes
from gslides_mcp.tools import components as tools

FOLDER = "folder123"
PERISCOPE = themes.load("periscope")


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path, fake_drive):
    monkeypatch.setenv("GSLIDES_MCP_ASSETS_FOLDER", FOLDER)
    monkeypatch.setattr(assets, "CACHE", tmp_path / "assets.json")
    yield


def _png(path, color=(255, 0, 0, 255)):
    im = PILImage.new("RGBA", (8, 8), (0, 0, 0, 0))
    for x in range(4):
        for y in range(8):
            im.putpixel((x, y), color)
    im.save(path, "PNG")
    return str(path)


def _names(drive, kind):
    return [n for n, _ in drive.calls if n == kind]


def test_named_asset_is_found_in_the_folder_and_cached(fake_drive):
    fake_drive.store_files.append({"id": "f_bolt", "name": "bolt.png", "mimeType": "image/png", "parents": [FOLDER]})
    assert assets.ensure_asset("bolt") == "f_bolt"
    assert _names(fake_drive, "files.create") == []
    assert assets.ensure_asset("bolt") == "f_bolt"
    assert _names(fake_drive, "files.list") == ["files.list"]  # second call hits the cache
    assert json.loads(assets.CACHE.read_text())[f"{FOLDER}/bolt.png"] == "f_bolt"


def test_local_path_is_uploaded_once_into_the_folder(fake_drive, tmp_path):
    path = _png(tmp_path / "logo.png")
    fid = assets.ensure_asset(path)
    (create_kw,) = [kw for n, kw in fake_drive.calls if n == "files.create"]
    assert create_kw["body"]["parents"] == [FOLDER] and create_kw["body"]["name"] == "logo.png"
    assert create_kw["supportsAllDrives"] is True
    perm = [kw for n, kw in fake_drive.calls if n == "permissions.create"][0]
    assert perm["body"] == {"type": "anyone", "role": "reader"}
    assert assets.ensure_asset(path) == fid
    assert len(_names(fake_drive, "files.create")) == 1


def test_tinted_variant_is_generated_from_the_source(fake_drive, tmp_path):
    src = _png(tmp_path / "bolt.png")
    fake_drive.store_files.append({"id": "f_bolt", "name": "bolt.png", "mimeType": "image/png", "parents": [FOLDER],
                                   "bytes": open(src, "rb").read()})
    fid = assets.ensure_asset("bolt", tint="#002B3C")
    create_kw = [kw for n, kw in fake_drive.calls if n == "files.create"][0]
    assert create_kw["body"]["name"] == "bolt__002b3c.png"
    with PILImage.open(create_kw["media_path"]) as im:
        assert im.getpixel((0, 0)) == (0, 43, 60, 255)   # opaque pixels take the tint
        assert im.getpixel((7, 7))[3] == 0                # transparency preserved
    assert fid != "f_bolt"
    assert assets.ensure_asset("bolt", tint="#002B3C") == fid  # cached, no second generation
    assert len(_names(fake_drive, "files.create")) == 1


def test_unknown_asset_lists_the_folder(fake_drive):
    fake_drive.store_files.append({"id": "f1", "name": "megaphone.png", "mimeType": "image/png", "parents": [FOLDER]})
    with pytest.raises(ValueError, match="'nope'.*megaphone.png"):
        assets.ensure_asset("nope")


def test_no_folder_configured_uses_the_team_folder(monkeypatch):
    monkeypatch.delenv("GSLIDES_MCP_ASSETS_FOLDER")
    assert assets.folder_id() == assets.DEFAULT_FOLDER


def test_folder_can_be_overridden_by_id_or_url(monkeypatch):
    monkeypatch.setenv("GSLIDES_MCP_ASSETS_FOLDER", "https://drive.google.com/drive/folders/OTHER_1")
    assert assets.folder_id() == "OTHER_1"


# --- draw / card / card_grid / tool wiring ------------------------------------------------

def test_draw_image_op_resolves_assets_through_the_callback():
    seen = []
    reqs, _ = draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 10, "h": 10, "asset": "bolt", "tint": "ink"}],
                                   PERISCOPE, resolve_asset=lambda name, tint: seen.append((name, tint)) or "fid1")
    assert seen == [("bolt", "ink")]
    assert [r["createImage"]["url"] for r in reqs if "createImage" in r] == ["https://drive.google.com/uc?export=view&id=fid1"]
    with pytest.raises(ValueError, match="asset"):
        draw.ops_to_requests("s", [{"op": "image", "x": 0, "y": 0, "w": 10, "h": 10, "asset": "bolt"}], PERISCOPE)


def test_card_icon_sits_in_a_white_circle_above_the_label():
    ops, _ = components.render("card", {"icon": "bolt", "label": "Constat", "title": "Un levier", "body": "x"}, PERISCOPE, 200)
    circle = next(o for o in ops if o["op"] == "box" and o.get("shape") == "ELLIPSE")
    image = next(o for o in ops if o["op"] == "image")
    assert circle["fill"] == "background" and circle["w"] == circle["h"] == 44
    assert image["asset"] == "bolt" and image["tint"] == "ink"
    assert circle["x"] < image["x"] < circle["x"] + circle["w"] - image["w"]
    label = next(o for o in ops if o["op"] == "text" and o["style"] == "card_label")
    assert label["y"] > circle["y"] + circle["h"]
    ops, _ = components.render("card", {"variant": "dark", "icon": "bolt", "title": "T"}, PERISCOPE, 200)
    assert next(o for o in ops if o["op"] == "image")["tint"] == "ink"  # circle stays white, picto ink


def test_card_grid_equalises_heights_and_columns():
    cards = [{"icon": "bolt", "label": "Constat", "title": "Un levier", "body": "Une ligne"},
             {"label": "Actif", "title": "Audience", "body": "- a\n- b\n- c\n- d"},
             {"label": "Diffusion", "title": "Mobile", "body": "Court"}]
    ops, height = components.render("card_grid", {"cards": cards, "cols": 3, "gap": 12}, PERISCOPE, 600)
    bgs = [o for o in ops if o["op"] == "box" and o.get("role") == "card"]
    assert len(bgs) == 3
    assert len({b["h"] for b in bgs}) == 1 and bgs[0]["h"] == height
    assert [round(b["x"]) for b in bgs] == [0, 204, 408] and bgs[0]["w"] == pytest.approx(192)


def test_insert_component_resolves_icon_tint_with_the_theme(fake_slides, monkeypatch):
    calls = []
    monkeypatch.setattr(assets, "ensure_asset", lambda name, tint=None: calls.append((name, tint)) or "fid9")
    tools.insert_component("PRES1", "1", "card", {"icon": "bolt", "title": "T"}, x_pt=0, y_pt=0, width_pt=200)
    assert calls == [("bolt", "#002B3C")]
    urls = [r["createImage"]["url"] for r in fake_slides.batches[0] if "createImage" in r]
    assert urls == ["https://drive.google.com/uc?export=view&id=fid9"]


def test_asset_size_is_measured_once_and_cached(fake_drive, tmp_path):
    src = _png(tmp_path / "shot.png")
    fake_drive.store_files.append({"id": "f_shot", "name": "shot.png", "mimeType": "image/png", "parents": [FOLDER],
                                   "bytes": open(src, "rb").read()})
    assert assets.asset_size("shot") == (8, 8)
    assert assets.asset_size("shot") == (8, 8)
    assert len([n for n, _ in fake_drive.calls if n == "files.get_media"]) == 1
    assert json.loads(assets.CACHE.read_text())["_sizes"]["f_shot"] == [8, 8]


def test_browser_takes_the_screenshot_aspect_from_the_asset(fake_slides, fake_drive, monkeypatch):
    monkeypatch.setattr(assets, "ensure_asset", lambda name, tint=None: "fid")
    monkeypatch.setattr(assets, "asset_size", lambda name, tint=None, fid=None: (838, 632))
    out = tools.insert_component("PRES1", "1", "browser", {"image": "laptop-demo"}, x_pt=0, y_pt=0, width_pt=300)
    img = next(r["createImage"] for r in fake_slides.batches[0] if "createImage" in r)
    size = img["elementProperties"]["size"]
    assert size["width"]["magnitude"] / size["height"]["magnitude"] == pytest.approx(838 / 632, rel=1e-3)
    assert out["height_pt"] > 300 / 1.6  # taller than the 16:10 default


def test_laptop_crops_the_screenshot_to_its_screen(fake_slides, fake_drive, monkeypatch):
    monkeypatch.setattr(assets, "ensure_asset", lambda name, tint=None: "fid")
    monkeypatch.setattr(assets, "asset_size", lambda name, tint=None, fid=None: (838, 632))
    tools.insert_component("PRES1", "1", "laptop", {"image": "laptop-demo"}, x_pt=0, y_pt=0, width_pt=300)
    crops = [r["updateImageProperties"]["imageProperties"]["cropProperties"] for r in fake_slides.batches[0] if "updateImageProperties" in r]
    assert crops and crops[0]["topOffset"] > 0 and crops[0]["leftOffset"] == 0  # 1.33 source into a 1.6 screen


def test_list_assets_tool_names_without_extension_nor_tints(fake_drive):
    from gslides_mcp.tools import assets as tool
    fake_drive.store_files += [{"id": "f1", "name": "bolt.png", "mimeType": "image/png", "parents": [FOLDER]},
                               {"id": "f2", "name": "bolt__002b3c.png", "mimeType": "image/png", "parents": [FOLDER]},
                               {"id": "f3", "name": "screen-demo.png", "mimeType": "image/png", "parents": [FOLDER]}]
    out = tool.list_assets()
    assert out["assets"] == ["bolt", "screen-demo"] and out["folder"] == FOLDER and "bolt__002b3c.png" in out["files"]


@pytest.mark.parametrize("tint", [None, "#002B3C"])
def test_hosted_server_never_uploads_a_server_file(fake_drive, tmp_path, monkeypatch, tint):
    monkeypatch.setenv("GSLIDES_MCP_TRANSPORT", "http")
    path = _png(tmp_path / "secret.png")
    with pytest.raises(ValueError, match="Drive assets folder"):
        assets.ensure_asset(path, tint=tint)
    assert _names(fake_drive, "files.create") == []
