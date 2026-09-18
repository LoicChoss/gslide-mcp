"""Shared chart furniture: a graduated Y axis with grid, French value formatting,
period dividers (« ISF | IFI »), and the combo chart (bars + line on a right axis).

Everything is boxes, lines and text: no chart objects, no Sheets.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import INSETS, _nice_max
from .diagrams import _fmt_fr

TICKS = 4  # grid steps above the baseline


def fmt_value(v: float, unit: str | None) -> str:
    """4000000 → '4 000 000 €' (unit glued with a narrow no-break space when it is a symbol)."""
    txt = _fmt_fr(float(v))
    unit = unit or ""
    if unit and not unit.startswith(" "):
        unit = " " + unit
    return txt + unit


def axis_width(vmax: float, unit: str | None) -> float:
    """Left margin needed for the tick labels (10 pt axis style)."""
    longest = max(len(fmt_value(vmax * k / TICKS, unit)) for k in range(TICKS + 1))
    return longest * 5.6 + 22  # glyphs + Google's fixed left/right insets


def y_axis_ops(px: float, py: float, pw: float, ph: float, vmax: float, unit: str | None, *,
               side: str = "left", label_w: float = 60.0, color: str | None = None) -> list[dict]:
    """Grid lines across the plot and tick labels on one side (baseline drawn by the caller)."""
    ops: list[dict] = []
    for k in range(1, TICKS + 1):
        t = vmax * k / TICKS
        y = py + ph - ph * k / TICKS
        if side == "left":
            ops.append({"op": "line", "x1": px, "y1": y, "x2": px + pw, "y2": y, "color": "grid", "weight": 0.75, "role": "grid"})
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
    labels = [str(lb) for lb in p["labels"]]
    n = max(1, len(labels))
    bars, line = dict(p["bars"]), dict(p["line"])
    bvals = [float(v or 0) for v in bars.get("values", [])]
    lvals = [None if v is None else float(v) for v in line.get("values", [])]
    bcol = bars.get("color") or "series_5"
    lcol = line.get("color") or "series_6"
    unit, unit2 = p["unit"], p["unit2"]
    vmax = float(p["y_max"]) if p["y_max"] else _nice_max(bvals)
    vmax2 = float(p["y2_max"]) if p["y2_max"] else _nice_max([v for v in lvals if v is not None])
    height = h or 220
    legend_h = 24.0 if p["legend"] else 0.0
    value_h = 14.0 + INSETS
    ml = axis_width(vmax, unit) + 6 if p["y_axis"] else 0.0
    mr = axis_width(vmax2, unit2) + 6 if p["y_axis"] else 0.0
    mt = (value_h + 4 if p["show_values"] else 6.0) + divider_height(p["dividers"])
    mb = 22.0 + legend_h
    px, py, pw, ph = ml, mt, w - ml - mr, height - mt - mb
    slot = pw / n
    bar_w = slot * 0.62

    def X(i: int) -> float:
        return px + (i + 0.5) * slot

    def Y(v: float) -> float:
        return py + ph - ph * v / vmax

    def Y2(v: float) -> float:
        return py + ph - ph * v / vmax2

    ops: list[dict] = []
    if p["y_axis"]:
        ops += y_axis_ops(px, py, pw, ph, vmax, unit, side="left", label_w=ml - 6)
        ops += y_axis_ops(px, py, pw, ph, vmax2, unit2, side="right", label_w=mr - 6)
    ops.append({"op": "line", "x1": px, "y1": py + ph, "x2": px + pw, "y2": py + ph, "color": "ink", "weight": 1.5, "role": "baseline"})
    for i, lb in enumerate(labels):
        v = bvals[i] if i < len(bvals) else 0.0
        bh = ph * v / vmax
        ops.append({"op": "box", "x": X(i) - bar_w / 2, "y": Y(v), "w": bar_w, "h": bh, "fill": bcol, "role": "bar"})
        if p["show_values"] and i < len(bvals):
            ops.append({"op": "text", "x": X(i) - slot / 2, "y": Y(v) - value_h + 2, "w": slot, "h": value_h, "text": fmt_value(v, unit),
                        "style": "chart_value", "color": bcol, "align": "CENTER", "role": "bar_value"})
        ops.append({"op": "text", "x": X(i) - slot / 2, "y": py + ph + 3, "w": slot, "h": 14 + INSETS, "text": lb,
                    "style": "chart_label", "align": "CENTER", "role": "label"})
    ops += divider_ops(p["dividers"], labels, px, py, slot, ph)
    pts = [[X(i), Y2(v)] for i, v in enumerate(lvals) if v is not None]
    if len(pts) >= 2:
        ops.append({"op": "polyline", "points": pts, "color": lcol, "weight": 3, "role": "line"})
    for i, v in enumerate(lvals):
        if v is None:
            continue
        x, y = X(i), Y2(v)
        ops.append({"op": "box", "x": x - 4.5, "y": y - 4.5, "w": 9, "h": 9, "shape": "ELLIPSE", "fill": lcol,
                    "line": {"color": "background", "weight": 1.5}, "role": "marker"})
        if p["show_values"]:
            bar_top = Y(bvals[i]) if i < len(bvals) else py + ph
            label_y = y - 6 - value_h
            bar_label = (bar_top - value_h + 2, bar_top + 2)  # where the bar's own value sits
            # above the marker, unless that would run off the top or overlap the bar's value label
            if label_y < py - value_h or (label_y < bar_label[1] and label_y + value_h > bar_label[0]):
                label_y = y + 6
            ops.append({"op": "text", "x": x - slot / 2, "y": label_y, "w": slot, "h": value_h, "text": fmt_value(v, unit2),
                        "style": "chart_value", "color": lcol, "align": "CENTER", "role": "point_value"})
    if p["legend"]:
        ly = height - legend_h + 4
        lx = px
        ops.append({"op": "box", "x": lx, "y": ly + 6, "w": 10, "h": 10, "fill": bcol, "role": "swatch"})
        bname = str(bars.get("name", "")); tw = len(bname) * 5.6 + 22
        ops.append({"op": "text", "x": lx + 14, "y": ly, "w": tw, "h": 21, "text": bname, "style": "legend", "valign": "MIDDLE"})
        lx += 14 + tw + 12
        ops.append({"op": "line", "x1": lx, "y1": ly + 11, "x2": lx + 18, "y2": ly + 11, "color": lcol, "weight": 3})
        ops.append({"op": "box", "x": lx + 5, "y": ly + 7, "w": 8, "h": 8, "shape": "ELLIPSE", "fill": lcol, "role": "swatch"})
        lname = str(line.get("name", "")); tw = len(lname) * 5.6 + 22
        ops.append({"op": "text", "x": lx + 22, "y": ly, "w": tw, "h": 21, "text": lname, "style": "legend", "valign": "MIDDLE"})
    return ops, height


register(Component(
    name="chart_combo", description="Barres (axe gauche) + courbe à marqueurs (axe droit) sur la même échelle horizontale : valeurs sur les barres et sur les points, deux axes gradués, légende.",
    props=[
        Prop("labels", "list", "Libellés de l'axe horizontal (années, mois…).", required=True),
        Prop("bars", "dict", "Série en barres : {name, values, color?} (axe gauche).", required=True),
        Prop("line", "dict", "Série en courbe : {name, values (null = trou), color?} (axe droit).", required=True),
        Prop("unit", "str", "Unité des barres, ex. '€'."),
        Prop("unit2", "str", "Unité de la courbe."),
        Prop("y_max", "number", "Échelle des barres (défaut : arrondi au-dessus du max)."),
        Prop("y2_max", "number", "Échelle de la courbe."),
        Prop("y_axis", "bool", "Axes gradués avec grille.", default=True),
        Prop("show_values", "bool", "Valeurs sur les barres et les points.", default=True),
        Prop("legend", "bool", "Légende sous le graphique.", default=True),
        Prop("dividers", "list", "Séparateurs de périodes : {after: libellé, left?, right?, color?, dash?}.", default=[]),
    ],
    render=_chart_combo,
    example={"labels": ["2021", "2022", "2023", "2024", "2025", "2026"],
             "bars": {"name": "Collecte annuelle", "values": [664974, 1085349, 826300, 1152729, 1067244, 708134]},
             "line": {"name": "Nombre de dons", "values": [524, 780, 497, 780, 404, 259]},
             "unit": "€"},
    tags=["graphiques"],
))
