"""Built-in components, ported from the Periscope Slidev theme's P*.vue
patterns (and their native-PPTX mirror) to draw ops.

Geometry is in points at origin; colors and text are theme roles / named
text styles only. Each ``render(props, theme, w, h)`` returns
``(ops, height)`` — ``h`` forces the box height when the caller has one.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register, shift

PAD = 14  # inner padding of boxed components
INSETS = 8  # Google's fixed top+bottom text-box insets
INSET_X = 7.2  # Google's fixed left text-box inset


def _lines(text: str) -> int:
    return max(1, str(text).count("\n") + 1)


GLYPH = 0.46        # average glyph width as a fraction of the font size (Barlow-ish)
LEADING = 1.35      # line height as a multiple of the font size (Google default spacing)
BULLET_INDENT = 30  # pt taken by a bullet + tab in Google Slides


def _text_height(text: str, width: float, size: float) -> float:
    """Box height for ``text`` wrapped in ``width`` pt at ``size`` pt, insets included."""
    return _wrapped_lines(text, width, size) * size * LEADING + INSETS


def _wrapped_lines(text: str, width: float, size: float) -> int:
    """Lines a text will take once wrapped in ``width`` pt (insets excluded)."""
    total = 0
    for raw in str(text).split("\n"):
        line = raw.strip()
        avail = width - 2 * INSET_X
        if line.startswith(("- ", "* ", "• ")):
            line = line[2:]
            avail -= BULLET_INDENT
        per_line = max(1, int(avail / (size * GLYPH)))
        total += max(1, -(-len(line) // per_line))
    return max(1, total)


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v:g}" if isinstance(v, float) else str(v)


def _nice_max(values: list[float]) -> float:
    raw = max(values) if values else 1
    if raw <= 0:
        return 1
    p = 10 ** max(0, len(str(int(raw))) - 1)
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * p >= raw:
            return m * p
    return raw


# --- kpi ------------------------------------------------------------------------

def _kpi(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    fg = {"color": "on_dark"} if p["dark"] else {}
    label: dict = {"op": "text", "x": PAD, "y": 36, "w": w - PAD, "h": 18, "style": "kpi_label", "role": "label", **fg}
    if p.get("note"):
        # « Collecte (GA4) » : the precision in small muted type after the label
        label["runs"] = [[{"text": str(p["label"])}, {"text": " " + str(p["note"]), "size": 10, "color": "muted"}]]
    else:
        label["text"] = str(p["label"])
    ops: list[dict] = [
        {"op": "box", "x": 0, "y": 0, "w": 5, "h": 61, "fill": "accent", "role": "bar"},
        {"op": "text", "x": PAD, "y": -3, "w": w - PAD, "h": 36, "text": str(p["value"]), "style": "kpi_value", **fg},
        label,
    ]
    height = 61.0
    if p["delta"]:
        sign = "positive" if str(p["delta"]).strip().startswith("+") else "negative"
        ops.append({"op": "text", "x": PAD, "y": 58, "w": w - PAD, "h": 16, "text": str(p["delta"]),
                    "style": "kpi_delta", "color": sign})
        height = 76.0
    return ops, h or height


register(Component(
    name="kpi", description="Chiffre clé : barre accent à gauche, valeur en gros, libellé, delta signé coloré (+ positif / − négatif).",
    props=[
        Prop("value", "str", "La valeur affichée en gros, déjà formatée (ex. '1 625 394').", required=True),
        Prop("label", "str", "Libellé sous la valeur.", required=True),
        Prop("delta", "str", "Variation signée, ex. '+12 %' ou '-3,4 pts'. Le signe pilote la couleur."),
        Prop("note", "str", "Précision en petit après le libellé, ex. '(GA4)' ou '(régie)'."),
        Prop("dark", "bool", "Texte clair pour fond sombre.", default=False),
    ],
    render=_kpi, example={"value": "196 623 €", "label": "Collecte", "note": "(GA4)", "delta": "+108,49 %"}, tags=["chiffres"],
))


ROW_LABEL_W = 90.0  # kpi_grid: width of the row-label column


def _kpi_grid(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = p["items"]
    rows = [str(r) for r in (p["rows"] or [])]
    cols = int(p["cols"] or (-(-len(items) // len(rows)) if rows else len(items)) or 1)
    x0 = ROW_LABEL_W if rows else 0.0
    col_w = (w - x0) / cols
    row_gap = float(p["row_gap"])
    ops: list[dict] = []
    height = 0.0
    for i, item in enumerate(items):
        sub, sub_h = _kpi({"value": item.get("value", ""), "label": item.get("label", ""), "note": item.get("note"),
                           "delta": item.get("delta"), "dark": p["dark"]}, theme, col_w - 12, None)
        y = (i // cols) * row_gap
        ops.extend(shift(sub, x0 + (i % cols) * col_w, y))
        height = max(height, y + sub_h)
    for r, label in enumerate(rows):
        ops.append({"op": "text", "x": 0, "y": r * row_gap + 12, "w": ROW_LABEL_W - 8, "h": 40, "text": label, "style": "label",
                    "bold": True, "color": "on_dark" if p["dark"] else "ink", "valign": "MIDDLE", "role": "row_label"})
    return ops, h or height


register(Component(
    name="kpi_grid", description="Grille de KPI (composant kpi répété en colonnes), avec en option un libellé de ligne à gauche (Marque / Hors marque).",
    props=[
        Prop("items", "list", "Liste de {value, label, delta?, note?}.", required=True),
        Prop("cols", "number", "Nombre de colonnes (défaut : un par item, ou items / rows)."),
        Prop("rows", "list", "Libellés de ligne en gras à gauche, un par rangée ; cols = indicateurs par rangée."),
        Prop("row_gap", "number", "Hauteur d'une rangée en pt.", default=90),
        Prop("dark", "bool", "Texte clair pour fond sombre.", default=False),
    ],
    render=_kpi_grid,
    example={"items": [{"value": "18 336 040", "label": "Impressions", "delta": "+170,50 %"}, {"value": "101 216", "label": "Clics", "delta": "+109,71 %"},
                       {"value": "130 311 €", "label": "Investissements", "delta": "+35,29 %"}, {"value": "1,61", "label": "ROAS", "note": "GA4", "delta": "+64,79 %"}],
             "cols": 4},
    tags=["chiffres"],
))


# --- card -----------------------------------------------------------------------

_CARD = {
    # variant: (fill, line, label/title color, big color, body color, num color)
    "light":   ("surface", None, "ink", "accent", "text", "ink"),
    "dark":    ("surface_dark", None, "accent", "accent", "on_dark", "accent"),
    "mint":    ("accent", None, "ink", "ink", "ink", "ink"),
    "acid":    ("accent_alt", None, "ink", "ink", "ink", "ink"),
    "outline": (None, {"color": "accent", "weight": 1.5}, "ink", "accent", "text", "ink"),
    "plain":   (None, None, "ink", "accent", "text", "ink"),
}


def _card(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    fill, line, head_col, big_col, body_col, num_col = _CARD[p["variant"]]
    inner = w - 2 * PAD
    texts: list[dict] = []
    icon_ops: list[dict] = []
    y = float(PAD)
    if p["icon"]:
        # picto in a white disc (PCard icon slot); the picto is tinted by the theme
        icon_ops.append({"op": "box", "x": PAD, "y": y, "w": 44, "h": 44, "shape": "ELLIPSE", "fill": "background"})
        icon_ops.append({"op": "image", "x": PAD + 10, "y": y + 10, "w": 24, "h": 24,
                         "asset": str(p["icon"]), "tint": p["icon_color"]})
        y += 44 + 10
    if p["num"]:
        texts.append({"op": "text", "x": w - PAD - 44, "y": PAD - 4, "w": 44, "h": 24, "text": str(p["num"]),
                      "style": "card_num", "color": num_col, "align": "END"})
    if p["label"]:
        texts.append({"op": "text", "x": PAD, "y": y, "w": inner - (48 if p["num"] else 0), "h": 14 + INSETS,
                      "text": str(p["label"]).upper(), "style": "card_label", "color": head_col})
        y += 18
    if p["big"]:
        texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": 34 + INSETS, "text": str(p["big"]),
                      "style": "card_big", "color": big_col})
        y += 42
    dot: list[dict] = []
    if p["title"]:
        tx = PAD
        if p["dot"]:
            # in the text column (after Google's left inset), centred on the caps
            dot.append({"op": "box", "x": PAD + INSET_X, "y": y + 7.5, "w": 7, "h": 7, "shape": "ELLIPSE", "fill": "accent"})
            tx = PAD + 11
        title_h = _text_height(str(p["title"]).upper(), w - tx - PAD, 10.5 * 1.1)  # caps are wider
        texts.append({"op": "text", "x": tx, "y": y, "w": w - tx - PAD, "h": title_h, "text": str(p["title"]).upper(),
                      "style": "card_title", "color": head_col})
        y += title_h + 2
    if p["body"]:
        body_h = (h - y - PAD) if h else _text_height(p["body"], inner, 11)
        texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": body_h, "markdown": str(p["body"]),
                      "style": "card_body", "color": body_col})
        y += body_h
    height = h or (y + PAD)
    ops: list[dict] = [{"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": fill, "line": line, "role": "card"}]
    return ops + icon_ops + dot + texts, height


register(Component(
    name="card", description="Carte plate : fond clair/sombre/menthe/acide, contour, ou sans fond (plain), avec picto, libellé caps, gros chiffre, numéro, titre (point accent) et corps markdown.",
    props=[
        Prop("variant", "choice", "Habillage de la carte.", default="light", choices=list(_CARD)),
        Prop("label", "str", "Petit libellé en capitales en tête."),
        Prop("big", "str", "Gros chiffre ou valeur."),
        Prop("num", "str", "Numéro en haut à droite (01, 02…)."),
        Prop("title", "str", "Titre en capitales."),
        Prop("body", "markdown", "Corps de la carte (markdown : gras, puces)."),
        Prop("dot", "bool", "Point accent devant le titre.", default=False),
        Prop("icon", "image", "Picto dans un disque blanc en tête : nom d'un PNG du dossier d'assets Drive (ex. 'bolt') ou chemin local."),
        Prop("icon_color", "color", "Teinte du picto (rôle du thème).", default="ink"),
    ],
    render=_card,
    example={"variant": "light", "num": "01", "title": "Visibilité", "body": "- Autorité de domaine\n- Contenu evergreen", "dot": True},
    tags=["cartes"],
))


def _card_grid(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    cards = list(p["cards"])
    cols = int(p["cols"] or len(cards) or 1)
    gap = float(p["gap"])
    card_w = (w - (cols - 1) * gap) / cols
    from . import validate, get
    spec = get("card")
    validated = [validate(spec, c) for c in cards]
    rows: list[list[dict]] = [validated[i:i + cols] for i in range(0, len(validated), cols)]
    ops: list[dict] = []
    y = 0.0
    for row in rows:
        natural = [_card(c, theme, card_w, None)[1] for c in row]
        row_h = h or max(natural)
        for j, c in enumerate(row):
            sub, _ = _card(c, theme, card_w, row_h)
            ops.extend(shift(sub, j * (card_w + gap), y))
        y += row_h + gap
    return ops, y - gap if rows else 0.0


register(Component(
    name="card_grid", description="Rangée(s) de cartes de même hauteur (composant card répété), avec picto, libellé, titre et corps.",
    props=[
        Prop("cards", "list", "Props de chaque carte (voir card).", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cartes.", default=12),
    ],
    render=_card_grid,
    example={"cards": [
        {"icon": "bolt", "label": "Constat", "title": "Un levier d'engagement", "body": "9 874 joueurs, 12 851 parties."},
        {"icon": "people", "label": "Actif", "title": "Une audience à capitaliser", "body": "4 438 visiteurs revenants."},
        {"icon": "lightbulb", "label": "À renforcer", "title": "Le pont jeu → cause → don", "body": "Seuls 16 % ouvrent une cause."}]},
    tags=["cartes"],
))


# --- callout ----------------------------------------------------------------------

def _callout(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    kind = p["type"]
    body_col = "on_dark" if kind == "dark" else "text"
    y = 10.0
    texts: list[dict] = []
    if p["title"]:
        texts.append({"op": "text", "x": 16, "y": y, "w": w - 24, "h": 14 + INSETS, "text": str(p["title"]),
                      "style": "callout_title", "color": f"callout_{kind}_title"})
        y += 20
    body_h = (h - y - 12) if h else _text_height(p["body"], w - 24, 11)
    texts.append({"op": "text", "x": 16, "y": y, "w": w - 24, "h": body_h, "markdown": str(p["body"]),
                  "style": "callout_body", "color": body_col})
    height = h or (y + body_h + 12)
    ops = [
        {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": f"callout_{kind}_bg"},
        {"op": "box", "x": 0, "y": 0, "w": 4, "h": height, "fill": f"callout_{kind}_bar"},
    ]
    return ops + texts, height


register(Component(
    name="callout", description="Encadré plat avec barre accent à gauche : info, idée, avertissement, alerte ou sombre.",
    props=[
        Prop("type", "choice", "Ton de l'encadré.", default="info", choices=["info", "idea", "warn", "alert", "dark"]),
        Prop("title", "str", "Titre en gras (optionnel)."),
        Prop("body", "markdown", "Contenu (markdown).", required=True),
    ],
    render=_callout, example={"type": "idea", "title": "À retenir", "body": "Le maillage interne est le levier le moins coûteux."},
    tags=["texte"],
))


# --- badge ------------------------------------------------------------------------

def _badge(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    text = str(p["text"]).upper()
    bw = min(w, len(text) * 5.4 + 14)
    bh = h or 16
    ops = [{"op": "box", "x": 0, "y": 0, "w": bw, "h": bh, "fill": p["fill"], "text": text,
            "style": "badge", "color": p["color"], "align": "CENTER", "valign": "MIDDLE"}]
    return ops, bh


register(Component(
    name="badge", description="Pastille / tag en capitales (statut, levier, priorité).",
    props=[
        Prop("text", "str", "Texte de la pastille.", required=True),
        Prop("fill", "color", "Fond (rôle ou token du thème).", default="accent"),
        Prop("color", "color", "Couleur du texte.", default="on_accent"),
    ],
    render=_badge, example={"text": "Priorité haute"}, tags=["texte"],
))


# --- steps ------------------------------------------------------------------------

def _steps(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    dark = p["dark"]
    ops: list[dict] = []
    y = 0.0
    bottom = 0.0
    for i, item in enumerate(p["items"]):
        item_h = max(23, _text_height(item, w - 32, 11))
        bottom = y + 2 + item_h
        ops.append({"op": "box", "x": 0, "y": y, "w": 23, "h": 23, "shape": "ELLIPSE",
                    "fill": "step_bg_dark" if dark else "step_bg", "text": str(i + 1), "style": "step_number",
                    "color": "step_number_dark" if dark else None, "align": "CENTER", "valign": "MIDDLE"})
        ops.append({"op": "text", "x": 32, "y": y + 2, "w": w - 32, "h": item_h, "markdown": str(item),
                    "style": "step_text", "color": "on_dark" if dark else None})
        y += item_h + 10
    return ops, h or bottom


register(Component(
    name="steps", description="Liste numérotée à pastilles : cercle + numéro + texte markdown.",
    props=[
        Prop("items", "list", "Textes des étapes (markdown).", required=True),
        Prop("dark", "bool", "Version pour fond sombre.", default=False),
    ],
    render=_steps, example={"items": ["Audit technique", "Plan de **contenus**", "Netlinking"]}, tags=["texte"],
))


# --- quote ------------------------------------------------------------------------

def _quote(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    dark = p["dark"]
    quote_h = _text_height(p["text"], w - 2 * PAD - 8, 12)
    y = float(PAD)
    texts: list[dict] = [{"op": "text", "x": PAD + 4, "y": y, "w": w - 2 * PAD - 8, "h": quote_h,
                          "markdown": str(p["text"]), "style": "quote", "color": "on_dark" if dark else None}]
    y += quote_h
    if p["author"]:
        runs = [{"text": str(p["author"]), "bold": True}]
        if p["role"]:
            runs.append({"text": f" — {p['role']}"})
        texts.append({"op": "text", "x": PAD + 4, "y": y + 2, "w": w - 2 * PAD - 8, "h": 14 + INSETS, "runs": [runs],
                      "style": "quote_author", "color": "on_dark" if dark else None})
        y += 24
    height = h or (y + PAD)
    ops = [{"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": None, "line": {"color": "accent", "weight": 2}}]
    return ops + texts, height


register(Component(
    name="quote", description="Citation : encadré liseré accent, texte gras italique, auteur et rôle.",
    props=[
        Prop("text", "markdown", "La citation (guillemets inclus si voulus).", required=True),
        Prop("author", "str", "Auteur."),
        Prop("role", "str", "Fonction / entreprise, après l'auteur."),
        Prop("dark", "bool", "Version pour fond sombre.", default=False),
    ],
    render=_quote, example={"text": "« Une agence qui comprend nos enjeux. »", "author": "Client X", "role": "Directrice marketing"},
    tags=["texte"],
))


# --- table ------------------------------------------------------------------------

ICON_COL_W = 26.0  # table: width of the leading picto column


def _table(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    rows = [list(r) for r in p["rows"]]
    row_h = float(p["row_h"])
    heights = [float(v) if v else row_h for v in (p["row_heights"] or [])] + [row_h] * (len(rows) - len(p["row_heights"] or []))
    last = len(rows) - 1
    icons = list(p["icons"] or [])
    col_w = list(p["col_w"] or [])
    align = list(p["align"] or [])
    ops: list[dict] = []
    if icons:
        # a narrow empty column in front, the pictos drawn over its cells (contain)
        rows = [[""] + r for r in rows]
        n_c = max(len(r) for r in rows)
        col_w = [ICON_COL_W] + (col_w or [(w - ICON_COL_W) / (n_c - 1)] * (n_c - 1))
        align = [None] + align
        icon_w = float(p["icon_w"])
        y = heights[0] if p["header"] else 0.0
        for i, icon in enumerate(icons):
            r = i + (1 if p["header"] else 0)
            if r >= len(rows):
                break
            if icon:
                ops.append({"op": "image", "x": (ICON_COL_W - icon_w) / 2 + 2, "y": y + (heights[r] - icon_w) / 2, "w": icon_w, "h": icon_w,
                            "asset": str(icon), "contain": True, "role": "icon"})
            y += heights[r]
    total = p["total_row"] and last > 0
    cell_text_colors: dict = {}
    for j in p["delta_cols"] or []:
        jj = int(j) + (1 if icons else 0)
        for i in range(1 if p["header"] else 0, len(rows) - (1 if total else 0)):
            txt = str(rows[i][jj]).strip() if jj < len(rows[i]) else ""
            if txt.startswith("+"):
                cell_text_colors[(i, jj)] = "positive"
            elif txt.startswith(("-", "−")):
                cell_text_colors[(i, jj)] = "negative"
    op: dict = {
        "op": "table", "x": 0, "y": 0, "w": w, "rows": rows, "col_w": col_w or None, "row_h": row_h, "row_heights": heights,
        "header": {"fill": "accent", "color": "on_accent", "bold": True} if p["header"] else None,
        "banding": ["background", "surface"],
        "first_col_bold": True,
        "borders": {"color": "rule", "weight": 1, "position": "INNER_HORIZONTAL"},
        "align": align or None,
        "size": p["size"],
        "row_fills": {last: "accent"} if total else {},
        "bold_rows": [last] if total else [],
        "cell_text_colors": cell_text_colors,
    }
    return [op] + ops, sum(heights)


register(Component(
    name="table", description="Tableau charté : en-tête accent, première colonne en gras, lignes alternées, filets horizontaux fins, ligne de total optionnelle ; pictos par ligne et colonnes de variation colorées par signe en option.",
    props=[
        Prop("rows", "list", "Lignes (la première est l'en-tête), listes de chaînes.", required=True),
        Prop("col_w", "list", "Largeurs de colonnes en pt (défaut : réparties)."),
        Prop("row_h", "number", "Hauteur de ligne en pt.", default=24),
        Prop("row_heights", "list", "Hauteur par ligne en pt (null = row_h)."),
        Prop("header", "bool", "La première ligne est un en-tête.", default=True),
        Prop("total_row", "bool", "La dernière ligne est un total (fond accent, gras).", default=False),
        Prop("align", "list", "Alignement par colonne : START, CENTER, END ou null."),
        Prop("size", "number", "Taille de police (défaut : style table_cell du thème)."),
        Prop("icons", "list", "Un picto (asset) ou null par ligne de données : ajoute une colonne étroite en tête (logos de canaux)."),
        Prop("icon_w", "number", "Taille des pictos.", default=16),
        Prop("delta_cols", "list", "Index (0-based, hors colonne picto) des colonnes « vs N-1 » : + en positif, - en négatif."),
    ],
    render=_table,
    example={"rows": [["Levier", "Budget", "Part"], ["Google Ads", "18 000 €", "45 %"], ["Meta", "12 000 €", "30 %"], ["Total", "30 000 €", "75 %"]],
             "align": [None, "END", "END"], "total_row": True},
    tags=["données"],
))


# --- charts -----------------------------------------------------------------------

def _frame_h(p: dict) -> float:
    """Height the optional title / panel frame adds around a chart."""
    from .axes import PANEL_PAD, TITLE_H
    return (TITLE_H + 2 if p.get("title") else 0.0) + (2 * PANEL_PAD if p.get("panel") else 0.0)


def _chart_bars(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    from .axes import (axis_width, baseline_op, divider_height, divider_ops, fmt_value, inner_width, panelize,
                       thin_labels, y_axis_ops)

    w_in = inner_width(w, p)
    labels, values = list(p["labels"]), [float(v) for v in p["values"]]
    n = max(1, len(values))
    vmax = float(p["max"]) if p["max"] else _nice_max(values)
    unit = p["unit"] or ""
    colors = list(p["colors"] or [])
    fill = lambda i: colors[i] if i < len(colors) and colors[i] else p["color"]  # noqa: E731
    ops: list[dict] = []
    if p["horizontal"]:
        row_h, gap = 22.0, 6.0
        label_w = w_in * 0.3
        value_w = 52.0
        track_x = label_w + 6
        track_w = w_in - track_x - value_w - 6
        for i, (lab, v) in enumerate(zip(labels, values)):
            y = i * (row_h + gap)
            ops.append({"op": "text", "x": 0, "y": y, "w": label_w, "h": row_h, "text": str(lab),
                        "style": "chart_label", "align": "END", "valign": "MIDDLE"})
            ops.append({"op": "box", "x": track_x, "y": y + 5, "w": track_w, "h": row_h - 10, "fill": "surface", "role": "track"})
            ops.append({"op": "box", "x": track_x, "y": y + 5, "w": track_w * v / vmax, "h": row_h - 10, "fill": fill(i), "role": "bar"})
            if p["show_values"]:
                ops.append({"op": "text", "x": track_x + track_w + 6, "y": y, "w": value_w, "h": row_h,
                            "text": fmt_value(v, unit), "style": "chart_value", "valign": "MIDDLE"})
        return panelize(ops, n * row_h + (n - 1) * gap, w, p) if (p.get("title") or p.get("panel")) \
            else (ops, h or (n * row_h + (n - 1) * gap))

    height = (h - _frame_h(p)) if h else 150.0
    label_h, value_h = 14.0 + INSETS, 14.0 + INSETS
    ml = axis_width(vmax, unit) + 6 if p["y_axis"] else 0.0
    y0 = (value_h + 2 if p["show_values"] else 2) + divider_height(p["dividers"])
    y1 = height - label_h - 4
    px, pw = ml, w_in - ml
    slot = pw / n
    bar_w = slot * 0.6
    if p["y_axis"]:
        ops += y_axis_ops(px, y0, pw, y1 - y0, vmax, unit, side="left", label_w=ml - 6)
    shown = thin_labels(labels, slot)
    for i, (lab, v) in enumerate(zip(labels, values)):
        bh = (y1 - y0) * v / vmax
        x = px + i * slot + slot * 0.2
        ops.append({"op": "box", "x": x, "y": y1 - bh, "w": bar_w, "h": bh, "fill": fill(i), "role": "bar"})
        if p["show_values"]:
            ops.append({"op": "text", "x": px + i * slot, "y": y1 - bh - value_h + 2, "w": slot, "h": value_h,
                        "text": fmt_value(v, unit), "style": "chart_value", "align": "CENTER", "role": "value"})
        if shown[i]:
            lw = max(slot, 48.0)
            ops.append({"op": "text", "x": px + (i + 0.5) * slot - lw / 2, "y": y1 + 3, "w": lw, "h": label_h, "text": str(lab),
                        "style": "chart_label", "align": "CENTER", "role": "label"})
    ops += divider_ops(p["dividers"], [str(lb) for lb in labels], px, y0, slot, y1 - y0)
    ops.append(baseline_op(px, y1, pw))
    return panelize(ops, height, w, p)


register(Component(
    name="chart_bars", description="Histogramme vertical (barres + valeurs + libellés, axe Y gradué et séparateurs de périodes en option, une couleur par barre possible) ou barres horizontales sur piste grise ; titre et panneau optionnels.",
    props=[
        Prop("labels", "list", "Libellés des barres.", required=True),
        Prop("values", "list", "Valeurs numériques, même longueur que labels.", required=True),
        Prop("horizontal", "bool", "Barres horizontales avec piste.", default=False),
        Prop("unit", "str", "Suffixe des valeurs, ex. ' %'."),
        Prop("max", "number", "Maximum de l'échelle (défaut : arrondi au-dessus du max)."),
        Prop("show_values", "bool", "Afficher les valeurs.", default=True),
        Prop("color", "color", "Couleur des barres.", default="accent"),
        Prop("colors", "list", "Une couleur par barre (rôles du thème, ex. regie_google), prime sur color."),
        Prop("y_axis", "bool", "Axe Y gradué avec grille (vertical).", default=False),
        Prop("dividers", "list", "Séparateurs de périodes (vertical) : {after: libellé, left?, right?, color?, dash?}.", default=[]),
        Prop("title", "str", "Titre du graphique, en petit et centré au-dessus."),
        Prop("panel", "bool", "Fond gris clair arrondi autour du graphique (style bilan).", default=False),
    ],
    render=_chart_bars,
    example={"labels": ["Google", "Bing", "Facebook", "Instagram"], "values": [3.9, 2.5, 3.45, 1.5],
             "colors": ["regie_google", "regie_bing", "regie_facebook", "regie_instagram"], "y_axis": True, "title": "ROAS par régie"},
    tags=["graphiques"],
))


def _chart_line(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    from .axes import AXIS_W, GRID_W, LEGEND_H, LINE_W, MARKER, auto, inner_width, legend_ops, panelize, thin_labels

    w_in = inner_width(w, p)
    height = (h - _frame_h(p)) if h else 180.0
    labels = list(p["labels"])
    series = list(p["series"])
    pos = p["legend_pos"] if (p["legend"] and len(series) > 1) else "none"
    legend_h = LEGEND_H + 4 if pos in ("top", "bottom") else 0.0
    ml, mr = 50.0, 10.0
    mt = 8.0 + (legend_h if pos == "top" else 0.0)
    mb = 22.0 + (legend_h if pos == "bottom" else 0.0)
    px, py, pw, ph = ml, mt, w_in - ml - mr, height - mt - mb
    allv = [float(v) for s in series for v in s.get("values", []) if v is not None]
    vmax = float(p["y_max"]) if p["y_max"] else _nice_max(allv)
    n = max(1, len(labels))
    markers_on = auto(p["markers"], n)

    def X(i: int) -> float:
        return px + (pw * i / (n - 1) if n > 1 else pw / 2)

    def Y(v: float) -> float:
        return py + ph - ph * v / vmax

    ops: list[dict] = []
    entries = [{"name": s.get("name", f"série {k + 1}"), "color": s.get("color") or f"series_{k + 1}", "kind": "line"}
               for k, s in enumerate(series)]
    if pos == "top":
        ops += legend_ops(entries, px, 0, pw, "top")[0]
    for k in range(5):
        t = vmax * k / 4
        ops.append({"op": "line", "x1": px, "y1": Y(t), "x2": px + pw, "y2": Y(t),
                    "color": "chart_axis" if k == 0 else "chart_grid", "weight": AXIS_W if k == 0 else GRID_W,
                    "role": "baseline" if k == 0 else "grid"})
        ops.append({"op": "text", "x": 0, "y": Y(t) - 7, "w": ml - 6, "h": 14, "text": _fmt(t), "style": "axis", "align": "END"})
    markers: list[dict] = []
    for k, s in enumerate(series):
        color = s.get("color") or f"series_{k + 1}"
        dash = "DASH" if s.get("dash") else None
        run: list[list[float]] = []
        runs: list[list[list[float]]] = []
        for i, v in enumerate(s.get("values", [])):
            if v is None:
                if run:
                    runs.append(run)
                run = []
                continue
            pt = [X(i), Y(float(v))]
            run.append(pt)
            if markers_on:
                markers.append({"op": "box", "x": pt[0] - MARKER / 2, "y": pt[1] - MARKER / 2, "w": MARKER, "h": MARKER,
                                "shape": "ELLIPSE", "fill": color, "role": "marker"})
        if run:
            runs.append(run)
        for r in runs:
            if len(r) >= 2:
                ops.append({"op": "polyline", "points": r, "color": color, "weight": LINE_W, "dash": dash, "role": "line"})
    ops.extend(markers)
    shown = thin_labels(labels, pw / max(n - 1, 1))
    for i, lab in enumerate(labels):
        if shown[i]:
            ops.append({"op": "text", "x": X(i) - 24, "y": py + ph + 3, "w": 48, "h": 12, "text": str(lab),
                        "style": "chart_label", "align": "CENTER", "role": "label"})
    if pos == "bottom":
        ops += legend_ops(entries, px, height - LEGEND_H, pw, "bottom")[0]
    return panelize(ops, height, w, p)


register(Component(
    name="chart_line", description="Courbes fines multi-séries sur grille légère : axe, libellés, petits marqueurs, série pointillée, trous (null), légende.",
    props=[
        Prop("labels", "list", "Libellés de l'axe horizontal.", required=True),
        Prop("series", "list", "Séries : {name, values (null = trou), dash?, color?}.", required=True),
        Prop("y_max", "number", "Maximum de l'échelle."),
        Prop("legend", "bool", "Légende (si plusieurs séries).", default=True),
        Prop("legend_pos", "choice", "Position de la légende.", default="bottom", choices=["top", "bottom", "none"]),
        Prop("markers", "str", "Marqueurs sur les points : 'auto' (jusqu'à 12 points), true, false.", default="auto"),
        Prop("title", "str", "Titre du graphique, en petit et centré au-dessus."),
        Prop("panel", "bool", "Fond gris clair arrondi autour du graphique (style bilan).", default=False),
    ],
    render=_chart_line,
    example={"labels": ["Jan", "Fév", "Mar", "Avr"], "series": [{"name": "2025", "values": [120, 140, 135, 160]}, {"name": "2026", "values": [130, 150, None, 190], "dash": True}]},
    tags=["graphiques"],
))


def _donut(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    import math

    from .axes import LEGEND_H, inner_width, legend_ops, panelize

    w_in = inner_width(w, p)
    height = (h - _frame_h(p)) if h else 160.0
    segs = list(p["segments"])
    total = sum(float(s.get("value", 0)) for s in segs) or 1.0
    pos = p.get("legend_pos") or "right"
    legend = p["legend"] and pos != "none"
    colored = [{"value": float(s.get("value", 0)), "color": s.get("color") or f"series_{i + 1}"} for i, s in enumerate(segs)]
    bottom_h = 0.0
    if legend and pos == "bottom":
        # legend lines wrap under the ring: estimate the rows the entries need
        per = [len(str(s.get("label", ""))) * 5.6 + 2 * INSET_X + 32 for s in segs]
        rows_n, line_w = 1, 0.0
        for width in per:
            if line_w + width > w_in and line_w:
                rows_n += 1
                line_w = 0.0
            line_w += width
        bottom_h = rows_n * LEGEND_H + 4
    d = min(height - bottom_h, w_in * 0.5 if (legend and pos == "right") else w_in)
    r = d / 2
    cx = r if (legend and pos == "right") else w_in / 2
    cy = d / 2 if pos == "bottom" else height / 2
    thickness = float(p["thickness"]) if p["thickness"] else r * 0.36
    ops: list[dict] = [{"op": "ring", "cx": cx, "cy": cy, "r": r, "thickness": thickness, "segments": colored}]
    if p["center"]:
        ops.append({"op": "text", "x": cx - r * 0.6, "y": cy - 10, "w": r * 1.2, "h": 20, "text": str(p["center"]),
                    "style": "chart_value", "size": 14, "align": "CENTER", "valign": "MIDDLE"})
    if p.get("labels"):
        a = -90.0
        rm = r - thickness / 2
        for c in colored:
            span = 360 * c["value"] / total
            pct = round(100 * c["value"] / total)
            if pct >= 6:
                t = math.radians(a + span / 2)
                lx, ly = cx + rm * math.cos(t), cy + rm * math.sin(t)
                ops.append({"op": "text", "x": lx - 20, "y": ly - 9, "w": 40, "h": 18, "text": f"{pct} %", "style": "chart_value",
                            "size": 10, "color": "on_dark" if theme.is_dark(c["color"]) else "ink", "align": "CENTER",
                            "valign": "MIDDLE", "role": "segment_label"})
            a += span
    if legend and pos == "right":
        lx = d + 16
        lw = w_in - lx
        row = LEGEND_H
        ly = cy - row * len(segs) / 2
        for s, c in zip(segs, colored):
            pct = round(100 * c["value"] / total)
            ops.append({"op": "box", "x": lx, "y": ly + 4, "w": 10, "h": 10, "fill": c["color"], "role": "swatch"})
            ops.append({"op": "text", "x": lx + 16, "y": ly, "w": lw - 16 - 44, "h": row, "text": str(s.get("label", "")),
                        "style": "legend", "valign": "MIDDLE"})
            ops.append({"op": "text", "x": lx + lw - 44, "y": ly, "w": 44, "h": row, "text": f"{pct} %",
                        "style": "chart_value", "align": "END", "valign": "MIDDLE"})
            ly += row
    elif legend and pos == "bottom":
        entries = [{"name": str(s.get("label", "")), "color": c["color"]} for s, c in zip(segs, colored)]
        ly = d + 4
        line: list[dict] = []
        line_w = 0.0
        for e, width in zip(entries, per):
            if line_w + width > w_in and line:
                ops += legend_ops(line, 0, ly, w_in, "top")[0]
                ly += LEGEND_H
                line, line_w = [], 0.0
            line.append(e)
            line_w += width
        if line:
            ops += legend_ops(line, 0, ly, w_in, "top")[0]
    return panelize(ops, height, w, p)


register(Component(
    name="donut", description="Anneau de répartition : parts en % dans la légende (à droite ou dessous) et, en option, posées sur les parts ; texte central, titre et panneau optionnels.",
    props=[
        Prop("segments", "list", "Parts : {label, value, color?} (couleurs : rôles du thème, ex. regie_google).", required=True),
        Prop("thickness", "number", "Épaisseur de l'anneau en pt (défaut : 36 % du rayon)."),
        Prop("center", "str", "Texte au centre."),
        Prop("legend", "bool", "Légende avec pourcentages.", default=True),
        Prop("legend_pos", "choice", "Légende à droite de l'anneau ou en dessous.", default="right", choices=["right", "bottom", "none"]),
        Prop("labels", "bool", "Pourcentages posés sur les parts (à partir de 6 %).", default=False),
        Prop("title", "str", "Titre du graphique, en petit et centré au-dessus."),
        Prop("panel", "bool", "Fond gris clair arrondi autour du graphique (style bilan).", default=False),
    ],
    render=_donut,
    example={"segments": [{"label": "Google", "value": 62, "color": "regie_google"}, {"label": "Meta", "value": 25, "color": "regie_meta"},
                          {"label": "Bing", "value": 13, "color": "regie_bing"}], "labels": True, "legend_pos": "bottom",
             "title": "Répartition des dépenses"},
    tags=["graphiques"],
))
