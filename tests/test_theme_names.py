"""A theme name becomes a file path: anything but a plain name is unknown."""

import pytest

from gslides_mcp import themes


@pytest.mark.parametrize("name", ["../secrets", r"..\x", "/etc/passwd", "a/b"])
def test_path_like_theme_names_are_unknown(name):
    with pytest.raises(ValueError, match="unknown theme"):
        themes.load(name)


def test_builtin_themes_still_load():
    assert themes.load("periscope").name == "periscope"
