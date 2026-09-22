"""Themes: the single place where colors, roles, font and text styles live.

Components and draw ops never carry a hex value or a point size of their
own — they name a *role* (``accent``, ``ink``, ``surface``…) or a *text
style* (``kpi_value``, ``label``…) and the theme resolves it. Changing how
a brand colors things means editing one JSON file, not every component.

Built-in themes ship next to this module (``periscope.json``,
``default.json``); user themes in ``~/.gslides-mcp/themes/<name>.json`` are
added to the catalogue and may ``"extends"`` another theme.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..util import hex_to_rgb01

BUILTIN_THEME_DIR = Path(__file__).parent
USER_THEME_DIR = Path.home() / ".gslides-mcp" / "themes"

_STYLE_KEYS = ("size", "bold", "italic", "color", "font", "highlight")


@dataclass
class Theme:
    name: str
    colors: dict[str, str] = field(default_factory=dict)      # token -> "#RRGGBB"
    roles: dict[str, str] = field(default_factory=dict)       # role -> token (or hex)
    font: str = "Arial"
    text_styles: dict[str, dict] = field(default_factory=dict)  # name -> {size, bold, italic, color, font}
    description: str = ""
    text_rules: dict = field(default_factory=dict)  # {min_size, small_min_size, small_styles, exempt_styles}

    def size_floor(self, style: str | None) -> float | None:
        """Smallest font size allowed for a text in ``style`` (None = no rule)."""
        rules = self.text_rules
        if not rules or style in rules.get("exempt_styles", ()):
            return None
        if style in rules.get("small_styles", ()):
            return rules.get("small_min_size", rules.get("min_size"))
        return rules.get("min_size")

    def color(self, value) -> dict:
        """Resolve a hex string, a palette token, a role, or an rgb dict."""
        if isinstance(value, dict):
            return value
        seen: set[str] = set()
        v = str(value)
        while not v.startswith("#"):
            if v in seen:
                raise ValueError(f"theme {self.name!r}: color role {value!r} loops")
            seen.add(v)
            if v in self.roles and self.roles[v] != v:  # a role may share its token's name
                v = self.roles[v]
            elif v in self.colors:
                v = self.colors[v]
            else:
                raise ValueError(
                    f"unknown color {value!r} in theme {self.name!r}; roles: "
                    f"{', '.join(sorted(self.roles)) or 'none'}; tokens: "
                    f"{', '.join(sorted(self.colors)) or 'none'} (or pass '#RRGGBB')"
                )
        r, g, b = hex_to_rgb01(v)
        return {"red": r, "green": g, "blue": b}

    def tint(self, value, amount: float) -> str:
        """``value`` mixed with white by ``amount`` (0 = unchanged, 1 = white), as '#RRGGBB'.

        The lighter N-1 series next to an N series, the pale track behind a
        bar: derived from a theme colour, so a brand change carries over.
        """
        c = self.color(value)
        a = max(0.0, min(1.0, float(amount)))
        parts = (round((c[k] + (1 - c[k]) * a) * 255) for k in ("red", "green", "blue"))
        return "#{:02X}{:02X}{:02X}".format(*parts)

    def is_dark(self, value) -> bool:
        """True when text on ``value`` should be light (relative luminance under 0.45)."""
        c = self.color(value)

        def lin(ch: float) -> float:
            return ch / 12.92 if ch <= 0.04045 else ((ch + 0.055) / 1.055) ** 2.4

        lum = 0.2126 * lin(c["red"]) + 0.7152 * lin(c["green"]) + 0.0722 * lin(c["blue"])
        return lum < 0.45

    def text_style(self, name: str | None, **overrides) -> dict:
        """Named text style merged with non-None overrides; always carries a font."""
        style: dict = {"font": self.font}
        if name:
            if name not in self.text_styles:
                raise ValueError(
                    f"unknown text style {name!r} in theme {self.name!r}; available: "
                    f"{', '.join(sorted(self.text_styles))}"
                )
            style.update(self.text_styles[name])
        style.update({k: v for k, v in overrides.items() if v is not None and k in _STYLE_KEYS})
        floor = self.size_floor(name)
        if floor is not None and style.get("size") is not None and style["size"] < floor:
            style["size"] = floor  # charter floor: body ≥ min_size, labels ≥ small_min_size, tables exempt
        return style


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _find(name: str) -> Path | None:
    for base in (USER_THEME_DIR, BUILTIN_THEME_DIR):
        p = base / f"{name}.json"
        if p.is_file():
            return p
    return None


def available() -> list[str]:
    names = {p.stem for p in BUILTIN_THEME_DIR.glob("*.json")}
    if USER_THEME_DIR.is_dir():
        names |= {p.stem for p in USER_THEME_DIR.glob("*.json")}
    return sorted(names)


def load(name: str = "default", _stack: tuple[str, ...] = ()) -> Theme:
    """Load a theme by name, applying its ``extends`` chain (user dir first)."""
    if name in _stack:
        raise ValueError(f"theme {name!r} extends itself ({' -> '.join(_stack + (name,))})")
    path = _find(name)
    if path is None:
        raise ValueError(f"unknown theme {name!r}; available: {', '.join(available())}")
    data = _read(path)
    base = load(data["extends"], _stack + (name,)) if data.get("extends") else Theme(name=name)
    styles = {k: dict(v) for k, v in base.text_styles.items()}
    for k, v in data.get("text_styles", {}).items():
        styles.setdefault(k, {}).update(v)
    return Theme(
        name=name,
        colors={**base.colors, **data.get("colors", {})},
        roles={**base.roles, **data.get("roles", {})},
        font=data.get("font", base.font),
        text_styles=styles,
        description=data.get("description", base.description),
        text_rules={**base.text_rules, **data.get("text_rules", {})},
    )
