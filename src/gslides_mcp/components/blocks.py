"""Text-block components: bigstat (bare or in a panel beside a text), stats (row or list), pill, checklist, chevrons, arrows.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only. Body texts are drawn at
the theme's size (13 pt on the charter) and never shrink: a long text wraps
and its block grows; a text that cannot hold (a height forced by the caller)
leaves a ``warning`` op, returned by ``insert_component`` in ``warnings``.
"""

from __future__ import annotations

import re

from ..themes import Theme
from . import Component, Prop, register
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, _wrapped_lines, caps_centre, too_long, word_fit_size

_DARK_FILLS = {"surface_dark", "surface_dark_2", "ink", "text"}
_MD = re.compile(r"\*\*|__|==|`")
BODY_MIN = 13.0  # the charter's body floor, when a caller renders without a theme


def _box_h(text, width: float, size: float, wide: float = 1.0) -> float:
    """Text-box height of ``text`` (markdown marks ignored) wrapped in ``width`` pt at ``size`` pt, insets included."""
    return _wrapped_lines(_MD.sub("", str(text)), width, size * wide) * size * LEADING + INSETS


def _body_size(theme: Theme | None, style: str, asked=None) -> float:
    """Size of a body text in ``style``: the one asked, else the theme's, never under the style's floor."""
    if theme is None:  # rendered from another component without a theme: the charter's floor
        return max(float(asked or BODY_MIN), BODY_MIN)
    return max(float(asked or theme.size(style)), float(theme.size_floor(style) or 0))


# --- bigstat / stats ---------------------------------------------------------------------

PANEL_FILLS = {"dark": ("surface_dark", "on_dark"), "surface": ("surface", "ink"), "accent": ("accent", "ink")}
PANEL_MIN_H = 220.0
PANEL_PAD = 16.0
PANEL_LABEL, PANEL_SUB = 15.0, 11.0  # the label under the figure, the precision (caption) under it


def _bigstat_panel(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    """The figure in a tall panel (navy by default), its source at the foot, and the text column beside it.

    From the Pasteur paid-media deck: « -30 à -40 % / Audience SEO / 09/2026
    vs N-1 * » centred in a navy panel, « * Source Tendances SEMRUSH » at its
    foot, a bold lead and paragraphs with a ==highlighted== passage on the right.
    The text keeps the body size (13 pt): a long one makes the panel taller.
    """
    fill, fg = PANEL_FILLS[p["panel"]] if p["panel"] else (None, None)
    text = p["text"]
    bs = theme.size("body")
    pw = w * float(p["panel_w"]) if text else w
    tx = pw + 24
    tw = w - tx
    text_h = _box_h(text, tw, bs) if text else 0.0
    inner = pw - 2 * PANEL_PAD
    value = str(p["value"])
    # the figure stays on one line: it shrinks to the panel (Barlow bold digits ≈ 0.58 × size), down to 20 pt, then wraps
    size = max(20.0, min(40.0, (inner - 2 * INSET_X) / max(1, len(value) * 0.58)))
    value_color = p["color"] or fg or "ink"
    group = [("value", value, _box_h(value, inner, size, BOLD_WRAP), {"style": "stat_value", "size": round(size, 1), "color": value_color}),
             ("label", str(p["label"]), _box_h(p["label"], inner, PANEL_LABEL), {"style": "label", "size": PANEL_LABEL, "color": fg or "ink"})]
    if p["sub"]:
        # a precision (period, scope): a caption, as under the bare figure
        group.append(("sub", str(p["sub"]), _box_h(p["sub"], inner, PANEL_SUB), {"style": "caption", "size": PANEL_SUB, "color": fg or "muted"}))
    source_h = _box_h(p["source"], inner, theme.size("caption")) if p["source"] else 0.0
    group_h = sum(gh for _, _, gh, _ in group) - 4 * (len(group) - 1)  # each box starts 4 pt into the previous one's bottom inset
    natural = max(text_h, PANEL_MIN_H, group_h + source_h + 2 * PANEL_PAD)
    panel_h = h or natural
    warnings = []
    if h is not None and natural > h + 0.5:
        warnings.append(too_long("bigstat", "text" if text_h > h else "label", text if text_h > h else p["label"]))
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
                    "style": "caption", "size": theme.size("caption"), "color": fg or "muted", "align": "CENTER", "role": "source"})
    if text:
        ops.append({"op": "text", "x": tx, "y": 0, "w": tw, "h": panel_h, "markdown": str(text), "style": "body", "size": bs,
                    "highlight": p["highlight"], "valign": "MIDDLE", "role": "text"})
    return ops + warnings, panel_h


