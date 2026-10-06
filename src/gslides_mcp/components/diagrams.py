"""Diagram components: funnel, timeline, process, hub_spoke, pie, stack,
compare_bars, effort_matrix, bubbles, heatmap.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only. Geometry follows the
Periscope PPTX engine blocks (inches × 72).
"""

from __future__ import annotations

import math

from ..themes import Theme
from . import Component, Prop, register
from .builtin import BOLD_WRAP, INSETS, _donut, _fmt, _nice_max, _text_height, fit_text_size


def _fmt_fr(v: float) -> str:
    """12400 → '12 400' (narrow no-break space), decimals with a comma."""
    if float(v).is_integer():
        return f"{int(v):,}".replace(",", "\u202f")
    txt = f"{v:,.2f}".rstrip("0")  # 1.95 -> 1,95 ; 3.90 -> 3,9 ; 12.5 -> 12,5
    return txt.replace(",", "\u202f").replace(".", ",")


# --- funnel -------------------------------------------------------------------------

def _funnel(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    n = max(1, len(items))
    pct = p["pct"]
    show_first = pct in ("first", "both")
    show_prev = pct in ("prev", "both")
    row_h = (h / n) if h else 34.0
    label_w = float(p["label_w"] or w * 0.22)
    longest = max((len(f"{_fmt_fr(float(it.get('value', 0)))}{p['unit'] or ''}") for it in items), default=1)
    value_w = max(float(p["value_w"]), longest * 7.4 + 16)  # 12 pt bold Barlow + insets
    pill_w = 40.0
    pills_w = (pill_w + 6) * (int(show_first) + int(show_prev))
    zone_x = label_w + 8
    zone_w = max(20.0, w - label_w - 8 - value_w - 8 - pills_w)
    values = [float(it.get("value", 0)) for it in items]
    vmax = max(values) or 1.0
    bar_h = min(float(p["bar_h"]), row_h * 0.62)
    unit = p["unit"] or ""
    ops: list[dict] = []
    for i, (it, v) in enumerate(zip(items, values)):
        cy = i * row_h + row_h / 2
        if it.get("sub"):
            ops.append({"op": "text", "x": 0, "y": cy - 20, "w": label_w, "h": 20, "text": str(it.get("label", "")),
                        "style": "label", "bold": True, "align": "END", "valign": "BOTTOM"})
            ops.append({"op": "text", "x": 0, "y": cy - 2, "w": label_w, "h": 16, "text": str(it["sub"]),
                        "style": "caption", "align": "END"})
        else:
            ops.append({"op": "text", "x": 0, "y": cy - row_h / 2, "w": label_w, "h": row_h, "text": str(it.get("label", "")),
                        "style": "label", "bold": True, "align": "END", "valign": "MIDDLE"})
        frac = max(v / vmax, float(p["min_frac"]))
        bw = zone_w * frac
        ops.append({"op": "box", "x": zone_x + (zone_w - bw) / 2, "y": cy - bar_h / 2, "w": bw, "h": bar_h,
                    "fill": it.get("color") or "ink", "role": "bar"})
        vx = zone_x + zone_w + 8
        ops.append({"op": "text", "x": vx, "y": cy - 12, "w": value_w, "h": 24, "text": f"{_fmt_fr(v)}{unit}",
                    "style": "chart_value", "size": 12, "valign": "MIDDLE"})
        px = vx + value_w + 4
        if show_first:
            first = values[0] or 1.0
            ops.append({"op": "box", "x": px, "y": cy - 9, "w": pill_w, "h": 18, "fill": "accent", "role": "pct_first",
                        "text": "100 %" if i == 0 else f"{round(100 * v / first)} %", "style": "badge", "size": 10,
                        "align": "CENTER", "valign": "MIDDLE"})
            px += pill_w + 6
        if show_prev and i > 0:
            prev = values[i - 1] or 1.0
            ops.append({"op": "box", "x": px, "y": cy - 9, "w": pill_w, "h": 18, "fill": None,
                        "line": {"color": "ink", "weight": 1.25}, "role": "pct_prev",
                        "text": f"{round(100 * v / prev)} %", "style": "badge", "size": 10, "color": "ink",
                        "align": "CENTER", "valign": "MIDDLE"})
    height = n * row_h
    if pct != "none" and p["legend"]:
        ly = height + 4
        lx = w - 6
        if show_prev:
            lx -= 126
            ops.append({"op": "box", "x": lx, "y": ly + 3, "w": 10, "h": 10, "fill": None, "line": {"color": "ink", "weight": 1.25}})
            ops.append({"op": "text", "x": lx + 14, "y": ly - 4, "w": 112, "h": 16 + INSETS, "text": "% de l'étape précédente", "style": "caption"})
        if show_first:
            lx -= 105
            ops.append({"op": "box", "x": lx, "y": ly + 3, "w": 10, "h": 10, "fill": "accent"})
            ops.append({"op": "text", "x": lx + 14, "y": ly - 4, "w": 92, "h": 16 + INSETS, "text": "% de la 1re étape", "style": "caption"})
        height += 20
    return ops, height


register(Component(
    name="funnel", description="Entonnoir de parcours : barres centrées proportionnelles à la 1re étape, libellé et sous-libellé à gauche, valeur à droite, taux vs 1re étape (pastille accent) et/ou vs étape précédente (contour).",
    props=[
        Prop("items", "list", "Étapes : {label, value, sub?, color?}.", required=True),
        Prop("pct", "choice", "Pastilles de taux.", default="first", choices=["first", "prev", "both", "none"]),
        Prop("unit", "str", "Suffixe des valeurs."),
        Prop("label_w", "number", "Largeur de la colonne des libellés (défaut 22 %)."),
        Prop("value_w", "number", "Largeur de la colonne des valeurs.", default=52),
        Prop("bar_h", "number", "Hauteur max des barres.", default=22),
        Prop("min_frac", "number", "Largeur minimale d'une barre (fraction).", default=0.06),
        Prop("legend", "bool", "Légende des pastilles sous l'entonnoir.", default=True),
    ],
    render=_funnel,
    example={"items": [{"label": "Visites", "value": 12400}, {"label": "Leads", "value": 620, "sub": "formulaire"}, {"label": "Clients", "value": 74}], "pct": "both"},
    tags=["graphiques"],
))


# --- timeline / process / hub_spoke --------------------------------------------------

def _timeline(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    phases = list(p["phases"])
    n = max(1, len(phases))
    step = w / max(n - 0.5, 1)
    ops: list[dict] = [{"op": "line", "x1": 0, "y1": 34, "x2": w, "y2": 34, "color": "ink", "weight": 3}]
    bottom = 74.0
    for i, ph in enumerate(phases):
        x = i * step
        ops.append({"op": "text", "x": x - 4, "y": 0, "w": 140, "h": 14 + INSETS, "text": str(ph.get("date", "")),
                    "style": "label", "bold": True})
        ops.append({"op": "box", "x": x, "y": 26, "w": 16, "h": 16, "shape": "ELLIPSE",
                    "fill": ph.get("color") or "accent", "line": {"color": "ink", "weight": 2}})
        ops.append({"op": "text", "x": x - 4, "y": 50, "w": step - 8, "h": 16 + INSETS, "text": str(ph.get("title", "")),
                    "style": "card_title", "size": float(ph.get("title_size", 12))})
        if ph.get("text"):
            th = _text_height(ph["text"], step - 8, 11)
            ops.append({"op": "text", "x": x - 4, "y": 74, "w": step - 8, "h": th, "markdown": str(ph["text"]),
                        "style": "body", "size": 11})
            bottom = max(bottom, 74 + th)
    return ops, h or bottom


register(Component(
    name="timeline", description="Frise : ligne horizontale, une pastille par phase avec date au-dessus, titre et texte en dessous.",
    props=[Prop("phases", "list", "Phases : {date, title, text?, color?, title_size?}.", required=True)],
    render=_timeline,
    example={"phases": [{"date": "T1 2026", "title": "Audit", "text": "Crawl, logs, Search Console"}, {"date": "T2", "title": "Plan de contenus"}, {"date": "T3", "title": "Netlinking", "color": "accent_alt"}]},
    tags=["schémas"],
))


def _process(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    steps = list(p["steps"])
    n = max(1, len(steps))
    height = h or 100
    arrow_w = float(p["arrow_w"])
    fixed = sum(float(s["w"]) for s in steps if s.get("w"))
    free = max(1, sum(1 for s in steps if not s.get("w")))
    auto_w = max(20.0, (w - (n - 1) * arrow_w - fixed) / free)
    ops: list[dict] = []
    x = 0.0
    for i, st in enumerate(steps):
        sw = float(st.get("w") or auto_w)
        fg = st.get("color") or ("on_dark" if str(st.get("fill", "")).startswith("surface_dark") else "ink")
        ops.append({"op": "box", "x": x, "y": 0, "w": sw, "h": height, "shape": "ROUND_RECTANGLE", "fill": st.get("fill") or "surface", "role": "step"})
        ops.append({"op": "text", "x": x + 6, "y": 10, "w": sw - 12, "h": 16 + INSETS, "text": str(st.get("label", "")),
                    "style": "label", "bold": True, "color": fg, "align": "CENTER"})
        if st.get("sub"):
            ops.append({"op": "text", "x": x + 6, "y": 38, "w": sw - 12, "h": max(10.0, height - 46), "markdown": str(st["sub"]),
                        "style": "body", "size": 11, "color": fg, "align": "CENTER"})
        x += sw
        if i < n - 1:
            ops.append({"op": "text", "x": x, "y": height / 2 - 16, "w": arrow_w, "h": 32, "text": "→",
                        "style": "label", "size": 18, "bold": True, "align": "CENTER", "valign": "MIDDLE"})
            x += arrow_w
    return ops, height


register(Component(
    name="process", description="Parcours fléché : blocs côte à côte (libellé + sous-texte) séparés par des flèches.",
    props=[
        Prop("steps", "list", "Étapes : {label, sub?, fill?, color?, w?}.", required=True),
        Prop("arrow_w", "number", "Largeur réservée à chaque flèche.", default=30),
    ],
    render=_process,
    example={"steps": [{"label": "Audit", "sub": "2 semaines"}, {"label": "Plan", "sub": "priorisation"}, {"label": "Run", "sub": "sprints mensuels", "fill": "accent"}]},
    tags=["schémas"],
))


def _hub_spoke(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    height = h or 260
    sats = list(p["sats"])
    n = max(1, len(sats))
    hub_w, hub_h = float(p["hub_w"]), float(p["hub_h"])
    d = float(p["sat_d"])
    cx, cy = w / 2, height / 2
    rx = max(hub_w / 2 + d / 2 + 6, w / 2 - d / 2 - 4)
    ry = max(hub_h / 2 + d / 2 + 6, height / 2 - d / 2 - 4)
    rx, ry = min(rx, w / 2 - d / 2 - 4), min(ry, height / 2 - d / 2 - 4)
    centers = []
    for i in range(n):
        a = math.radians(-90 + 360 * i / n)
        centers.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    lines = [{"op": "line", "x1": cx, "y1": cy, "x2": sx, "y2": sy, "color": "ink", "weight": 1.75} for sx, sy in centers]
    circles = []
    for sat, (sx, sy) in zip(sats, centers):
        circles.append({"op": "box", "x": sx - d / 2, "y": sy - d / 2, "w": d, "h": d, "shape": "ELLIPSE", "fill": "background",
                        "line": {"color": "accent" if sat.get("hl") else "ink", "weight": 2.5},
                        "text": str(sat.get("label", "")), "style": "caption", "size": 10, "bold": True, "color": "ink",
                        "align": "CENTER", "valign": "MIDDLE"})
    hub = {"op": "box", "x": cx - hub_w / 2, "y": cy - hub_h / 2, "w": hub_w, "h": hub_h, "fill": "accent", "role": "hub",
           "text": str(p["center"]), "style": "card_title", "size": 12, "color": "on_accent", "align": "CENTER", "valign": "MIDDLE"}
    return lines + circles + [hub], height


register(Component(
    name="hub_spoke", description="Schéma archipel : bloc central accent relié à des satellites ronds (contour accent pour les mis en avant).",
    props=[
        Prop("center", "str", "Texte du bloc central.", required=True),
        Prop("sats", "list", "Satellites : {label, hl?}.", required=True),
        Prop("hub_w", "number", "Largeur du bloc central.", default=130),
        Prop("hub_h", "number", "Hauteur du bloc central.", default=72),
        Prop("sat_d", "number", "Diamètre des satellites.", default=76),
    ],
    render=_hub_spoke,
    example={"center": "Site de marque", "sats": [{"label": "SEO"}, {"label": "Google Ads", "hl": True}, {"label": "Social"}, {"label": "Emailing"}, {"label": "Presse"}]},
    tags=["schémas"],
))


# --- pie / stack -------------------------------------------------------------------------

def _pie(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ops, height = _donut({"segments": p["segments"], "thickness": None, "center": None, "legend": p["legend"]}, theme, w, h)
    for o in ops:
        if o["op"] == "ring":
            o["thickness"] = o["r"]
    return ops, height


register(Component(
    name="pie", description="Camembert (anneau plein) avec légende et pourcentages.",
    props=[
        Prop("segments", "list", "Parts : {label, value, color?}.", required=True),
        Prop("legend", "bool", "Légende à droite.", default=True),
    ],
    render=_pie, example={"segments": [{"label": "Google", "value": 62}, {"label": "Bing", "value": 8}, {"label": "Meta", "value": 30}]},
    tags=["graphiques"],
))

_STACK_PALETTES = {
    "navy": ("surface_dark", "surface_dark_2", "surface"),
    "brand": ("surface_dark", "accent", "surface_dark", "accent_alt"),
}
_STACK_FG = {"surface_dark": "on_dark", "surface_dark_2": "on_dark", "accent": "on_accent", "accent_alt": "ink"}
_DARK_FILLS = {"surface_dark", "surface_dark_2", "ink", "text"}


def _stack(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    n = max(1, len(items))
    item_h, gap = float(p["item_h"]), float(p["gap"])
    min_w = w * float(p["min_ratio"])
    fills = _STACK_PALETTES[p["palette"]]
    ops: list[dict] = []
    dark_seen = 0
    for i, it in enumerate(items):
        iw = float(it.get("width") or (w - (w - min_w) * i / max(n - 1, 1)))
        fill = it.get("fill") or fills[i % len(fills)]
        fg = it.get("color") or _STACK_FG.get(fill, "ink")
        y = i * (item_h + gap)
        x = w / 2 - iw / 2
        ops.append({"op": "box", "x": x, "y": y, "w": iw, "h": item_h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "layer"})
        tx, tw = x, iw
        if p["numbered"] or it.get("num"):
            # on dark layers the number takes the accents in turn (mint, then acid), as in the mock-up
            if fill in _DARK_FILLS:
                num_col = ("accent", "accent_alt")[dark_seen % 2]
                dark_seen += 1
            else:
                num_col = "ink"
            ops.append({"op": "text", "x": x + 10, "y": y, "w": 40, "h": item_h, "text": str(it.get("num") or f"{i + 1:02d}"),
                        "style": "label", "size": 11, "bold": True, "color": num_col, "valign": "MIDDLE", "role": "num"})
            tx, tw = x + 34, iw - 68  # keep the centred text clear of the number, symmetrically
        label = str(it.get("label", ""))
        if it.get("sub"):
            # one line each: a narrow layer shrinks its text instead of wrapping over the sub-line
            ls = fit_text_size(label, tw / BOLD_WRAP, 12, floor=9.5)
            ss = fit_text_size(str(it["sub"]), tw, 10.5, floor=9)
            ops.append({"op": "text", "x": tx, "y": y + 4, "w": tw, "h": 18 + INSETS, "text": label,
                        "style": "label", "size": ls, "small_ok": ls < 11, "bold": True, "color": fg, "align": "CENTER", "role": "label"})
            ops.append({"op": "text", "x": tx, "y": y + item_h / 2, "w": tw, "h": item_h / 2 - 2, "text": str(it["sub"]),
                        "style": "caption", "size": ss, "small_ok": ss < 10, "color": fg, "align": "CENTER", "role": "sub"})
        else:
            ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": item_h, "text": label,
                        "style": "label", "bold": True, "color": fg, "align": "CENTER", "valign": "MIDDLE", "role": "label"})
    return ops, n * (item_h + gap) - gap


register(Component(
    name="stack", description="Pile centrée (pyramide, entonnoir simple) : couches arrondies de largeur décroissante avec libellé et sous-texte, numéro « 01 » optionnel à gauche.",
    props=[
        Prop("items", "list", "Couches, du haut vers le bas : {label, sub?, num?, fill?, color?, width?}.", required=True),
        Prop("item_h", "number", "Hauteur d'une couche.", default=48),
        Prop("gap", "number", "Espace entre couches.", default=8),
        Prop("min_ratio", "number", "Largeur de la dernière couche (fraction de la largeur).", default=0.45),
        Prop("numbered", "bool", "Numéro 01, 02… à gauche de chaque couche (menthe puis acide sur fond sombre, encre sinon) ; `num` d'un item le remplace.", default=False),
        Prop("palette", "choice", "Fonds par défaut : navy (navy, navy 2, gris) ou brand (navy, menthe, navy, acide).", default="navy",
             choices=list(_STACK_PALETTES)),
    ],
    render=_stack,
    example={"items": [{"label": "Notoriété", "sub": "Haut de funnel"}, {"label": "Considération"}, {"label": "Conversion", "fill": "accent"}]},
    tags=["schémas"],
))


# --- compare_bars / effort_matrix / bubbles / heatmap ----------------------------------------

def _compare_bars(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ops: list[dict] = []
    y = 0.0
    gap = float(p["gap"])
    for bar in p["bars"]:
        ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": 22, "text": str(bar.get("label", "")), "style": "label", "bold": True})
        ops.append({"op": "box", "x": 0, "y": y + 22, "w": w, "h": 25, "fill": "surface", "role": "track"})
        frac = float(bar.get("frac", 0))
        if frac > 0:
            ops.append({"op": "box", "x": 0, "y": y + 22, "w": max(w * frac, 4), "h": 25, "fill": bar.get("color") or "accent", "role": "bar"})
        y += gap
    return ops, h or (y - gap + 47)


register(Component(
    name="compare_bars", description="Barres horizontales pleines/vides à comparer (part atteinte vs angle mort).",
    props=[
        Prop("bars", "list", "Barres : {label, frac (0-1), color?}.", required=True),
        Prop("gap", "number", "Pas vertical entre barres.", default=61),
    ],
    render=_compare_bars, example={"bars": [{"label": "Pages vues par Google", "frac": 0.72}, {"label": "Pages indexées", "frac": 0.41, "color": "accent_alt"}]},
    tags=["graphiques"],
))


def _effort_matrix(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    height = h or 200
    ops: list[dict] = [
        {"op": "line", "x1": 0, "y1": 0, "x2": 0, "y2": height, "color": "ink", "weight": 2},
        {"op": "line", "x1": 0, "y1": height, "x2": w, "y2": height, "color": "ink", "weight": 2},
        {"op": "text", "x": 4, "y": -2, "w": 120, "h": 16 + INSETS, "text": str(p["y_label"]), "style": "label", "bold": True},
        {"op": "text", "x": w - 120, "y": height + 2, "w": 120, "h": 16 + INSETS, "text": str(p["x_label"]), "style": "label", "bold": True, "align": "END"},
    ]
    for b in p["bubbles"]:
        d = float(b.get("d", 34))
        cx, cy = float(b["x"]) * w, (1 - float(b["y"])) * height
        ops.append({"op": "box", "x": cx - d / 2, "y": cy - d / 2, "w": d, "h": d, "shape": "ELLIPSE", "fill": b.get("fill") or "accent",
                    "role": "bubble", "text": str(b.get("n", "")), "style": "label", "size": 16, "bold": True,
                    "color": b.get("color") or "ink", "align": "CENTER", "valign": "MIDDLE"})
        ly = cy - d / 2 - 22 if b.get("above") else cy + d / 2 + 2
        ops.append({"op": "text", "x": cx - 60, "y": ly, "w": 120, "h": 14 + INSETS, "text": str(b.get("label", "")),
                    "style": "caption", "size": 10, "bold": True, "align": "CENTER"})
    return ops, height + 22


register(Component(
    name="effort_matrix", description="Matrice impact / effort : deux axes, bulles numérotées positionnées en fractions (x = effort, y = impact).",
    props=[
        Prop("bubbles", "list", "Bulles : {n, label, x (0-1), y (0-1), d?, fill?, color?, above?}.", required=True),
        Prop("x_label", "str", "Libellé de l'axe horizontal.", default="Effort →"),
        Prop("y_label", "str", "Libellé de l'axe vertical.", default="Impact"),
    ],
    render=_effort_matrix,
    example={"bubbles": [{"n": "1", "label": "Maillage interne", "x": 0.2, "y": 0.8}, {"n": "2", "label": "Refonte technique", "x": 0.85, "y": 0.7, "fill": "accent_alt"}, {"n": "3", "label": "Netlinking", "x": 0.6, "y": 0.35}]},
    tags=["schémas"],
))


def _bubbles(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    height = h or 200
    pts = list(p["points"])
    ml, mb, mt, mr = 40.0, 24.0, 8.0, 8.0
    px, py, pw, ph = ml, mt, w - ml - mr, height - mt - mb
    xmax = float(p["x_max"] or _nice_max([float(q["x"]) for q in pts]))
    ymax = float(p["y_max"] or _nice_max([float(q["y"]) for q in pts]))
    smax = max((float(q.get("size", 1)) for q in pts), default=1) or 1
    ops: list[dict] = []
    for k in range(5):
        gy = py + ph - ph * k / 4
        gx = px + pw * k / 4
        ops.append({"op": "line", "x1": px, "y1": gy, "x2": px + pw, "y2": gy, "color": "ink" if k == 0 else "grid", "weight": 1.5 if k == 0 else 0.75})
        ops.append({"op": "line", "x1": gx, "y1": py, "x2": gx, "y2": py + ph, "color": "ink" if k == 0 else "grid", "weight": 1.5 if k == 0 else 0.75})
        ops.append({"op": "text", "x": 0, "y": gy - 7, "w": ml - 6, "h": 14, "text": _fmt(ymax * k / 4), "style": "axis", "align": "END"})
        ops.append({"op": "text", "x": gx - 20, "y": py + ph + 3, "w": 40, "h": 12, "text": _fmt(xmax * k / 4), "style": "axis", "align": "CENTER"})
    for i, q in enumerate(pts):
        d = 12 + 36 * float(q.get("size", 1)) / smax
        cx = px + pw * float(q["x"]) / xmax
        cy = py + ph - ph * float(q["y"]) / ymax
        ops.append({"op": "box", "x": cx - d / 2, "y": cy - d / 2, "w": d, "h": d, "shape": "ELLIPSE",
                    "fill": q.get("color") or f"series_{i % 6 + 1}", "line": {"color": "background", "weight": 1}, "role": "bubble"})
        ops.append({"op": "text", "x": cx + d / 2 + 2, "y": cy - 8, "w": 90, "h": 16, "text": str(q.get("name", "")), "style": "legend", "valign": "MIDDLE"})
    if p["x_title"]:
        ops.append({"op": "text", "x": px, "y": height + 2, "w": pw, "h": 14, "text": str(p["x_title"]), "style": "caption", "align": "CENTER"})
    return ops, height + (16 if p["x_title"] else 0)


register(Component(
    name="bubbles", description="Matrice à bulles : points (x, y) dont la taille encode une troisième valeur, sur grille.",
    props=[
        Prop("points", "list", "Points : {name, x, y, size, color?}.", required=True),
        Prop("x_max", "number", "Maximum de l'axe horizontal."),
        Prop("y_max", "number", "Maximum de l'axe vertical."),
        Prop("x_title", "str", "Titre de l'axe horizontal."),
    ],
    render=_bubbles,
    example={"points": [{"name": "SEO", "x": 20, "y": 70, "size": 100}, {"name": "Ads", "x": 70, "y": 40, "size": 60}, {"name": "Social", "x": 40, "y": 20, "size": 30}], "x_title": "Effort"},
    tags=["graphiques"],
))


def _heatmap(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    rows = [list(r) for r in p["rows"]]
    numbers = [(i, j, float(v)) for i, r in enumerate(rows) if i > 0 for j, v in enumerate(r) if j > 0 and _is_num(v)]
    vals = [v for _, _, v in numbers]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
    span = (hi - lo) or 1.0
    fills: dict[tuple[int, int], str] = {}
    colors: dict[tuple[int, int], str] = {}
    for i, j, v in numbers:
        b = min(4, int((v - lo) / span * 4) + 1)
        fills[(i, j)] = f"heat_{b}"
        if b == 4:
            colors[(i, j)] = "on_dark"
    text_rows = [[("" if v is None or v == "" else (_fmt(float(v)) if _is_num(v) else str(v))) for v in r] for r in rows]
    row_h = float(p["row_h"])
    op = {
        "op": "table", "x": 0, "y": 0, "w": w, "rows": text_rows, "col_w": p["col_w"], "row_h": row_h,
        "header": {"fill": "ink", "color": "on_dark", "bold": True},
        "banding": ["background"], "first_col_bold": True,
        "borders": {"color": "background", "weight": 1.5},
        "align": [None] + ["CENTER"] * (max(len(r) for r in rows) - 1),
        "size": p["size"], "cell_fills": fills, "cell_text_colors": colors,
    }
    return [op], row_h * len(rows)


def _is_num(v) -> bool:
    try:
        float(v)
        return not isinstance(v, bool) and v is not None and v != ""
    except (TypeError, ValueError):
        return False


register(Component(
    name="heatmap", description="Tableau thermique : cellules numériques colorées par quartile (gris, menthe pâle, menthe, navy), en-tête sombre, première colonne en gras.",
    props=[
        Prop("rows", "list", "Lignes : première = en-tête, première colonne = libellés, cellules numériques (null = vide).", required=True),
        Prop("col_w", "list", "Largeurs de colonnes en pt."),
        Prop("row_h", "number", "Hauteur de ligne.", default=24),
        Prop("size", "number", "Taille de police."),
    ],
    render=_heatmap,
    example={"rows": [["", "Jan", "Fév", "Mar"], ["SEO", 12, 48, 90], ["Ads", 60, 55, 20], ["Social", 5, None, 33]]},
    tags=["données"],
))
