"""Bilan média charts: chart_grouped (N vs N-1 side by side, one tint per régie),
donut_row (small donuts with titles), mini_charts (small multiples).

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles only. The N-1 series is a white-mixed tint of the
category colour (``theme.tint``), so « foncé = N, clair = N-1 » holds for
every charter.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register, shift, validate, get
from .axes import (FRAME_PROPS, LEGEND_H, auto, axis_width, baseline_op, fmt_value, inner_width, legend_ops, panelize,
                   thin_labels, value_label, y_axis_ops)
from .builtin import INSETS, _chart_bars, _donut, _frame_h, _nice_max

TINT_STEP = 0.55  # how much whiter each further series gets when categories carry the colour


def _series_fill(theme: Theme, k: int, s: dict, cat_color: str | None) -> str:
    if cat_color:
        return cat_color if k == 0 else theme.tint(cat_color, min(0.85, TINT_STEP * k))
    return s.get("color") or f"series_{k % 6 + 1}"


# --- chart_grouped ----------------------------------------------------------------------

def _chart_grouped(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    w_in = inner_width(w, p)
    labels = [str(lb) for lb in p["labels"]]
    series = list(p["series"])
    cats = list(p["category_colors"] or [])
    n, m = len(labels), max(1, len(series))
    values = [[float((s.get("values") or [0] * n)[i] or 0) for i in range(n)] for s in series]
    vmax = float(p["max"]) if p["max"] else _nice_max([v for row in values for v in row])
    unit = p["unit"] or ""
    show_values = auto(p["show_values"], n * m)
    pos = p["legend_pos"]
    legend_h = LEGEND_H + 4 if pos in ("top", "bottom") else 0.0
    entries = [{"name": str(s.get("name", "")), "color": _series_fill(theme, k, s, cats[0] if cats else None)}
               for k, s in enumerate(series)]
    if cats and m > 1:  # the legend shows the dark / light pairing on a neutral colour
        entries = [{"name": str(s.get("name", "")), "color": "ink" if k == 0 else theme.tint("ink", TINT_STEP * k)}
                   for k, s in enumerate(series)]
    ops: list[dict] = []
    value_h = 14.0 + INSETS

    def fill(k: int, i: int) -> str:
        return _series_fill(theme, k, series[k], cats[i] if i < len(cats) and cats[i] else None)

    if p["horizontal"]:
        bar_h, gap, cat_gap = float(p["bar_h"]), 2.0, 10.0
        label_w = min(w_in * 0.3, max((len(lb) for lb in labels), default=0) * 6.0 + 16)
        x0 = label_w + 6
        bw = w_in - x0 - (60 if show_values else 0)
        y = legend_h if pos == "top" else 0.0
        if pos == "top":
            ops += legend_ops(entries, x0, 0, bw, "top")[0]
        for i, lb in enumerate(labels):
            group_h = m * bar_h + (m - 1) * gap
            ops.append({"op": "text", "x": 0, "y": y, "w": label_w, "h": group_h, "text": lb, "style": "chart_label",
                        "align": "END", "valign": "MIDDLE", "role": "label"})
            for k in range(m):
                v = values[k][i]
                by = y + k * (bar_h + gap)
                ops.append({"op": "box", "x": x0, "y": by, "w": bw * v / vmax, "h": bar_h, "fill": fill(k, i), "role": "bar",
                            "series": k})
                if show_values:
                    ops.append({"op": "text", "x": x0 + bw * v / vmax + 2, "y": by - 4, "w": 80, "h": bar_h + 8,
                                "text": fmt_value(v, unit), "style": "chart_value", "valign": "MIDDLE", "role": "value"})
            y += group_h + cat_gap
        height = y - cat_gap
        if pos == "bottom":
            ops += legend_ops(entries, x0, height + 4, bw, "bottom")[0]
            height += legend_h
        return panelize(ops, height, w, p)

    height = (h - _frame_h(p)) if h else 200.0
    ml = axis_width(vmax, unit) + 6 if p["y_axis"] else 0.0
    top = (value_h + 2 if show_values else 4.0) + (legend_h if pos == "top" else 0.0)
    bottom = 30.0 + (legend_h if pos == "bottom" else 0.0)
    px, pw = ml, w_in - ml
    py, ph = top, height - top - bottom
    slot = pw / max(n, 1)
    inner = slot * 0.72
    bw = (inner - (m - 1) * 2) / m
    if str(p["show_values"]).lower() == "auto" and bw < 40:
        show_values = False  # paired values would touch: no value over narrow bars
    if pos == "top":
        ops += legend_ops(entries, px, 0, pw, "top")[0]
    if p["y_axis"]:
        ops += y_axis_ops(px, py, pw, ph, vmax, unit, side="left", label_w=ml - 6)
    ops.append(baseline_op(px, py + ph, pw))
    shown = thin_labels(labels, slot)
    for i, lb in enumerate(labels):
        gx = px + i * slot + (slot - inner) / 2
        for k in range(m):
            v = values[k][i]
            bh = ph * v / vmax
            x = gx + k * (bw + 2)
            ops.append({"op": "box", "x": x, "y": py + ph - bh, "w": bw, "h": bh, "fill": fill(k, i), "role": "bar", "series": k})
            if show_values:
                ops.append(value_label(x + bw / 2, py + ph - bh - value_h + 3, bw + 2, fmt_value(v, unit), value_h))
        if shown[i]:
            lw = max(slot, 56.0)
            ops.append({"op": "text", "x": px + (i + 0.5) * slot - lw / 2, "y": py + ph + 3, "w": lw, "h": 26 + INSETS, "text": lb,
                        "style": "chart_label", "align": "CENTER", "role": "label"})
    if pos == "bottom":
        ops += legend_ops(entries, px, height - LEGEND_H, pw, "bottom")[0]
    return panelize(ops, height, w, p)


register(Component(
    name="chart_grouped",
    description="Barres groupées : plusieurs séries côte à côte par catégorie (N foncé / N-1 clair, une teinte par régie avec category_colors), vertical ou horizontal, axe gradué, légende en haut.",
    props=[
        Prop("labels", "list", "Catégories (régies, canaux, familles…).", required=True),
        Prop("series", "list", "Séries : {name, values, color?}. La première est N, la suivante N-1.", required=True),
        Prop("category_colors", "list", "Une couleur par catégorie (ex. regie_google) : la série k prend une teinte plus claire de la couleur de sa catégorie."),
        Prop("horizontal", "bool", "Barres horizontales (libellés à gauche, valeurs au bout).", default=False),
        Prop("unit", "str", "Unité des valeurs, ex. '€'."),
        Prop("max", "number", "Échelle (défaut : arrondi au-dessus du max)."),
        Prop("y_axis", "bool", "Axe Y gradué avec grille (vertical).", default=True),
        Prop("show_values", "str", "Valeurs sur les barres : 'auto' (jusqu'à 12 barres), true, false.", default="auto"),
        Prop("legend_pos", "choice", "Position de la légende.", default="top", choices=["top", "bottom", "none"]),
        Prop("bar_h", "number", "Hauteur d'une barre (horizontal).", default=12),
        *FRAME_PROPS,
    ],
    render=_chart_grouped,
    example={"labels": ["Google", "Bing", "Facebook", "Instagram"], "unit": "€",
             "series": [{"name": "Collecte N", "values": [356118, 35079, 60007, 11522]},
                        {"name": "Collecte N-1", "values": [0, 47353, 36090, 11726]}],
             "category_colors": ["regie_google", "regie_bing", "regie_facebook", "regie_instagram"],
             "title": "Collecte N et collecte N-1 (régies)"},
    tags=["graphiques"],
))


# --- donut_row --------------------------------------------------------------------------

def _donut_row(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    cols = int(p["cols"] or len(items) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    colors = list(p["colors"] or [])
    spec = get("donut")
    ops: list[dict] = []
    height = 0.0
    for i, it in enumerate(items):
        segs = [dict(s) for s in it.get("segments", [])]
        for j, s in enumerate(segs):
            if not s.get("color") and j < len(colors):
                s["color"] = colors[j]
        props = validate(spec, {"segments": segs, "labels": p["labels"], "legend_pos": p["legend_pos"], "title": it.get("title"),
                                "panel": p["panel"], "thickness": p["thickness"]})
        sub, sh = _donut(props, theme, cw, h)
        x, y = (i % cols) * (cw + gap), (i // cols) * ((h or sh) + gap)
        ops.extend(shift(sub, x, y))
        height = max(height, y + sh)
    return ops, h or height


register(Component(
    name="donut_row",
    description="Rangée de petits donuts (composant donut répété) avec un titre chacun, pourcentages sur les parts et légende dessous : répartition des impressions / clics / dépenses par régie.",
    props=[
        Prop("items", "list", "Donuts : {title, segments: [{label, value, color?}]}.", required=True),
        Prop("colors", "list", "Couleurs par position de part, communes à tous les donuts (ex. regie_google, regie_facebook)."),
        Prop("cols", "number", "Donuts par rangée (défaut : tous)."),
        Prop("gap", "number", "Espace entre donuts.", default=16),
        Prop("labels", "bool", "Pourcentages posés sur les parts.", default=True),
        Prop("legend_pos", "choice", "Légende sous chaque donut, à droite, ou aucune.", default="bottom", choices=["bottom", "right", "none"]),
        Prop("thickness", "number", "Épaisseur des anneaux (défaut : 36 % du rayon)."),
        Prop("panel", "bool", "Panneau gris clair autour de chaque donut.", default=False),
    ],
    render=_donut_row,
    example={"items": [{"title": "Répartition des impressions", "segments": [{"label": "Google", "value": 13}, {"label": "Bing", "value": 1}, {"label": "Facebook", "value": 78}, {"label": "Instagram", "value": 8}]},
                       {"title": "Répartition des clics", "segments": [{"label": "Google", "value": 62}, {"label": "Bing", "value": 5}, {"label": "Facebook", "value": 29}, {"label": "Instagram", "value": 4}]},
                       {"title": "Répartition des dépenses", "segments": [{"label": "Google", "value": 70}, {"label": "Bing", "value": 11}, {"label": "Facebook", "value": 13}, {"label": "Instagram", "value": 6}]}],
             "colors": ["regie_google", "regie_bing", "regie_facebook", "regie_instagram"]},
    tags=["graphiques"],
))


# --- mini_charts ------------------------------------------------------------------------

def _mini_charts(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    charts = list(p["charts"])
    cols = int(p["cols"] or len(charts) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    spec = get("chart_bars")
    labels = [str(lb) for lb in p["labels"]]
    colors = list(p["colors"] or [])
    ops: list[dict] = []
    top = 0.0
    if p["legend"]:
        # one shared legend instead of category labels under each narrow chart
        entries = [{"name": lb, "color": colors[i] if i < len(colors) and colors[i] else "accent"} for i, lb in enumerate(labels)]
        ops += legend_ops(entries, 0, 0, w, "top")[0]
        top = LEGEND_H + 4
    chart_h = (h - top) if h else None
    height = top
    for i, c in enumerate(charts):
        props = validate(spec, {"labels": ["" for _ in labels] if p["legend"] else labels, "values": c.get("values", []),
                                "unit": c.get("unit"), "max": c.get("max"), "colors": colors or None, "y_axis": p["y_axis"],
                                "show_values": p["show_values"], "title": c.get("title"), "panel": p["panel"]})
        sub, sh = _chart_bars(props, theme, cw, chart_h)
        x, y = (i % cols) * (cw + gap), top + (i // cols) * ((chart_h or sh) + gap)
        ops.extend(shift(sub, x, y))
        height = max(height, y + sh)
    return ops, h or height


register(Component(
    name="mini_charts",
    description="Petits multiples : un mini-histogramme par indicateur (impressions, clics, collecte, ROAS, dépenses), mêmes catégories et mêmes couleurs partout, titre au-dessus de chacun.",
    props=[
        Prop("labels", "list", "Catégories partagées (ex. Google, Bing).", required=True),
        Prop("charts", "list", "Indicateurs : {title, values, unit?, max?}.", required=True),
        Prop("colors", "list", "Une couleur par catégorie (ex. regie_google, regie_bing)."),
        Prop("cols", "number", "Graphiques par rangée (défaut : tous)."),
        Prop("gap", "number", "Espace entre graphiques.", default=12),
        Prop("y_axis", "bool", "Axe gradué sur chaque graphique.", default=True),
        Prop("show_values", "bool", "Valeurs sur les barres.", default=True),
        Prop("legend", "bool", "Une légende commune au-dessus (couleur par catégorie) à la place des libellés sous chaque graphique.", default=True),
        Prop("panel", "bool", "Panneau gris clair autour de chaque graphique.", default=False),
    ],
    render=_mini_charts,
    example={"labels": ["Google", "Bing"], "colors": ["regie_google", "regie_bing"],
             "charts": [{"title": "Impressions", "values": [2439153, 150851]}, {"title": "Clics", "values": [62579, 5627]},
                        {"title": "Collecte GA4", "values": [178175, 18448], "unit": "€"}, {"title": "ROAS GA4", "values": [1.95, 1.32]},
                        {"title": "Dépenses", "values": [91244, 14014], "unit": "€"}]},
    tags=["graphiques"],
))