def _bigstat(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    if p["panel"] or p["text"]:
        return _bigstat_panel(p, theme, w, h)
    color = p["color"]
    ls = theme.size("stat_label")
    # one line of label keeps its 26 pt box; a label or a sub on two lines pushes what follows down
    label_h = round(_box_h(p["label"], w, ls, BOLD_WRAP))
    ops: list[dict] = [
        {"op": "text", "x": 0, "y": 0, "w": w, "h": 64 + INSETS, "text": str(p["value"]), "style": "stat_value",
         "color": color, "align": "CENTER"},
        {"op": "text", "x": 0, "y": 72, "w": w, "h": label_h, "text": str(p["label"]), "style": "stat_label",
         "color": color, "align": "CENTER"},
    ]
    height = 72.0 + label_h
    if p["sub"]:
        sub_h = round(_box_h(p["sub"], w, 11))
        ops.append({"op": "text", "x": 0, "y": height, "w": w, "h": sub_h, "text": str(p["sub"]), "style": "caption",
                    "size": 11, "align": "CENTER"})
        height += sub_h
    if h is not None and height > h + 0.5:
        ops.append(too_long("bigstat", "label", p["label"]))
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


LIST_GAP = 6.0


def _stat_items(items) -> list[tuple[str, str, str | None]]:
    return [(str(it.get("value", "")), str(it.get("label", "")), it.get("sub")) if isinstance(it, dict) else (str(it[0]), str(it[1]), None)
            for it in items]


def _stats_list(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    """Figures in a column on the left, each with a bold title and a grey line beside it.

    The memo-deck rows: grey rounded bands with ``tile`` (notation grid, points
    of progress), bare lines without (« profil moyen du testateur »). One value
    size and one row height for the whole list, so the figures line up. The
    grey line is body text (13 pt), so the title over it goes up to 15 pt.
    """
    rows = _stat_items(p["items"])
    tile = bool(p["tile"])
    pad = 8.0 if tile else 0.0
    size = 22.0 if tile else 18.0
    # a title over a grey line is bold and 2 pt above it; a bare label (« 70 % de femmes ») stays roman next to its bold figure
    titled = any(sub for _, _, sub in rows)
    sub_size = theme.size("label")
    label_size = sub_size + 2 if titled else sub_size
    longest = max((len(v) for v, _, _ in rows), default=1)
    value_w = float(p["value_w"] or min(max(longest * size * 0.6 + 2 * INSET_X + 8, w * 0.12), w * 0.32))
    # a figure does not wrap: it shrinks to its column (Barlow bold digits ≈ 0.58 × size), down to the floor, where it may
    size = max(float(theme.size_floor("stat_value") or 0), min(size, (value_w - 2 * INSET_X) / (longest * 0.58)))
    tx = pad + value_w + 6
    tw = w - tx - pad
    heights = [(_wrapped_lines(label, tw, label_size * (BOLD_WRAP if titled else 1.0)) * label_size
                + (_wrapped_lines(str(sub), tw, sub_size) * sub_size if sub else 0)) * LEADING + INSETS for _, label, sub in rows]
    value_h = max((_box_h(v, value_w, size, BOLD_WRAP) for v, _, _ in rows), default=0.0)
    row_h = max(max(heights, default=0.0), value_h) + (12 if tile else 0)
    natural = len(rows) * row_h + max(0, len(rows) - 1) * LIST_GAP
    if h and rows:
        row_h = max(row_h, (h - (len(rows) - 1) * LIST_GAP) / len(rows))
    color = p["color"] or "ink"  # mint figures vanish on a grey band
    ops: list[dict] = []
    for i, (value, label, sub) in enumerate(rows):
        y = i * (row_h + LIST_GAP)
        if tile:
            ops.append({"op": "box", "x": 0, "y": y, "w": w, "h": row_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "row"})
        ops.append({"op": "text", "x": pad, "y": y, "w": value_w, "h": row_h, "text": value, "style": "stat_value", "size": round(size, 1),
                    "color": color, "valign": "MIDDLE", "role": "value"})
        paras = [[{"text": label, "bold": titled, "size": label_size, "color": "ink"}]]
        if sub:
            paras.append([{"text": str(sub), "size": sub_size, "color": "muted"}])
        ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": row_h, "runs": paras, "style": "label", "valign": "MIDDLE", "role": "text"})
    height = len(rows) * row_h + max(0, len(rows) - 1) * LIST_GAP
    if h is not None and natural > h + 0.5:
        ops.append(too_long("stats", "label", max((lb for _, lb, _ in rows), key=len, default="")))
    return ops, h or height


def _stats(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    if p["layout"] == "list":
        return _stats_list(p, theme, w, h)
    items = [(it.get("value"), it.get("label"), it.get("sub")) if isinstance(it, dict) else (it[0], it[1], None) for it in p["items"]]
    n = max(1, len(items))
    per_w = w / n
    color = p["color"]
    # one label size for the row (stat_label, a small style: 12.5 pt, down to its 10 pt floor so a word is not cut)
    floor = float(theme.size_floor("stat_label") or 10)
    ls = min((word_fit_size(str(lb), per_w, 12.5, floor=floor, glyph=GLYPH_WRAP * BOLD_WRAP) for _, lb, _ in items), default=12.5)
    # one geometry for the row: every label box as tall as the tallest, every sub under it
    label_h = max((_box_h(lb, per_w, ls, BOLD_WRAP) for _, lb, _ in items), default=0.0)
    sub_y = 56 + max(label_h, 18 + INSETS) - 2
    ops: list[dict] = []
    height = max(82.0, 56 + label_h)
    for i, (value, label, sub) in enumerate(items):
        x = i * per_w
        ops.append({"op": "text", "x": x, "y": 0, "w": per_w, "h": 46 + INSETS, "text": str(value), "style": "stat_value",
                    "size": 38, "color": color, "align": "CENTER"})
        ops.append({"op": "text", "x": x, "y": 56, "w": per_w, "h": max(label_h, 18 + INSETS), "text": str(label), "style": "stat_label",
                    "size": ls, "color": color, "align": "CENTER"})
        if sub:
            sh = _box_h(sub, per_w, theme.size("caption"))
            ops.append({"op": "text", "x": x, "y": sub_y, "w": per_w, "h": sh, "text": str(sub), "style": "caption", "align": "CENTER", "role": "sub"})
            height = max(height, sub_y + sh)
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
    size = max(float(p["size"] or theme.size("pill")), float(theme.size_floor("pill") or 0))
    pw = min(w, len(text) * size * 0.62 + 36)  # bold glyphs ≈ 0.62 × size, 18 pt of air on each side
    # one line in a 29 pt capsule; a text wider than the box wraps and the capsule grows
    lines = _wrapped_lines(text, pw, size * (1.3 if outline else BOLD_WRAP))
    ph = h or max(29.0, round(lines * size * LEADING + INSETS + 6))
    box: dict = {"op": "box", "x": 0, "y": 0, "w": pw, "h": ph, "shape": "ROUND_RECTANGLE", "text": text,
                 "style": "pill", "size": size, "align": "CENTER", "valign": "MIDDLE"}
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
        Prop("size", "number", "Taille de police (défaut : style pill du thème, 11 pt)."),
        Prop("count", "number", "Compteur « ×n » ajouté au texte quand il vaut 2 ou plus."),
    ],
    render=_pill, example={"text": "Google Ads", "outline": True}, tags=["texte"],
))


