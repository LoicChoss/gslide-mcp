"""Shared chart furniture: the common chart style (thin lines, light grid, light
baseline, small markers), a graduated Y axis, French value formatting, label
thinning, legends, period dividers (« ISF | IFI »), the optional title / panel
frame, and the combo chart (bars + line on a right axis).

Everything is boxes, lines and text: no chart objects, no Sheets. The style
follows the agency's generated PPTX bilans: the chart is quiet (grid 0.5 pt,
no ink axis) so the data carries the colour.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import GLYPH, INSET_X, INSETS, _nice_max
from .diagrams import _fmt_fr

TICKS = 4  # grid steps above the baseline
GRID_W = 0.5      # grid lines
AXIS_W = 1.0      # baseline
LINE_W = 1.5      # series lines
MARKER = 4.0      # marker diameter
AUTO_MAX = 12     # markers and values are shown automatically up to this many points
LEGEND_H = 21.0
PANEL_PAD = 10.0
TITLE_H = 14.0 + INSETS


def fmt_value(v: float, unit: str | None) -> str:
    """4000000 → '4 000 000 €' (unit glued with a narrow no-break space when it is a symbol)."""
    txt = _fmt_fr(float(v))
    unit = unit or ""
    if unit and not unit.startswith((" ", " ")):
        unit = " " + unit
    return txt + unit


def axis_width(vmax: float, unit: str | None) -> float:
    """Left margin needed for the tick labels (10 pt axis style)."""
    longest = max(len(fmt_value(vmax * k / TICKS, unit)) for k in range(TICKS + 1))
    return longest * 5.6 + 22  # glyphs + Google's fixed left/right insets


def auto(value, n: int) -> bool:
    """Resolve an 'auto' | bool prop: auto = on while there are at most AUTO_MAX points."""
    if value is None or str(value).lower() == "auto":
        return n <= AUTO_MAX
    if isinstance(value, str):
        return value.lower() in ("true", "on", "yes", "1")
    return bool(value)


def baseline_op(px: float, y: float, pw: float) -> dict:
    return {"op": "line", "x1": px, "y1": y, "x2": px + pw, "y2": y, "color": "chart_axis", "weight": AXIS_W, "role": "baseline"}


def y_axis_ops(px: float, py: float, pw: float, ph: float, vmax: float, unit: str | None, *,
               side: str = "left", label_w: float = 60.0, color: str | None = None) -> list[dict]:
    """Grid lines across the plot and tick labels on one side (baseline drawn by the caller)."""
    ops: list[dict] = []
    for k in range(1, TICKS + 1):
        t = vmax * k / TICKS
        y = py + ph - ph * k / TICKS
        if side == "left":
            ops.append({"op": "line", "x1": px, "y1": y, "x2": px + pw, "y2": y, "color": "chart_grid", "weight": GRID_W, "role": "grid"})
            ops.append({"op": "text", "x": px - label_w - 4, "y": y - 11, "w": label_w, "h": 14 + INSETS, "text": fmt_value(t, unit),
                        "style": "axis", "align": "END", "role": "tick", **({"color": color} if color else {})})
        else:
            ops.append({"op": "text", "x": px + pw + 4, "y": y - 11, "w": label_w, "h": 14 + INSETS, "text": fmt_value(t, unit),
                        "style": "axis", "align": "START", "role": "tick2", **({"color": color} if color else {})})
    zero = {"op": "text", "x": px - label_w - 4, "y": py + ph - 11, "w": label_w, "h": 14 + INSETS, "text": fmt_value(0, unit),
            "style": "axis", "align": "END", "role": "tick"}
    if side == "right":
        zero.update({"x": px + pw + 4, "align": "START", "role": "tick2"})
    if color:
        zero["color"] = color
    ops.append(zero)
    return ops


def thin_labels(labels: list, slot: float, size: float = 10.0) -> list[str | None]:
    """Keep one label in k when a slot is narrower than a label; first and last always stay.

    Google cannot rotate a text box through the ops, so a dense axis (31
    days) shows every third or fourth date instead of overlapping them.
    """
    labels = [str(lb) for lb in labels]
    n = len(labels)
    if n == 0:
        return []
    need = max(len(lb) for lb in labels) * size * GLYPH + 2 * INSET_X
    k = max(1, -(-need // slot)) if slot > 0 else 1
    if k == 1:
        return list(labels)
    keep = {i for i in range(n) if i % k == 0}
    last = n - 1
    if last not in keep:
        keep = {i for i in keep if last - i >= k} | {last}
    return [lb if i in keep else None for i, lb in enumerate(labels)]


def legend_ops(entries: list[dict], x: float, y: float, w: float, pos: str = "bottom") -> tuple[list[dict], float]:
    """A legend line: swatch (box) or short line per entry; centred when ``pos`` is 'top'.

    entries: ``[{name, color, kind?: 'box' | 'line'}]``. Returns (ops, height).
    """
    if pos == "none" or not entries:
        return [], 0.0
    items = []
    for e in entries:
        name = str(e.get("name", ""))
        tw = len(name) * 5.6 + 2 * INSET_X + 4
        items.append((name, e.get("color") or "accent", e.get("kind", "box"), tw))
    total = sum(18 + tw + 10 for _, _, _, tw in items) - 10
    lx = x + max(0.0, (w - total) / 2) if pos == "top" else x
    ops: list[dict] = []
    for name, color, kind, tw in items:
        if kind == "line":
            ops.append({"op": "line", "x1": lx, "y1": y + LEGEND_H / 2, "x2": lx + 14, "y2": y + LEGEND_H / 2, "color": color,
                        "weight": LINE_W, "role": "swatch"})
        else:
            ops.append({"op": "box", "x": lx, "y": y + LEGEND_H / 2 - 4, "w": 8, "h": 8, "fill": color, "role": "swatch"})
        ops.append({"op": "text", "x": lx + 16, "y": y, "w": tw, "h": LEGEND_H, "text": name, "style": "legend", "valign": "MIDDLE"})
        lx += 18 + tw + 10
    return ops, LEGEND_H


def inner_width(w: float, p: dict) -> float:
    """Width left for the plot once the optional panel padding is taken."""
    return w - 2 * PANEL_PAD if p.get("panel") else w


def panelize(ops: list[dict], height: float, w: float, p: dict) -> tuple[list[dict], float]:
    """Wrap chart ops with an optional centred caption title and a rounded surface panel.

    The ops were rendered at ``inner_width(w, p)``; they are shifted into the
    frame. Returns (ops, total height).
    """
    from . import shift

    title = p.get("title")
    panel = bool(p.get("panel"))
    if not title and not panel:
        return ops, height
    pad = PANEL_PAD if panel else 0.0
    top = pad + (TITLE_H + 2 if title else 0.0)
    out: list[dict] = []
    total = top + height + pad
    if panel:
        out.append({"op": "box", "x": 0, "y": 0, "w": w, "h": total, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "panel"})
    if title:
        out.append({"op": "text", "x": pad, "y": pad, "w": w - 2 * pad, "h": TITLE_H, "text": str(title), "style": "caption",
                    "size": 10.5, "align": "CENTER", "role": "chart_title"})
    out.extend(shift(ops, pad, top))
    return out, total


FRAME_PROPS = [
    Prop("title", "str", "Titre du graphique, en petit et centré au-dessus."),
    Prop("panel", "bool", "Fond gris clair arrondi autour du graphique (style bilan).", default=False),
]


def divider_height(dividers: list) -> float:
    """Vertical room to reserve above the plot for the divider labels (0 when none)."""
    labelled = [d for d in dividers or [] if d.get("left") or d.get("right")]
    return max((float(d.get("size", 20)) * 1.35 + INSETS for d in labelled), default=0.0)


def divider_ops(dividers: list, labels: list[str], px: float, py: float, slot: float, ph: float) -> list[dict]:
    """Vertical rule between two slots with a big label on each side, above the plot (period changes)."""
    ops: list[dict] = []
    for d in dividers or []:
        after = d.get("after")
        idx = labels.index(str(after)) if str(after) in labels else int(after)
        x = px + (idx + 1) * slot
        size = float(d.get("size", 20))
        label_h = size * 1.35 + INSETS
        top = py - label_h if (d.get("left") or d.get("right")) else py - 2
        ops.append({"op": "line", "x1": x, "y1": top, "x2": x, "y2": py + ph, "color": d.get("color") or "divider",
                    "weight": 2, "dash": "DASH" if d.get("dash") else None, "role": "divider"})
        if d.get("left"):
            ops.append({"op": "text", "x": x - 8 - (idx + 1) * slot, "y": py - label_h, "w": (idx + 1) * slot, "h": label_h,
                        "text": str(d["left"]), "style": "stat_label", "size": size, "color": d.get("left_color") or "accent",
                        "align": "END", "role": "divider_label"})
        if d.get("right"):
            ops.append({"op": "text", "x": x + 8, "y": py - label_h, "w": (len(labels) - idx - 1) * slot, "h": label_h,
                        "text": str(d["right"]), "style": "stat_label", "size": size, "color": d.get("right_color") or "ink",
                        "align": "START", "role": "divider_label"})
    return ops


# --- chart_combo --------------------------------------------------------------------------

def _chart_combo(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    w_in = inner_width(w, p)
    labels = [str(lb) for lb in p["labels"]]
    n = max(1, len(labels))
    bars, line = dict(p["bars"]), dict(p["line"])
    bvals = [float(v or 0) for v in bars.get("values", [])]
    lvals = [None if v is None else float(v) for v in line.get("values", [])]
    bcol = bars.get("color") or "series_1"
    lcol = line.get("color") or "series_6"
    unit, unit2 = p["unit"], p["unit2"]
    vmax = float(p["y_max"]) if p["y_max"] else _nice_max(bvals)
    vmax2 = float(p["y2_max"]) if p["y2_max"] else _nice_max([v for v in lvals if v is not None])
    show_values = auto(p["show_values"], n)
    markers = auto(p["markers"], n)
    pos = p["legend_pos"] if p["legend"] else "none"
    entries = [{"name": bars.get("name", ""), "color": bcol}, {"name": line.get("name", ""), "color": lcol, "kind": "line"}]
    legend_h = LEGEND_H + 4 if pos in ("top", "bottom") else 0.0
    frame_h = (TITLE_H + 2 if p.get("title") else 0.0) + (2 * PANEL_PAD if p.get("panel") else 0.0)
    height = (h - frame_h) if h else 220.0
    value_h = 14.0 + INSETS
    ml = axis_width(vmax, unit) + 6 if p["y_axis"] else 0.0
    mr = axis_width(vmax2, unit2) + 6 if p["y_axis"] else 0.0
    mt = (value_h + 4 if show_values else 6.0) + divider_height(p["dividers"]) + (legend_h if pos == "top" else 0.0)
    mb = 22.0 + (legend_h if pos == "bottom" else 0.0)
    px, py, pw, ph = ml, mt, w_in - ml - mr, height - mt - mb
    slot = pw / n
    bar_w = slot * 0.62

    def X(i: int) -> float:
        return px + (i + 0.5) * slot

    def Y(v: float) -> float:
        return py + ph - ph * v / vmax

    def Y2(v: float) -> float:
        return py + ph - ph * v / vmax2

    ops: list[dict] = []
    if pos == "top":
        ops += legend_ops(entries, px, 0, pw, "top")[0]
    if p["y_axis"]:
        ops += y_axis_ops(px, py, pw, ph, vmax, unit, side="left", label_w=ml - 6)
        ops += y_axis_ops(px, py, pw, ph, vmax2, unit2, side="right", label_w=mr - 6)
    ops.append(baseline_op(px, py + ph, pw))
    shown = thin_labels(labels, slot)
    for i, lb in enumerate(labels):
        v = bvals[i] if i < len(bvals) else 0.0
        bh = ph * v / vmax
        ops.append({"op": "box", "x": X(i) - bar_w / 2, "y": Y(v), "w": bar_w, "h": bh, "fill": bcol, "role": "bar"})
        if show_values and i < len(bvals):
            ops.append({"op": "text", "x": X(i) - slot / 2, "y": Y(v) - value_h + 2, "w": slot, "h": value_h, "text": fmt_value(v, unit),
                        "style": "chart_value", "color": bcol, "align": "CENTER", "role": "bar_value"})
        if shown[i]:
            lw = max(slot, 48.0)
            ops.append({"op": "text", "x": X(i) - lw / 2, "y": py + ph + 3, "w": lw, "h": 14 + INSETS, "text": lb,
                        "style": "chart_label", "align": "CENTER", "role": "label"})
    ops += divider_ops(p["dividers"], labels, px, py, slot, ph)
    pts = [[X(i), Y2(v)] for i, v in enumerate(lvals) if v is not None]
    if len(pts) >= 2:
        ops.append({"op": "polyline", "points": pts, "color": lcol, "weight": LINE_W, "role": "line"})
    for i, v in enumerate(lvals):
        if v is None:
            continue
        x, y = X(i), Y2(v)
        if markers:
            ops.append({"op": "box", "x": x - MARKER / 2, "y": y - MARKER / 2, "w": MARKER, "h": MARKER, "shape": "ELLIPSE", "fill": lcol,
                        "line": {"color": "background", "weight": 1}, "role": "marker"})
        if show_values:
            bar_top = Y(bvals[i]) if i < len(bvals) else py + ph
            label_y = y - 6 - value_h
            bar_label = (bar_top - value_h + 2, bar_top + 2)  # where the bar's own value sits
            # above the marker, unless that would run off the top or overlap the bar's value label
            if label_y < py - value_h or (label_y < bar_label[1] and label_y + value_h > bar_label[0]):
                label_y = y + 6
            ops.append({"op": "text", "x": x - slot / 2, "y": label_y, "w": slot, "h": value_h, "text": fmt_value(v, unit2),
                        "style": "chart_value", "color": lcol, "align": "CENTER", "role": "point_value"})
    if pos == "bottom":
        ops += legend_ops(entries, px, height - LEGEND_H, pw, "bottom")[0]
    return panelize(ops, height, w, p)


register(Component(
    name="chart_combo", description="Barres (axe gauche) + courbe fine (axe droit) sur la même échelle horizontale : légende en haut, deux axes gradués, grille légère ; valeurs et marqueurs affichés jusqu'à 12 points.",
    props=[
        Prop("labels", "list", "Libellés de l'axe horizontal (années, mois, jours…).", required=True),
        Prop("bars", "dict", "Série en barres : {name, values, color?} (axe gauche).", required=True),
        Prop("line", "dict", "Série en courbe : {name, values (null = trou), color?} (axe droit).", required=True),
        Prop("unit", "str", "Unité des barres, ex. '€'."),
        Prop("unit2", "str", "Unité de la courbe."),
        Prop("y_max", "number", "Échelle des barres (défaut : arrondi au-dessus du max)."),
        Prop("y2_max", "number", "Échelle de la courbe."),
        Prop("y_axis", "bool", "Axes gradués avec grille.", default=True),
        Prop("show_values", "str", "Valeurs sur les barres et les points : 'auto' (jusqu'à 12 points), true, false.", default="auto"),
        Prop("markers", "str", "Marqueurs sur la courbe : 'auto' (jusqu'à 12 points), true, false.", default="auto"),
        Prop("legend", "bool", "Légende.", default=True),
        Prop("legend_pos", "choice", "Position de la légende.", default="top", choices=["top", "bottom", "none"]),
        Prop("dividers", "list", "Séparateurs de périodes : {after: libellé, left?, right?, color?, dash?}.", default=[]),
        *FRAME_PROPS,
    ],
    render=_chart_combo,
    example={"labels": ["2021", "2022", "2023", "2024", "2025", "2026"],
             "bars": {"name": "Collecte annuelle", "values": [664974, 1085349, 826300, 1152729, 1067244, 708134]},
             "line": {"name": "Nombre de dons", "values": [524, 780, 497, 780, 404, 259], "color": "regie_meta"},
             "unit": "€"},
    tags=["graphiques"],
))
