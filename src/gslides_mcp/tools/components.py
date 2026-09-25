"""Component tools: list_components, insert_component, draw, save_component, delete_component.

Components are rendered by ``gslides_mcp.components`` onto the ``draw`` ops
canvas and styled by a theme (``gslides_mcp.themes``); every insert is one
``batchUpdate`` grouped into a single element. The default theme comes from
``GSLIDES_MCP_THEME`` (``periscope`` when unset).
"""

from __future__ import annotations

import os
import uuid

from .. import assets
from .. import components as registry
from .. import draw as drawing
from .. import themes
from ..app import ADDITIVE, DESTRUCTIVE, READ_ONLY, mcp
from ..auth import slide_service
from ..components import recipes
from ..util import parse_pres_id, resolve_slide_ids

DEFAULT_THEME = os.environ.get("GSLIDES_MCP_THEME", "periscope")

_HOW_TO_ADD = (
    "Draw the element with `draw` (ops: box, text, line, polyline, arc, ring, table, image). "
    "When it looks right, freeze it as a recipe with `save_component`: same ops with "
    "{prop} placeholders in strings, expressions in numeric keys (\"i * 70\", \"w / 2\") and "
    "`each` blocks over list props. It then appears here with source 'recipe' and works "
    "with `insert_component` like a built-in."
)

_DRAW_HINT = (
    "Reusable? Save these ops as a component with save_component — replace the values "
    "that vary with {prop} placeholders."
)


def _theme(name: str | None) -> themes.Theme:
    return themes.load(name or DEFAULT_THEME)


def _hex(rgb: dict) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(round(rgb.get(k, 0) * 255) for k in ("red", "green", "blue")))


def _resolver(theme: themes.Theme):
    """Asset names → (Drive id, natural size); tints are theme roles resolved to hex."""
    def resolve(name, tint=None):
        hex_tint = _hex(theme.color(tint)) if tint else None
        fid = assets.ensure_asset(name, tint=hex_tint)
        try:
            return fid, assets.asset_size(name, hex_tint, fid)
        except Exception:
            return fid  # size unknown: no cover crop, the image is stretched to its box
    return resolve


def _fill_image_aspects(component: str, props: dict | None) -> dict:
    """``browser``-style components follow the source's aspect unless told otherwise."""
    props = dict(props or {})
    spec = registry.get(component)
    for prop in spec.props:
        aspect_key = f"{prop.name}_aspect"
        if prop.type == "image" and props.get(prop.name) and aspect_key not in props \
                and component == "browser":
            try:
                w, h = assets.asset_size(str(props[prop.name]))
                props[aspect_key] = w / h
            except Exception:
                pass  # keep the component default
    return props


@mcp.tool(annotations=READ_ONLY)
def list_components(theme: str | None = None) -> dict:
    """Catalogue of insertable components and available themes.

    Each entry gives ``description`` (what it draws), ``use`` (when to pick
    it, with the close alternatives — a component fits several intents, so
    read ``use`` before choosing), the props (type, default, choices,
    required), an example call, optional ``variants`` (other ready-made
    settings of the same component: ``title`` = what it looks like,
    ``when`` = the situation it fits, ``props`` = the call to copy) and
    its source: ``builtin`` (Python) or ``recipe`` (JSON saved with
    ``save_component``). Themes carry the
    brand — colors, font, text styles — so the same component renders in
    any charter.

    Args:
        theme: theme to validate and report (default: ``GSLIDES_MCP_THEME``
            or ``periscope``).

    Returns: ``{default_theme, theme, themes, components: [...], how_to_add}``.

    Example: ``list_components()["components"][0]``
    """
    t = _theme(theme)
    out = {
        "default_theme": DEFAULT_THEME,
        "theme": t.name,
        "themes": themes.available(),
        "components": registry.catalogue(),
        "how_to_add": _HOW_TO_ADD,
    }
    try:
        out["assets"] = assets.list_assets()
    except Exception as exc:  # no folder configured, or Drive unreachable: the catalogue still works
        out["assets_error"] = str(exc)
    return out