# --- checklist / chevrons / arrows ------------------------------------------------------------

def _check_items(items, x: float, y: float, w: float, gap: float, color: str, size: float, box: float) -> tuple[list[dict], float]:
    """Check boxes and their texts from (x, y); returns the ops and the bottom.

    Each box is centred on the capitals of its text's first line; a text on
    several lines pushes the next item down (``gap`` is the minimum pitch).
    """
    ops: list[dict] = []
    bottom = y
    for it in items:
        text, done = (it.get("text", ""), bool(it.get("done"))) if isinstance(it, dict) else (str(it), False)
        by = caps_centre(y, size) - box / 2
        ops.append({"op": "box", "x": x, "y": by, "w": box, "h": box, "fill": color if done else None,
                    "line": {"color": "ink", "weight": 2 if box >= 15 else 1.5}, "role": "check"})
        if done:
            k = box / 15
            ops.append({"op": "polyline", "points": [[x + 3.2 * k, by + 9 * k], [x + 6.1 * k, by + 12.6 * k], [x + 11.9 * k, by + 4.3 * k]],
                        "color": "ink", "weight": 2.25 * k})
        tx = x + box + 11
        th = max(gap - 6, _box_h(text, w - (tx - x), size))
        ops.append({"op": "text", "x": tx, "y": y, "w": w - (tx - x), "h": th, "markdown": str(text), "style": "list", "size": size})
        bottom = max(bottom, by + box, y + th)
        y += max(gap, th + 2)
    return ops, bottom


