"""Text-block components: bigstat (bare or in a panel beside a text), stats (row or list), pill, checklist, chevrons, arrows.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import BOLD_WRAP, INSET_X, INSETS, LEADING, _text_height, _wrapped_lines

_DARK_FILLS = {"surface_dark", "surface_dark_2", "ink", "text"}


# --- bigstat / stats ---------------------------------------------------------------------

PANEL_FILLS = {"dark": ("surface_dark", "on_dark"), "surface": ("surface", "ink"), "accent": ("accent", "ink")}
PANEL_MIN_H = 220.0
PANEL_TEXT = 12.0
PANEL_PAD = 16.0


def _bigstat_panel(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    """The figure in a tall panel (navy by default), its source at the foot, and the text column beside it.

    From the Pasteur paid-media deck: « -30 à -40 % / Audience SEO / 09/2026
    vs N-1 * » centred in a navy panel, « * Source Tendances SEMRUSH » at its
    foot, a bold lead and paragraphs with a ==highlighted== passage on the right.
    """
    fill, fg = PANEL_FILLS[p["panel"]] if p["panel"] else (None, None)
    text = p["text"]
    pw = w * float(p["panel_w"]) if text else w
    tx = pw + 24
    tw = w - tx
    text_h = _text_height(str(text), tw, PANEL_TEXT) if text else 0.0
    panel_h = h or max(text_h, PANEL_MIN_H)
    inner = pw - 2 * PANEL_PAD
    value = str(p["value"])
    # the figure stays on one line: it shrinks to the panel (Barlow bold digits ≈ 0.58 × size)
    size = max(20.0, min(40.0, (inner - 2 * INSET_X) / max(1, len(value) * 0.58)))
    value_color = p["color"] or fg or "ink"
    label_size, sub_size = 15.0, 11.0
    label_h = _text_height(str(p["label"]), inner, label_size)
    group = [("value", value, size * 1.2 + INSETS, {"style": "stat_value", "size": round(size, 1), "color": value_color}),
             ("label", str(p["label"]), label_h, {"style": "label", "size": label_size, "color": fg or "ink"})]
    if p["sub"]:
        group.append(("sub", str(p["sub"]), sub_size * 1.2 + INSETS, {"style": "label", "size": sub_size, "color": fg or "muted"}))
    source_h = 10 * 1.2 + INSETS if p["source"] else 0.0
    group_h = sum(gh for _, _, gh, _ in group)
    # the figure group centred in the panel, above the source line
    y = max(PANEL_PAD, (panel_h - source_h - group_h) / 2)
    ops: list[dict] = []
    if fill:
        ops.append({"op": "box", "x": 0, "y": 0, "w": pw, "h": panel_h, "fill": fill, "role": "panel"})
    for role, t, gh, style in group:
        ops.append({"op": "text", "x": PANEL_PAD, "y": y, "w": inner, "h": gh, "text": t, "align": "CENTER", "role": role, **style})
        y += gh - 4
    if p["source"]:
        ops.append({"op": "text", "x": PANEL_PAD, "y": panel_h - PANEL_PAD + 4 - source_h, "w": inner, "h": source_h, "text": str(p["source"]),
                    "style": "caption", "size": 10, "color": fg or "muted", "align": "CENTER", "role": "source"})
    if text:
        ops.append({"op": "text", "x": tx, "y": 0, "w": tw, "h": panel_h, "markdown": str(text), "style": "body", "size": PANEL_TEXT,
                    "highlight": p["highlight"], "valign": "MIDDLE", "role": "text"})
    return ops, panel_h


def _bigstat(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    if p["panel"] or p["text"]:
        return _bigstat_panel(p, theme, w, h)
    color = p["color"]
    ops: list[dict] = [
        {"op": "text", "x": 0, "y": 0, "w": w, "h": 64 + INSETS, "text": str(p["value"]), "style": "stat_value",
         "color": color, "align": "CENTER"},
        {"op": "text", "x": 0, "y": 72, "w": w, "h": 18 + INSETS, "text": str(p["label"]), "style": "stat_label",
         "color": color, "align": "CENTER"},
    ]
    height = 98.0
    if p["sub"]:
        ops.append({"op": "text", "x": 0, "y": 98, "w": w, "h": 14 + INSETS, "text": str(p["sub"]), "style": "caption",
                    "size": 11, "align": "CENTER"})
        height = 120.0
    return ops, h or height


register(Component(
    name="bigstat", description="Un chiffre spectaculaire centré (54 pt) avec son libellé et un sous-texte optionnel ; "
                                "ou dans un panneau haut (navy, gris, menthe) avec sa source en pied et une colonne de texte à côté.",
    props=[
        Prop("value", "str", "Le chiffre, formaté.", required=True),
        Prop("label", "str", "Libellé sous le chiffre.", required=True),
        Prop("sub", "str", "Précision en petit (période, périmètre)."),
        Prop("color", "color", "Couleur du chiffre et du libellé (rôle du thème) ; avec panel, celle du chiffre seul."),
        Prop("panel", "choice", "Panneau derrière le chiffre : dark (navy, texte blanc), surface (gris), accent (menthe).",
             choices=list(PANEL_FILLS)),
        Prop("source", "str", "Source en petit au pied du panneau (« * Source Tendances SEMRUSH »)."),
        Prop("text", "markdown", "Colonne de texte à droite du chiffre : **chapô gras**, paragraphes séparés par une ligne vide, ==passage surligné==."),
        Prop("panel_w", "number", "Part de la largeur prise par le chiffre quand il y a du texte.", default=0.36),
        Prop("highlight", "color", "Couleur du ==surlignage== du texte.", default="highlight_alt"),
    ],
    render=_bigstat, example={"value": "+42 %", "label": "de trafic organique", "sub": "vs 2025, à périmètre constant"},
    tags=["chiffres"],
))


LIST_LABEL, LIST_SUB = 13.0, 11.0  # stats list: bold title and grey line next to each figure
LIST_GAP = 6.0


def _stat_items(items) -> list[tuple[str, str, str | None]]:
    return [(str(it.get("value", "")), str(it.get("label", "")), it.get("sub")) if isinstance(it, dict) else (str(it[0]), str(it[1]), None)
            for it in items]


def _stats_list(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    """Figures in a column on the left, each with a bold title and a grey line beside it.

    The memo-deck rows: grey rounded bands with ``tile`` (notation grid, points
    of progress), bare lines without (« profil moyen du testateur »). One value
    size and one row height for the whole list, so the figures line up.
    """
    rows = _stat_items(p["items"])
    tile = bool(p["tile"])
    pad = 8.0 if tile else 0.0
    size = 22.0 if tile else 18.0
    longest = max((len(v) for v, _, _ in rows), default=1)
    value_w = float(p["value_w"] or min(max(longest * size * 0.6 + 2 * INSET_X + 8, w * 0.12), w * 0.32))
    # a figure never wraps: it shrinks to its column (Barlow bold digits ≈ 0.58 × size)
    size = max(12.0, min(size, (value_w - 2 * INSET_X) / (longest * 0.58)))
    tx = pad + value_w + 6
    tw = w - tx - pad
    heights = [(_wrapped_lines(label, tw, LIST_LABEL * BOLD_WRAP) * LIST_LABEL
                + (_wrapped_lines(str(sub), tw, LIST_SUB) * LIST_SUB if sub else 0)) * LEADING + INSETS for _, label, sub in rows]
    row_h = max(max(heights, default=0.0), size * 1.2 + INSETS) + (12 if tile else 0)
    if h and rows:
        row_h = max(row_h, (h - (len(rows) - 1) * LIST_GAP) / len(rows))
    color = p["color"] or "ink"  # mint figures vanish on a grey band
    # a title over a grey line is bold; a bare label (« 70 % de femmes ») stays roman next to its bold figure
    titled = any(sub for _, _, sub in rows)
    ops: list[dict] = []
    for i, (value, label, sub) in enumerate(rows):
        y = i * (row_h + LIST_GAP)
        if tile:
            ops.append({"op": "box", "x": 0, "y": y, "w": w, "h": row_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "row"})
        ops.append({"op": "text", "x": pad, "y": y, "w": value_w, "h": row_h, "text": value, "style": "stat_value", "size": round(size, 1),
                    "color": color, "valign": "MIDDLE", "role": "value"})
        paras = [[{"text": label, "bold": titled, "size": LIST_LABEL, "color": "ink"}]]
        if sub:
            paras.append([{"text": str(sub), "size": LIST_SUB, "color": "muted"}])
        ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": row_h, "runs": paras, "style": "label", "valign": "MIDDLE", "role": "text"})
    height = len(rows) * row_h + max(0, len(rows) - 1) * LIST_GAP
    return ops, h or height


def _stats(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    if p["layout"] == "list":
        return _stats_list(p, theme, w, h)
    items = list(p["items"])
    n = max(1, len(items))
    per_w = w / n
    color = p["color"]
    ops: list[dict] = []
    height = 82.0
    for i, it in enumerate(items):
        value, label, sub = (it.get("value"), it.get("label"), it.get("sub")) if isinstance(it, dict) else (it[0], it[1], None)
        x = i * per_w
        ops.append({"op": "text", "x": x, "y": 0, "w": per_w, "h": 46 + INSETS, "text": str(value), "style": "stat_value",
                    "size": 38, "color": color, "align": "CENTER"})
        ops.append({"op": "text", "x": x, "y": 56, "w": per_w, "h": 18 + INSETS, "text": str(label), "style": "stat_label",
                    "size": 12.5, "color": color, "align": "CENTER"})
        if sub:
            sh = _text_height(str(sub), per_w, 10)
            ops.append({"op": "text", "x": x, "y": 80, "w": per_w, "h": sh, "text": str(sub), "style": "caption", "align": "CENTER", "role": "sub"})
            height = max(height, 80 + sh)
    return ops, h or height


register(Component(
    name="stats", description="Rangée de chiffres clés centrés (valeur 38 pt + libellé), répartis sur la largeur ; ou, en liste, "
                              "un chiffre à gauche de chaque ligne avec titre gras et précision grise, en bandeaux gris arrondis ou nus.",
    props=[
        Prop("items", "list", "Chiffres : {value, label, sub?} (ou paires [value, label]).", required=True),
        Prop("color", "color", "Couleur des chiffres (rôle du thème ; encre par défaut en liste)."),
        Prop("layout", "choice", "row : chiffres côte à côte ; list : une ligne par chiffre, label en titre gras, sub en précision grise.",
             default="row", choices=["row", "list"]),
        Prop("tile", "bool", "En liste : chaque ligne dans un bandeau gris arrondi.", default=False),
        Prop("value_w", "number", "En liste : largeur de la colonne des chiffres (défaut : selon le plus long)."),
    ],
    render=_stats, example={"items": [{"value": "12", "label": "pays couverts"}, {"value": "3", "label": "langues"}, {"value": "98 %", "label": "de satisfaction"}]},
    tags=["chiffres"],
))


# --- pill ------------------------------------------------------------------------------------

def _pill(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    color = p["color"]
    outline = bool(p["outline"])
    text = str(p["text"]).upper() if outline else str(p["text"])
    if p["count"] and int(p["count"]) > 1:
        text += f"  ×{int(p['count'])}"
    pw = min(w, len(text) * 6.8 + 36)
    ph = h or 29
    box: dict = {"op": "box", "x": 0, "y": 0, "w": pw, "h": ph, "shape": "ROUND_RECTANGLE", "text": text,
                 "style": "pill", "size": p["size"], "align": "CENTER", "valign": "MIDDLE"}
    if outline:
        box.update({"fill": "background", "line": {"color": color, "weight": 2}, "color": color})
    else:
        box.update({"fill": color, "color": "on_dark" if color in _DARK_FILLS else "on_accent"})
    return [box], ph


register(Component(
    name="pill", description="Capsule (rectangle arrondi) pleine ou en contour, largeur ajustée au texte.",
    props=[
        Prop("text", "str", "Texte de la capsule.", required=True),
        Prop("color", "color", "Couleur de fond (ou du contour).", default="accent"),
        Prop("outline", "bool", "Contour seul, texte en capitales.", default=False),
        Prop("size", "number", "Taille de police.", default=11),
        Prop("count", "number", "Compteur « ×n » ajouté au texte quand il vaut 2 ou plus."),
    ],
    render=_pill, example={"text": "Google Ads", "outline": True}, tags=["texte"],
))


# --- checklist / chevrons / arrows ------------------------------------------------------------

def _check_items(items, x: float, y: float, w: float, gap: float, color: str, size: float, box: float) -> tuple[list[dict], float]:
    """Check boxes and their texts from (x, y); returns the ops and the bottom."""
    ops: list[dict] = []
    bottom = y
    for it in items:
        text, done = (it.get("text", ""), bool(it.get("done"))) if isinstance(it, dict) else (str(it), False)
        ops.append({"op": "box", "x": x, "y": y + 2, "w": box, "h": box, "fill": color if done else None,
                    "line": {"color": "ink", "weight": 2 if box >= 15 else 1.5}, "role": "check"})
        if done:
            k = box / 15
            ops.append({"op": "polyline", "points": [[x + 3.2 * k, y + 2 + 9 * k], [x + 6.1 * k, y + 2 + 12.6 * k], [x + 11.9 * k, y + 2 + 4.3 * k]],
                        "color": "ink", "weight": 2.25 * k})
        tx = x + box + 11
        th = max(gap - 6, _text_height(text, w - (tx - x), size))
        ops.append({"op": "text", "x": tx, "y": y - 2, "w": w - (tx - x), "h": th, "markdown": str(text), "style": "list", "size": size,
                    "small_ok": size < 11})
        bottom = max(bottom, y + box + 2, y - 2 + th)
        y += max(gap, th + 2)
    return ops, bottom


def _checklist(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    color = p["color"]
    groups = list(p["groups"] or [])
    if not groups:
        ops, bottom = _check_items(p["items"] or [], 0, 0, w, gap, color, 12, 15)
        return ops, h or bottom
    # numbered sections in columns: ① title, then compact items; groups fill the columns in order
    cols = max(1, int(p["cols"]))
    col_gap = 24.0
    col_w = (w - (cols - 1) * col_gap) / cols
    per_col = -(-len(groups) // cols)
    ops: list[dict] = []
    bottom = 0.0
    for c in range(cols):
        x = c * (col_w + col_gap)
        y = 0.0
        for k, g in enumerate(groups[c * per_col:(c + 1) * per_col]):
            n = c * per_col + k + 1
            ops.append({"op": "box", "x": x, "y": y, "w": 18, "h": 18, "shape": "ELLIPSE", "fill": color, "role": "group_num",
                        "text": str(n), "style": "badge", "size": 9, "small_ok": True, "bold": True, "color": "ink", "align": "CENTER", "valign": "MIDDLE"})
            ops.append({"op": "text", "x": x + 24, "y": y - 1, "w": col_w - 24, "h": 14 + INSETS, "text": str(g.get("title", "")).upper(),
                        "style": "card_label", "size": 10, "bold": True, "color": "ink", "role": "group_title"})
            y += 24
            item_ops, y = _check_items(g.get("items") or [], x + 2, y, col_w - 2, float(p["group_gap"]), color, 9.5, 11)
            ops.extend(item_ops)
            y += 14
        bottom = max(bottom, y - 14)
    return ops, h or bottom


register(Component(
    name="checklist", description="Liste à cases carrées ; les cases cochées sont pleines (accent) avec une coche. Avec `groups`, des sections numérotées ① ② ③ en une ou deux colonnes, cases et textes compacts (checklist de publication).",
    props=[
        Prop("items", "list", "Éléments : texte, ou {text, done} (ignoré quand groups est donné)."),
        Prop("gap", "number", "Pas vertical.", default=32),
        Prop("color", "color", "Couleur des cases cochées et des numéros de section.", default="accent"),
        Prop("groups", "list", "Sections : {title, items: [texte ou {text, done}]}.", default=[]),
        Prop("cols", "number", "Colonnes pour les sections.", default=1),
        Prop("group_gap", "number", "Pas vertical dans une section.", default=20),
    ],
    render=_checklist, example={"items": [{"text": "Sitemap XML soumis", "done": True}, "Balises canoniques", {"text": "Core Web Vitals", "done": False}]},
    tags=["texte"],
))


def _marker_list(marker: str, marker_color: str | None):
    def render(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
        size = float(p["size"])
        spacing = float(p["spacing"])
        runs = []
        for it in p["items"]:
            prefix: dict = {"text": f"{marker}  ", "bold": True}
            if marker_color:
                prefix["color"] = marker_color
            runs.append([prefix, {"text": str(it)}])
        n = max(1, len(runs))
        wrapped = sum(max(1, -(-len(str(it)) // max(1, int((w - 20) / (size * 0.46))))) for it in p["items"])
        height = h or (wrapped * size * LEADING + (n - 1) * spacing + INSETS)
        return [{"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": runs, "style": "list", "size": size, "spacing": spacing}], height
    return render


register(Component(
    name="chevrons", description="Liste à puces › (chevron accent), un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police.", default=12.5),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("›", "positive"), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))

register(Component(
    name="arrows", description="Liste à flèches →, un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police.", default=12.5),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("→", None), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))
