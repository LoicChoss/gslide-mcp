"""Lot 4 charts: gauge (half ring), target (concentric rings), chart_stacked.

Rings are radial spokes (``ring`` op, ``span`` for partial arcs); bars are
boxes. Series default to the theme's ``series_1…6`` roles.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .axes import axis_width, divider_height, divider_ops, fmt_value, y_axis_ops
from .builtin import INSETS, LEADING, _nice_max


# --- gauge ------------------------------------------------------------------------------

def _gauge(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    value = float(p["value"])
    vmax = float(p["max"]) or 1.0
    r = float(p["size"]) / 2 if p["size"] else min(w / 2, (h - 24) if h else 80)
    cx, cy = w / 2, r + 2
    thickness = float(p["thickness"]) if p["thickness"] else r * 0.3
    frac = max(0.0, min(1.0, value / vmax))
    segments = [{"value": frac, "color": p["color"]}]
    if frac < 1:
        segments.append({"value": 1 - frac, "color": "track"})
    ops: list[dict] = [{"op": "ring", "cx": cx, "cy": cy, "r": r, "thickness": thickness, "segments": segments,
                        "start": 180, "span": 180}]
    text = str(p["text"]) if p["text"] is not None else f"{value:g}".replace(".", ",") + (p["unit"] or "")
    ops.append({"op": "text", "x": cx - r, "y": cy - 30, "w": 2 * r, "h": 28 + INSETS, "text": text, "style": "stat_value",
                "size": float(p["value_size"]), "color": "ink", "align": "CENTER", "valign": "BOTTOM", "role": "value"})
    height = cy + 4
    if p["label"]:
        ops.append({"op": "text", "x": 0, "y": height, "w": w, "h": 14 + INSETS, "text": str(p["label"]), "style": "caption",
                    "size": 10, "align": "CENTER", "role": "label"})
        height += 12 + INSETS
    return ops, h or height


register(Component(
    name="gauge", description="Jauge en demi-anneau : part atteinte en accent sur une piste grise, valeur au centre, libellé dessous.",
    props=[
        Prop("value", "number", "Valeur atteinte.", required=True),
        Prop("max", "number", "Valeur maximale (100 %).", default=100),
        Prop("label", "str", "Libellé sous la jauge."),
        Prop("text", "str", "Texte au centre (défaut : la valeur + unit)."),
        Prop("unit", "str", "Unité accolée à la valeur.", default=""),
        Prop("color", "color", "Couleur de la part atteinte.", default="accent"),
        Prop("size", "number", "Diamètre (défaut : la largeur)."),
        Prop("thickness", "number", "Épaisseur de l'anneau (défaut : 30 % du rayon)."),
        Prop("value_size", "number", "Taille de la valeur.", default=24),
    ],
    render=_gauge, example={"value": 43, "label": "Autorité de domaine", "size": 140}, tags=["graphiques"],
))


# --- target -----------------------------------------------------------------------------

def _target(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    rings = list(p["rings"])
    vmax = float(p["max"]) or 1.0
    legend = p["legend"]
    height = h or 160
    d = min(height, w * 0.5 if legend else w)
    r_out = d / 2
    cx, cy = r_out, height / 2
    thickness = float(p["thickness"])
    gap = float(p["gap"])
    ops: list[dict] = []
    colored = []
    for i, rg in enumerate(rings):
        r = r_out - i * (thickness + gap)
        if r <= thickness / 2:
            break
        frac = max(0.0, min(1.0, float(rg.get("value", 0)) / vmax))
        color = rg.get("color") or f"series_{i % 6 + 1}"
        colored.append((rg, color, frac))
        segments = [{"value": frac, "color": color}]
        if frac < 1:
            segments.append({"value": 1 - frac, "color": "track"})
        ops.append({"op": "ring", "cx": cx, "cy": cy, "r": r, "thickness": thickness, "segments": segments, "start": -90})
    if p["center"]:
        cd = max(4.0, thickness * 0.8)
        ops.append({"op": "box", "x": cx - cd / 2, "y": cy - cd / 2, "w": cd, "h": cd, "shape": "ELLIPSE", "fill": "ink", "role": "center"})
    if legend:
        lx = d + 16
        lw = w - lx
        row = 21.0
        ly = cy - row * len(colored) / 2
        for rg, color, frac in colored:
            ops.append({"op": "box", "x": lx, "y": ly + 4, "w": 10, "h": 10, "fill": color, "role": "swatch"})
            ops.append({"op": "text", "x": lx + 16, "y": ly, "w": lw - 16 - 44, "h": row, "text": str(rg.get("label", "")),
                        "style": "legend", "valign": "MIDDLE"})
            ops.append({"op": "text", "x": lx + lw - 44, "y": ly, "w": 44, "h": row, "text": f"{round(100 * frac)} %",
                        "style": "chart_value", "align": "END", "valign": "MIDDLE"})
            ly += row
    return ops, height


register(Component(
    name="target", description="Cible : anneaux concentriques, chacun rempli à son pourcentage (barres radiales) sur piste grise, légende à droite.",
    props=[
        Prop("rings", "list", "Anneaux, de l'extérieur vers le centre : {label, value, color?}.", required=True),
        Prop("max", "number", "Valeur maximale (100 %).", default=100),
        Prop("thickness", "number", "Épaisseur d'un anneau.", default=12),
        Prop("gap", "number", "Espace entre anneaux.", default=4),
        Prop("center", "bool", "Point central.", default=True),
        Prop("legend", "bool", "Légende à droite avec pourcentages.", default=True),
    ],
    render=_target,
    example={"rings": [{"label": "Tests lancés", "value": 80}, {"label": "Variantes gagnantes", "value": 55}, {"label": "Industrialisées", "value": 30}]},
    tags=["graphiques"],
))


# --- chart_stacked ----------------------------------------------------------------------

def _chart_stacked(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    labels = [str(lb) for lb in p["labels"]]
    series = list(p["series"])
    n = len(labels)
    colors = [s.get("color") or f"series_{i % 6 + 1}" for i, s in enumerate(series)]
    totals = [sum(float((s.get("values") or [0] * n)[i] or 0) for s in series) for i in range(n)]
    vmax = float(p["max"]) if p["max"] else _nice_max(totals)
    unit = p["unit"] or ""
    ops: list[dict] = []
    legend_h = 21.0 if p["legend"] else 0.0
    if p["horizontal"]:
        bar_h, gap = float(p["bar_h"]), float(p["gap"])
        label_w = min(w * 0.35, max(len(lb) for lb in labels) * 6.0 + 14) if labels else 0
        x0 = label_w + 6
        bw = w - x0 - (44 if p["show_values"] else 0)
        for i, lb in enumerate(labels):
            y = i * (bar_h + gap)
            ops.append({"op": "text", "x": 0, "y": y - 2, "w": label_w, "h": bar_h + 4, "text": lb, "style": "chart_label",
                        "align": "END", "valign": "MIDDLE", "role": "label"})
            x = x0
            for s, color in zip(series, colors):
                v = float((s.get("values") or [0] * n)[i] or 0)
                sw = bw * v / vmax
                if sw > 0:
                    ops.append({"op": "box", "x": x, "y": y, "w": sw, "h": bar_h, "fill": color, "role": "segment"})
                    x += sw
            if p["show_values"]:
                ops.append({"op": "text", "x": x + 4, "y": y - 2, "w": 64, "h": bar_h + 4, "text": fmt_value(totals[i], unit),
                            "style": "chart_value", "valign": "MIDDLE", "role": "total"})
        height = n * (bar_h + gap) - gap
        ly = height + 8
    else:
        plot_h = (h or 180) - legend_h - 22
        ml = axis_width(vmax, unit) + 6 if p["y_axis"] else 0.0
        top = (14 + INSETS + 2 if p["show_values"] else 0.0) + divider_height(p["dividers"])
        px, pw = ml, w - ml
        col_w = pw / max(n, 1)
        bar_w = col_w * 0.6
        if p["y_axis"]:
            ops += y_axis_ops(px, top, pw, plot_h - top, vmax, unit, side="left", label_w=ml - 6)
        for i, lb in enumerate(labels):
            x = px + i * col_w + (col_w - bar_w) / 2
            y = plot_h
            for s, color in zip(series, colors):
                v = float((s.get("values") or [0] * n)[i] or 0)
                sh = (plot_h - top) * v / vmax
                if sh > 0:
                    y -= sh
                    ops.append({"op": "box", "x": x, "y": y, "w": bar_w, "h": sh, "fill": color, "role": "segment"})
            if p["show_values"]:
                ops.append({"op": "text", "x": px + i * col_w, "y": y - 14 - INSETS + 2, "w": col_w, "h": 14 + INSETS,
                            "text": fmt_value(totals[i], unit), "style": "chart_value", "align": "CENTER", "role": "total"})
            ops.append({"op": "text", "x": px + i * col_w, "y": plot_h + 2, "w": col_w, "h": 14 + INSETS, "text": lb, "style": "chart_label",
                        "align": "CENTER", "role": "label"})
        ops += divider_ops(p["dividers"], labels, px, top, col_w, plot_h - top)
        ops.insert(0, {"op": "line", "x1": px, "y1": plot_h, "x2": w, "y2": plot_h, "color": "ink", "weight": 1.5})
        height = plot_h + 22
        ly = height
    if p["legend"]:
        lx = 0.0
        for s, color in zip(series, colors):
            name = str(s.get("name", ""))
            ops.append({"op": "box", "x": lx, "y": ly + 5, "w": 8, "h": 8, "fill": color, "role": "swatch"})
            tw = len(name) * 10 * 0.55 + 22
            ops.append({"op": "text", "x": lx + 11, "y": ly, "w": tw, "h": 21, "text": name, "style": "legend", "valign": "MIDDLE"})
            lx += tw + 14
        height = ly + legend_h
    return ops, h or height


register(Component(
    name="chart_stacked", description="Barres empilées multi-séries, horizontales (par défaut) ou verticales avec axe Y gradué et séparateurs de périodes, totaux optionnels, légende.",
    props=[
        Prop("labels", "list", "Libellés des barres.", required=True),
        Prop("series", "list", "Séries : {name, values, color?}.", required=True),
        Prop("horizontal", "bool", "Barres horizontales.", default=True),
        Prop("max", "number", "Échelle (défaut : total max arrondi)."),
        Prop("unit", "str", "Unité des totaux.", default=""),
        Prop("show_values", "bool", "Afficher le total de chaque barre.", default=False),
        Prop("legend", "bool", "Légende des séries.", default=True),
        Prop("bar_h", "number", "Hauteur des barres (horizontal).", default=16),
        Prop("gap", "number", "Espace entre barres (horizontal).", default=8),
        Prop("y_axis", "bool", "Axe Y gradué avec grille (vertical).", default=False),
        Prop("dividers", "list", "Séparateurs de périodes (vertical) : {after: libellé, left?, right?, color?, dash?}.", default=[]),
    ],
    render=_chart_stacked,
    example={"labels": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022"],
             "series": [{"name": "Collecte (hors digital)", "values": [3300000, 3500000, 3800000, 1100000, 1000000, 1200000, 1150000, 1150000], "color": "series_2"},
                        {"name": "Collecte digitale", "values": [800000, 1200000, 1400000, 500000, 500000, 600000, 650000, 1050000], "color": "series_5"},
                        {"name": "Dons ≥ 1 000 €", "values": [0, 0, 0, 300000, 1300000, 2050000, 1200000, 1400000], "color": "series_3"}],
             "horizontal": False, "y_axis": True, "unit": "€", "show_values": False,
             "dividers": [{"after": "2017", "left": "ISF", "right": "IFI"}]},
    tags=["graphiques"],
))