GROUP_DISC = 18.0  # checklist sections: the number disc in front of the title
CAPS_BOLD = 1.3    # bold capitals run this much wider than the wrap estimate


def _checklist(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    color = p["color"]
    groups = list(p["groups"] or [])
    size = _body_size(theme, "list")  # items at the body size (13 pt), in sections as in the plain list
    if not groups:
        ops, bottom = _check_items(p["items"] or [], 0, 0, w, gap, color, size, 15)
        return ops, h or bottom
    # numbered sections in columns: ① title, then compact items; groups fill the columns in order,
    # the sections of a row starting at one height in every column
    cols = max(1, int(p["cols"]))
    col_gap = 24.0
    col_w = (w - (cols - 1) * col_gap) / cols
    per_col = -(-len(groups) // cols)
    ts = size + 2  # the section title stays above its items: body + 2, bold capitals
    titles = [str(g.get("title", "")).upper() for g in groups]
    title_hs = [_box_h(t, col_w - 24, ts, CAPS_BOLD) for t in titles]
    item_gap = float(p["group_gap"])

    def section(idx: int, x: float, y: float) -> tuple[list[dict], float]:
        # the number disc centred on the capitals of the title's first line, the items under the title
        ops = [{"op": "box", "x": x, "y": caps_centre(y, ts) - GROUP_DISC / 2, "w": GROUP_DISC, "h": GROUP_DISC, "shape": "ELLIPSE",
                "fill": color, "role": "group_num", "text": str(idx + 1), "style": "badge", "size": 10, "bold": True, "color": "ink",
                "align": "CENTER", "valign": "MIDDLE"},
               {"op": "text", "x": x + 24, "y": y, "w": col_w - 24, "h": title_hs[idx], "text": titles[idx],
                "style": "card_title", "size": ts, "bold": True, "color": "ink", "role": "group_title"}]
        item_ops, bottom = _check_items(groups[idx].get("items") or [], x + 2, y + title_hs[idx] - 2, col_w - 2, item_gap, color, size, 11)
        return ops + item_ops, bottom

    # the tops of the rows of sections: each row starts under the tallest section of the previous one
    tops = [0.0]
    for k in range(per_col):
        row = [idx for idx in (c * per_col + k for c in range(cols)) if idx < len(groups)]
        tops.append(max(section(idx, 0.0, tops[-1])[1] for idx in row) + 14)
    ops: list[dict] = []
    for c in range(cols):
        for k in range(per_col):
            idx = c * per_col + k
            if idx < len(groups):
                ops.extend(section(idx, c * (col_w + col_gap), tops[k])[0])
    return ops, h or tops[-1] - 14


register(Component(
    name="checklist", description="Liste à cases carrées ; les cases cochées sont pleines (accent) avec une coche. Avec `groups`, des sections numérotées ① ② ③ en une ou deux colonnes, cases compactes (checklist de publication).",
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
    def render(p: dict, theme: Theme | None, w: float, h: float | None) -> tuple[list[dict], float]:
        # body text: the theme's list size (13 pt), never under the floor, even when another block asks for less
        size = _body_size(theme, "list", p["size"])
        spacing = float(p["spacing"])
        runs = []
        for it in p["items"]:
            prefix: dict = {"text": f"{marker}  ", "bold": True}
            if marker_color:
                prefix["color"] = marker_color
            runs.append([prefix, {"text": str(it)}])
        n = max(1, len(runs))
        lines = sum(_wrapped_lines(f"{marker}  {it}", w, size) for it in p["items"])
        natural = lines * size * LEADING + (n - 1) * spacing + INSETS
        height = h or natural
        ops: list[dict] = [{"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": runs, "style": "list", "size": size, "spacing": spacing}]
        if h is not None and natural > h + 0.5:
            ops.append(too_long("chevrons" if marker == "›" else "arrows", "items", max((str(it) for it in p["items"]), key=len, default="")))
        return ops, height
    return render


register(Component(
    name="chevrons", description="Liste à puces › (chevron accent), un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police (défaut : style list du thème, 13 pt ; jamais moins)."),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("›", "positive"), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))

register(Component(
    name="arrows", description="Liste à flèches →, un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police (défaut : style list du thème, 13 pt ; jamais moins)."),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("→", None), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))