@mcp.tool(annotations=ADDITIVE)
def insert_component(
    presentation: str,
    slide: str,
    component: str,
    props: dict | None = None,
    x_pt: float = 0,
    y_pt: float = 0,
    width_pt: float = 300,
    height_pt: float | None = None,
    theme: str | None = None,
) -> dict:
    """Render a component on a slide — one batchUpdate, grouped as one element.

    Args:
        slide: 1-based index or objectId.
        component: name from ``list_components`` (``kpi``, ``card``,
            ``callout``, ``table``, ``chart_bars``, ``donut``… or a recipe).
        props: the component's props (see the catalogue for the schema).
        x_pt, y_pt: top-left corner on the slide, in points.
        width_pt: width the component lays itself out in.
        height_pt: forced height; default is the component's natural height.
        theme: theme name (default ``periscope``).

    Returns: ``{component, theme, slide_id, group_id, element_ids, height_pt,
    requests}`` — ``group_id`` is the element to move/delete afterwards
    (``None`` when the component is a single element).

    Example::

        insert_component(deck, 5, "kpi_grid", {"items": [
            {"value": "12 400", "label": "Sessions", "delta": "+8 %"},
            {"value": "3,2 %", "label": "CTR", "delta": "-0,4 pt"}], "cols": 2},
            x_pt=40, y_pt=120, width_pt=640)
    """
    t = _theme(theme)
    props = _fill_image_aspects(component, props)
    ops, height = registry.render(component, props, t, width_pt, height_pt)  # fails before any write
    pid = parse_pres_id(presentation)
    svc = slide_service()
    sid = resolve_slide_ids(svc, pid, [slide])[0]
    gid = f"cmp_{uuid.uuid4().hex[:10]}"
    # a table cannot be grouped with other elements: components built around one stay ungrouped
    group = None if any(o.get("op") == "table" for o in ops) else gid
    reqs, ids = drawing.ops_to_requests(sid, ops, t, prefix=gid, offset=(x_pt, y_pt), group=group, resolve_asset=_resolver(t))
    svc.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute(num_retries=5)
    return {
        "component": component,
        "theme": t.name,
        "slide_id": sid,
        "group_id": gid if (group and len(ids) >= 2) else None,
        "element_ids": ids,
        "height_pt": height,
        "requests": len(reqs),
    }


@mcp.tool(annotations=ADDITIVE)
def draw(
    presentation: str,
    slide: str,
    ops: list[dict],
    x_pt: float = 0,
    y_pt: float = 0,
    theme: str | None = None,
    group: bool = True,
) -> dict:
    """Draw primitive ops on a slide in one batchUpdate.

    Ops (coordinates in points, relative to ``x_pt``/``y_pt``; colors are
    theme roles like ``accent``/``ink``/``surface``, palette tokens, or
    ``#RRGGBB``; text takes a named ``style`` from the theme):

    - ``box`` x y w h [fill] [line {color, weight}] [shape] [text|markdown|runs …]
    - ``text`` x y w h text | markdown | runs=[[{text, bold, italic, color, size}], …] [style] [align] [valign]
    - ``line`` x1 y1 x2 y2 [color] [weight] [dash]
    - ``polyline`` points=[[x, y], …] [color] [weight] [dash]
    - ``arc`` cx cy r a0 a1 weight [color] — degrees, 0 = east, clockwise
    - ``ring`` cx cy r thickness segments=[{value, color}] [start]
    - ``table`` x y w rows [col_w] [row_h] [header] [banding] [borders] [align]
    - ``image`` x y w h drive_file_id | url | asset [tint] — ``asset`` names a PNG of the Drive assets folder

    Args:
        group: group everything into one element (default True).

    Returns: ``{slide_id, group_id, element_ids, requests, hint}``.

    Example: ``draw(deck, 3, [{"op": "box", "x": 0, "y": 0, "w": 120, "h": 24,
    "fill": "accent", "text": "NOUVEAU", "style": "badge", "align": "CENTER",
    "valign": "MIDDLE"}], x_pt=40, y_pt=80)``
    """
    t = _theme(theme)
    pid = parse_pres_id(presentation)
    gid = f"drw_{uuid.uuid4().hex[:10]}"
    svc = slide_service()
    sid = resolve_slide_ids(svc, pid, [slide])[0]
    # translation raises on a bad op before anything is written
    reqs, ids = drawing.ops_to_requests(sid, ops, t, prefix=gid, offset=(x_pt, y_pt), group=gid if group else None,
                                        resolve_asset=_resolver(t))
    svc.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute(num_retries=5)
    return {
        "slide_id": sid,
        "group_id": gid if group and len(ids) >= 2 else None,
        "element_ids": ids,
        "requests": len(reqs),
        "hint": _DRAW_HINT,
    }


@mcp.tool(annotations=ADDITIVE)
def save_component(recipe: dict) -> dict:
    """Save a JSON recipe as a reusable component (``~/.gslides-mcp/components``).

    The recipe is validated and dry-rendered with sample props before being
    written; a broken op is reported with its index. Shape::

        {"name": "pill_row", "description": "…", "use": "when to pick it (optional)",
         "props": {"items": {"type": "list", "description": "…", "required": true},
                   "fill": {"type": "color", "description": "…", "default": "accent"}},
         "height": "16",
         "ops": [{"each": "items", "ops": [
                    {"op": "box", "x": "i * 70", "y": 0, "w": 64, "h": 16,
                     "fill": "{fill}", "text": "{item}", "style": "badge"}]}]}

    Numeric keys are expressions over the props plus ``w``, ``h`` and, in an
    ``each`` block, ``i``/``n``/the item (``"w / 2"``, ``"len(items) * 26"``);
    string keys are templates whose braces hold expressions (``"{item}"``,
    ``"{row.name}"``, ``"{len(items)} pastilles"``). Names can't shadow built-ins.

    Returns: ``{saved: path, component: catalogue entry}``.
    """
    path = recipes.save(recipe)
    return {"saved": str(path), "component": registry.get(recipe["name"]).schema()}


@mcp.tool(annotations=DESTRUCTIVE)
def delete_component(name: str) -> dict:
    """Delete a saved recipe (built-ins can't be deleted). Returns ``{deleted}``."""
    recipes.delete(name)
    return {"deleted": name}
