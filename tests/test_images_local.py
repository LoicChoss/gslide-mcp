"""insert_image_local: sniff the file, upload to Drive, createImage, always clean up."""

import pytest
from conftest import make_http_error
from PIL import Image as PILImage

from gslides_mcp.tools import images


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "logo.png"
    PILImage.new("RGB", (4, 4), (255, 0, 0)).save(p, "PNG")
    return str(p)


@pytest.fixture
def jpeg(tmp_path):
    p = tmp_path / "photo.jpg"
    PILImage.new("RGB", (4, 4), (0, 255, 0)).save(p, "JPEG")
    return str(p)


def _names(drive):
    return [name for name, _ in drive.calls]


def test_upload_share_insert_then_delete(fake_slides, fake_drive, png):
    out = images.insert_image_local("PRES1", "1", png, x_pt=10, y_pt=20, width_pt=100, height_pt=50)

    assert _names(fake_drive) == ["files.create", "permissions.create", "files.delete"]
    create_kw = fake_drive.calls[0][1]
    assert create_kw["has_media"] is True
    assert create_kw["body"]["mimeType"] == "image/png"
    assert fake_drive.calls[1][1]["body"] == {"type": "anyone", "role": "reader"}
    assert fake_drive.calls[2][1]["fileId"] == "drive_file_1"

    (req,) = fake_slides.batches[0]
    assert req["createImage"]["url"] == "https://drive.google.com/uc?export=view&id=drive_file_1"
    assert req["createImage"]["elementProperties"]["pageObjectId"] == "slide_1"
    assert req["createImage"]["elementProperties"]["transform"]["translateX"] == 10 * 12700
    assert req["createImage"]["elementProperties"]["size"]["width"]["magnitude"] == 100 * 12700

    assert out == {"object_id": "gen_image_1", "slide_id": "slide_1", "mime_type": "image/png",
                   "drive_file_id": None, "warning": None}


def test_jpeg_is_detected_by_magic_bytes_not_extension(fake_slides, fake_drive, jpeg, tmp_path):
    renamed = tmp_path / "actually_jpeg.png"
    renamed.write_bytes(open(jpeg, "rb").read())
    out = images.insert_image_local("PRES1", "1", str(renamed), x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert out["mime_type"] == "image/jpeg"
    assert fake_drive.calls[0][1]["body"]["mimeType"] == "image/jpeg"


def test_non_image_is_rejected_before_any_upload(fake_slides, fake_drive, tmp_path):
    bad = tmp_path / "notes.png"
    bad.write_text("this is not an image")
    with pytest.raises(ValueError, match="PNG, JPEG or GIF"):
        images.insert_image_local("PRES1", "1", str(bad), x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert fake_drive.calls == []


def test_missing_file_named(fake_slides, fake_drive, tmp_path):
    with pytest.raises(ValueError, match="nope.png"):
        images.insert_image_local("PRES1", "1", str(tmp_path / "nope.png"), x_pt=0, y_pt=0, width_pt=10, height_pt=10)


def test_oversized_file_rejected(fake_slides, fake_drive, png, monkeypatch):
    monkeypatch.setattr(images, "_MAX_BYTES", 10)
    with pytest.raises(ValueError, match="50 MB"):
        images.insert_image_local("PRES1", "1", png, x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert fake_drive.calls == []


def test_drive_file_deleted_even_when_create_image_fails(fake_slides, fake_drive, png):
    fake_slides.fail_next_batch = make_http_error(400, "bad image")
    with pytest.raises(Exception, match="bad image"):
        images.insert_image_local("PRES1", "1", png, x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert _names(fake_drive)[-1] == "files.delete"


def test_delete_failure_reports_public_leftover(fake_slides, fake_drive, png):
    fake_drive.fail["files.delete"] = make_http_error(500, "drive down")
    fake_drive.fail["permissions.delete"] = make_http_error(500, "drive down")
    out = images.insert_image_local("PRES1", "1", png, x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert out["object_id"] == "gen_image_1"
    assert out["drive_file_id"] == "drive_file_1"
    assert "public" in out["warning"] and "drive_file_1" in out["warning"]


def test_delete_failure_but_permission_revoked(fake_slides, fake_drive, png):
    fake_drive.fail["files.delete"] = make_http_error(500, "drive down")
    out = images.insert_image_local("PRES1", "1", png, x_pt=0, y_pt=0, width_pt=10, height_pt=10)
    assert out["drive_file_id"] == "drive_file_1"
    assert "no longer public" in out["warning"]
    assert ("permissions.delete", {"fileId": "drive_file_1", "permissionId": "anyoneWithLink"}) in fake_drive.calls
