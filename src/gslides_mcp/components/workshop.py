"""Workshop and reporting blocks drawn from the Periscope restitution dashboards:
score_matrix, ranked_bars, chip_cloud, quadrant_matrix, next_steps, board_columns,
session_plan, attention_points, bar_list.

Grounds are light: transparent or ``surface`` panels; only headers, tags and
tiles carry a colour. Same contract as ``builtin``: ``render(props, theme, w, h)
-> (ops, height)`` at origin, theme roles and named text styles only.

Read texts take their size from the theme (``theme.size``) and never go under
the charter floor: a long label wraps and its row grows. Values and counts are
chart internals (``chart_value`` / ``chart_label``), eyebrows ``card_label``.
"""

from __future__ import annotations

import math

from ..themes import Theme
from . import Component, Prop, register, shift
from .axes import fmt_value
from .brand import THIN
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, PAD, _wrapped_lines, caps_centre
from .reporting import _chevrons, box_h, too_long

EYEBROW = {"style": "card_label", "size": 9.5, "bold": True, "small_ok": True}


def _eyebrow_op(text: str, x: float, y: float, w: float, color: str = "muted", align: str = "START", lines: int = 1) -> dict:
    """Tracked capitals on one line when they fit, else plain capitals that wrap; ``h`` holds every line."""
    up = str(text).upper()
    avail = w - 2 * INSET_X
    size = 9.5
    tracked_w = len(up) * (size * 0.62 + 2.5)  # thin spaces add ~2.5 pt each
    wrapped = 1
    if tracked_w <= avail:
        text_out = THIN.join(up)  # tracking only when it fits on one line
    else:
        text_out = up
        longest = max(len(word) for word in up.split()) if up.split() else len(up)
        if longest * size * 0.62 > avail:  # a word alone would break: shrink instead (down to 7.5 pt)
            size = max(7.5, round(avail / (longest * 0.62), 1))
        wrapped = _wrapped_lines(up, w, size * BOLD_WRAP)
    h = 12 * lines + INSETS if wrapped <= lines else wrapped * size * LEADING + INSETS
    return {"op": "text", "x": x, "y": y, "w": w, "h": h, "text": text_out, "color": color, "align": align, "role": "eyebrow",
            **{**EYEBROW, "size": size}}


def _word_w(text: str, size: float, bold: bool = False) -> float:
    """Text-box width the longest word of ``text`` needs on one line at ``size``."""
    longest = max((len(word) for word in str(text).split()), default=0)
    return longest * size * GLYPH_WRAP * (BOLD_WRAP if bold else 1.0) + 2 * INSET_X


def _num(value) -> float | None:
    """'34,71 €' → 34.71 ; None / '' / text → None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace(" ", "").replace(" ", "").replace("%", "").replace("€", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def threshold_color(value: float | None, thresholds: list[dict], default: str = "surface") -> str:
    """First threshold whose ``max`` the value is under (a threshold without ``max`` catches the rest)."""
    if value is None:
        return default
    for t in thresholds:
        if t.get("max") is None or value < float(t["max"]):
            return t.get("color") or default
    return default


DEFAULT_SCORE_THRESHOLDS = [{"max": 1.75, "color": "coral"}, {"max": 2.5, "color": "acid"}, {"max": 3.25, "color": "mint_pale"},
                            {"color": "accent"}]


# --- score_matrix ------------------------------------------------------------------------------

def _score_matrix(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    rows = list(p["rows"])
    cols = [str(c) for c in p["columns"]]
    thresholds = list(p["thresholds"] or DEFAULT_SCORE_THRESHOLDS)
    label_w = w * float(p["label_ratio"])
    lw = label_w - 8
    gap = 8.0
    tile_w = (w - label_w - (len(cols) - 1) * gap) / max(1, len(cols))
    ops: list[dict] = [_eyebrow_op(p["row_title"], 0, 0, label_w)]
    for j, c in enumerate(cols):
        ops.append(_eyebrow_op(c, label_w + j * (tile_w + gap), 0, tile_w, align="CENTER", lines=2))
    y = max(o["h"] for o in ops) + 6
    floor = theme.size("card_title")
    cs = theme.size("caption")
    # row labels: 14 pt bold on one line, down to the charter floor, then they wrap; the sub-text under them
    blocks = []
    for r in rows:
        label = str(r.get("label", ""))
        rsize = 14.0
        while rsize > floor and _wrapped_lines(label, lw, rsize * BOLD_WRAP) > 1:
            rsize = round(rsize - 0.5, 1)
        rsize = max(rsize, floor)
        lh = box_h(label, lw, rsize, bold=True)
        sh = box_h(r["sub"], lw, cs) if r.get("sub") else 0.0
        blocks.append((rsize, lh, sh, lh - 5 + sh if sh else lh))
    # one tile height for the whole matrix: the tallest label block decides, the rows stay alike
    tile_h = max([float(p["tile_h"])] + [b[3] + 4 for b in blocks])
    for r, (rsize, lh, sh, bh) in zip(rows, blocks):
        values = list(r.get("values") or [])
        counts = list(r.get("counts") or [])
        # the label's capitals on the score's line (the score box's centre, the counts under it), the block kept in the row
        score_cc = y + 4 + (tile_h - 22) / 2 + 1.2
        top = max(y, min(score_cc - caps_centre(0, rsize), y + tile_h - 2 - bh))
        ops.append({"op": "text", "x": 0, "y": top, "w": lw, "h": lh, "text": str(r.get("label", "")),
                    "style": "card_title", "size": rsize, "color": "ink", "role": "row_label"})
        if r.get("sub"):
            ops.append({"op": "text", "x": 0, "y": top + lh - 5, "w": lw, "h": sh, "text": str(r["sub"]),
                        "style": "caption", "size": cs, "role": "row_sub"})
        for j in range(len(cols)):
            v = _num(values[j]) if j < len(values) else None
            fill = threshold_color(v, thresholds)
            x = label_w + j * (tile_w + gap)
            ops.append({"op": "box", "x": x, "y": y, "w": tile_w, "h": tile_h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "tile"})
            text = "–" if v is None else f"{v:.1f}".replace(".", ",")
            ops.append({"op": "text", "x": x, "y": y + 4, "w": tile_w, "h": tile_h - 22, "text": text, "style": "kpi_value", "size": 24,
                        "color": "ink", "align": "CENTER", "valign": "MIDDLE", "role": "score"})
            if j < len(counts) and counts[j] is not None:  # a chart internal: may go under the small floor in a narrow tile
                ops.append({"op": "text", "x": x, "y": y + tile_h - 20, "w": tile_w, "h": 12 + INSETS,
                            "text": f"{counts[j]} {p['count_label']}", "style": "chart_label", "size": 9.5, "color": "ink", "small_ok": True,
                            "align": "CENTER", "role": "count"})
        y += tile_h + gap
    if p["legend"]:
        lx = 0.0
        prev = None
        for t in thresholds:
            color = t.get("color") or "surface"
            if t.get("max") is None:
                name = f"{fmt_value(prev, '')} et plus" if prev is not None else "reste"
            elif prev is None:
                name = f"moins de {fmt_value(float(t['max']), '')}"
            else:
                name = f"{fmt_value(prev, '')} à {fmt_value(float(t['max']), '')}"
            prev = t.get("max")
            tw = len(name) * 5.6 + 2 * INSET_X
            if lx > 0 and lx + 12 + tw > w:  # the legend wraps rather than running off the block
                lx = 0.0
                y += 24
            ops.append({"op": "box", "x": lx, "y": caps_centre(y, theme.size("legend")) - 5, "w": 10, "h": 10, "shape": "ROUND_RECTANGLE", "fill": color, "role": "swatch"})
            ops.append({"op": "text", "x": lx + 12, "y": y, "w": tw, "h": 22, "text": name, "style": "legend", "role": "legend"})  # the swatch on its capitals
            lx += 12 + tw + 8
        y += 24
    if h and tile_h > float(p["tile_h"]) and y > h + 1:  # the labels grew the tiles past the pinned height
        ops.append(too_long("score_matrix", "rows", max((str(r.get("sub") or r.get("label", "")) for r in rows), key=len, default="")))
    return ops, h or y


register(Component(
    name="score_matrix",
    description="Matrice de notes (familles × critères) : tuiles arrondies colorées par seuil avec la note en gros et le nombre de réponses, libellés de ligne avec sous-texte, légende des seuils.",
    props=[
        Prop("rows", "list", "Lignes : {label, sub?, values: [notes], counts?: [nb de réponses]}.", required=True),
        Prop("columns", "list", "Critères (en-têtes de colonnes).", required=True),
        Prop("thresholds", "list", "Seuils croissants : [{max, color}, …, {color}] (défaut : < 1,75 corail, < 2,5 acide, < 3,25 menthe pâle, sinon menthe)."),
        Prop("row_title", "str", "Titre de la colonne des lignes.", default="Famille de missions"),
        Prop("count_label", "str", "Suffixe du compte.", default="rép."),
        Prop("label_ratio", "number", "Part de la largeur pour les libellés.", default=0.34),
        Prop("tile_h", "number", "Hauteur minimale d'une tuile (un libellé long agrandit toutes les tuiles).", default=64),
        Prop("legend", "bool", "Légende des seuils.", default=True),
    ],
    render=_score_matrix,
    example={"columns": ["Qualité des résultats", "Respect des délais", "Clarté du pilotage", "Valeur perçue"],
             "rows": [{"label": "Sites et produits web", "sub": "Ma Générosité, Info-legs, ifi.fondationdefrance", "values": [2.5, 1.5, 1.3, 2.0], "counts": [2, 2, 3, 2]},
                      {"label": "CRM", "sub": "Newsletters et emails", "values": [3.7, 3.7, 4.0, 4.0], "counts": [3, 3, 3, 3]},
                      {"label": "Media et création", "sub": "Fil rouge, legs, IFI, fin d'année", "values": [3.3, 2.0, 2.7, 3.0], "counts": [3, 3, 3, 3]}]},
    tags=["données"],
))


# --- ranked_bars ---------------------------------------------------------------------------------

def _ranked_bars(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = [it if isinstance(it, dict) else {"label": str(it)} for it in p["items"]]
    values = [_num(it.get("value")) or 0.0 for it in items]
    vmax = float(p["max"]) if p["max"] else (max(values) or 1.0)
    top = int(p["top"])
    label_w = w * float(p["label_ratio"])
    bar_x = label_w + 12
    bar_h = float(p["bar_h"])
    ls = theme.size("label")
    vs = 16.0  # the count, a chart value set big
    counts = [fmt_value(v, "") for v in values]
    count_w = max([42.0] + [len(c) * vs * GLYPH_WRAP * BOLD_WRAP + 2 * INSET_X for c in counts])
    bar_w = w - bar_x - count_w - 6
    ch = vs * LEADING + INSETS
    ops: list[dict] = []
    y = 0.0
    if p["eyebrow"]:
        eb = _eyebrow_op(p["eyebrow"], 0, 0, w)
        ops.append(eb)
        y = eb["h"] + 6
    for i, (it, v) in enumerate(zip(items, values)):
        lead = i < top and v > 0
        label = str(it.get("label", ""))
        # 13 pt (the charter floor), wrapping rather than shrinking: the row grows
        n = _wrapped_lines(label, label_w, ls * (BOLD_WRAP if lead else 1.0))
        lh = n * ls * LEADING + INSETS
        mid = caps_centre(0, ls) + (n - 1) * ls * LEADING / 2  # the bar and the count on the middle of the label's lines
        b_top, c_top = mid - bar_h / 2, mid - caps_centre(0, vs)
        off = -min(0.0, b_top, c_top)
        row_h = max(lh, b_top + bar_h) + off  # the count's bottom inset may run into the gap
        ops.append({"op": "text", "x": 0, "y": y + off, "w": label_w, "h": lh, "text": label, "style": "label",
                    "size": ls, "bold": lead, "color": "ink", "role": "label"})
        by = y + off + b_top
        ops.append({"op": "box", "x": bar_x, "y": by, "w": bar_w, "h": bar_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "track"})
        if v > 0:
            ops.append({"op": "box", "x": bar_x, "y": by, "w": max(bar_h, bar_w * v / vmax), "h": bar_h, "shape": "ROUND_RECTANGLE",
                        "fill": "accent" if lead else "gray_2", "role": "bar"})
        ops.append({"op": "text", "x": bar_x + bar_w + 6, "y": y + off + c_top, "w": count_w, "h": ch, "text": counts[i],
                    "style": "chart_value", "size": vs, "color": "ink", "align": "END", "role": "count"})
        y += row_h + 4
    natural = max(0.0, y - 4)
    if h and natural > h + 1:
        ops.append(too_long("ranked_bars", "items", max((str(it.get("label", "")) for it in items), key=len, default="")))
    return ops, h or natural


register(Component(
    name="ranked_bars",
    description="Liste classée (votes, priorités) : libellé, piste grise avec remplissage accent pour le haut du classement et gris pour les autres, compte en gros à droite ; sur-titre optionnel (« 3 choix par personne »).",
    props=[
        Prop("items", "list", "Éléments dans l'ordre : {label, value}.", required=True),
        Prop("top", "number", "Nombre d'éléments mis en avant (accent, libellé gras).", default=3),
        Prop("max", "number", "Valeur pleine (défaut : le max)."),
        Prop("eyebrow", "str", "Sur-titre en capitales."),
        Prop("label_ratio", "number", "Part de la largeur pour les libellés.", default=0.5),
        Prop("bar_h", "number", "Hauteur des barres.", default=12),
    ],
    render=_ranked_bars,
    example={"eyebrow": "Vos priorités · 3 choix par personne",
             "items": [{"label": "Recrutement de nouveaux donateurs", "value": 3}, {"label": "Lisibilité de la Fondation et des Collectifs d'action", "value": 2},
                       {"label": "GEO : visibilité dans les moteurs de réponse IA", "value": 1}, {"label": "Legs, donations, assurance-vie", "value": 1},
                       {"label": "Passage au don régulier", "value": 0}]},
    tags=["données"],
))


# --- chip_cloud ----------------------------------------------------------------------------------

def _chip_cloud(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = [it if isinstance(it, dict) else {"text": str(it)} for it in p["items"]]
    size = max(float(p["size"]), theme.size("label"))  # read texts: never under the charter floor
    gap = float(p["gap"])
    one = size * 1.2 + 14
    ops: list[dict] = []
    x = y = 0.0
    row_h = 0.0
    for it in items:
        text = str(it.get("text", ""))
        count = it.get("count")
        runs = [{"text": text}]
        full = text
        cw = len(text) * size * 0.55 + 2 * INSET_X + 14
        if count and int(count) > 1:
            runs.append({"text": f"  ×{int(count)}", "bold": True, "color": "accent_dark"})
            full += f"  ×{int(count)}"
            cw += (2 + len(str(count))) * size * 0.55 + 6
        cw = min(cw, w)
        if x + cw > w and x > 0:
            x = 0.0
            y += row_h + gap
            row_h = 0.0
        # a chip as wide as the block wraps its text and grows (it is alone on its row)
        ch = max(one, box_h(full, cw - 14, size) + 6) if cw >= w else one
        ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": ch, "shape": "ROUND_RECTANGLE", "fill": p["fill"], "runs": [runs],
                    "style": "label", "size": size, "color": "ink", "align": "CENTER", "valign": "MIDDLE", "role": "chip"})
        row_h = max(row_h, ch)
        x += cw + gap
    natural = y + row_h
    if h and natural > h + 1:
        ops.append(too_long("chip_cloud", "items", max((str(it.get("text", "")) for it in items), key=len, default="")))
    return ops, h or natural


register(Component(
    name="chip_cloud",
    description="Nappe de chips arrondies (chantiers cités, tags) avec compteur « ×2 » en gras quand un élément revient plusieurs fois.",
    props=[
        Prop("items", "list", "Chips : texte, ou {text, count}.", required=True),
        Prop("fill", "color", "Fond des chips.", default="surface"),
        Prop("size", "number", "Taille du texte (13 pt au moins, le plancher de la charte).", default=13),
        Prop("gap", "number", "Espace entre chips.", default=8),
    ],
    render=_chip_cloud,
    example={"items": [{"text": "CFA, dont CFA 2027", "count": 2}, "Refonte des causes : Ma Générosité, puis IFI", "IA, co-pilotée avec l'agence",
                       "Fil rouge", "Campagnes legs", "Campagnes IFI", "FDD"]},
    tags=["texte"],
))


# --- quadrant_matrix -----------------------------------------------------------------------------

def _quadrant_matrix(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    quads = [q if isinstance(q, dict) else {"title": str(q)} for q in p["quadrants"]]
    while len(quads) < 4:
        quads.append({})
    axis_w = 0.0
    axis_h = 20.0 if p["x_label"] else 0.0
    gap = 10.0
    height = h or float(p["height"])
    ops: list[dict] = []
    heads: list[dict] = []
    if p["eyebrow"]:  # clear of the axis name set at the right end of the same line
        heads.append(_eyebrow_op(p["eyebrow"], 0, 0, max(w / 2, w - 128) if p["y_label"] else w))
    if p["y_label"]:
        heads.append(_eyebrow_op(f"↑ {p['y_label']}", w - 120, 0, 120, color="muted", align="END"))
    top = max(o["h"] for o in heads) + 6 if heads else 0.0
    grid_h = height - axis_h - top
    qw = (w - axis_w - gap) / 2
    qh = (grid_h - gap) / 2
    ts = max(14.0, theme.size("body") + 2)  # the quadrant title stays visibly above its items
    tw = qw - 20
    if p["eyebrow"]:
        ops.append(heads[0])
    q_min = 8 + max(box_h(str(q.get("title", "")), tw, ts, bold=True) for q in quads[:4]) + 4
    warned = qh < q_min
    if warned:  # a height too small for the titles: the quadrants keep them, the caller gives more room
        ops.append(too_long("quadrant_matrix", "title", max((str(q.get("title", "")) for q in quads[:4]), key=len)))
        qh = q_min
    for i, q in enumerate(quads[:4]):
        x = axis_w + (i % 2) * (qw + gap)
        y = top + (i // 2) * (qh + gap)
        hl = bool(q.get("highlight"))
        # one geometry per row of quadrants: the taller title of the row places both subs and both item lists
        row = quads[(i // 2) * 2:(i // 2) * 2 + 2]
        th = max(box_h(str(r.get("title", "")), tw, ts, bold=True) for r in row)
        sub_y = y + 8 + th - 2
        items_y = sub_y + max([_eyebrow_op(r["sub"], 0, 0, tw)["h"] for r in row if r.get("sub")] or [20.0]) + 2
        ops.append({"op": "box", "x": x, "y": y, "w": qw, "h": qh, "shape": "ROUND_RECTANGLE", "fill": "accent" if hl else "surface",
                    "role": "quadrant"})
        ops.append({"op": "text", "x": x + 10, "y": y + 8, "w": tw, "h": box_h(str(q.get("title", "")), tw, ts, bold=True),
                    "text": str(q.get("title", "")), "style": "card_title", "size": ts, "color": "ink", "role": "title"})
        bottom, field, text = y + 8 + th, "title", str(q.get("title", ""))
        if q.get("sub"):
            sub = _eyebrow_op(q["sub"], x + 10, sub_y, tw, color="ink" if hl else "muted")
            ops.append(sub)
            bottom, field, text = sub_y + sub["h"], "sub", str(q["sub"])
        if q.get("items"):
            chev, ch = _chevrons(q["items"], tw, theme.size("list"), spacing=4, theme=theme)
            chev.update({"x": x + 10, "y": items_y, "color": "ink", "role": "items"})
            if hl:  # the mint chevron would vanish on the mint quadrant
                chev["runs"] = [[{**r[0], "color": "ink"}, *r[1:]] for r in chev["runs"]]
            ops.append(chev)
            bottom, field, text = items_y + ch, "items", " · ".join(map(str, q["items"]))
        if bottom > y + qh - 4 and not warned:  # the matrix keeps its height: the text stays at the floor, the caller shortens it
            ops.append(too_long("quadrant_matrix", field, text))
            warned = True
    if p["y_label"]:
        ops.append(heads[-1])
    if p["x_label"]:
        xl = _eyebrow_op(f"{p['x_label']} →", 0, 0, w, color="muted", align="END")
        xl["y"] = height - xl["h"]  # under the grid, inside the block
        ops.append(xl)
    return ops, height


register(Component(
    name="quadrant_matrix",
    description="Matrice 2 × 2 (impact × urgence) : quatre cadrans titrés avec leur sous-titre en capitales, un cadran mis en avant en accent, items optionnels, axes nommés ; vide, elle se remplit en séance.",
    props=[
        Prop("quadrants", "list", "Quatre cadrans, haut-gauche, haut-droite, bas-gauche, bas-droite : {title, sub?, items?, highlight?}.", required=True),
        Prop("x_label", "str", "Axe horizontal.", default="Urgence"),
        Prop("y_label", "str", "Axe vertical.", default="Impact"),
        Prop("eyebrow", "str", "Sur-titre."),
        Prop("height", "number", "Hauteur totale (défaut : 300).", default=300),
    ],
    render=_quadrant_matrix,
    example={"eyebrow": "Matrice impact × urgence · à remplir en séance",
             "quadrants": [{"title": "À planifier", "sub": "Fort impact · peu urgent"}, {"title": "À lancer en priorité", "sub": "Fort impact · urgent", "highlight": True, "items": ["Refonte des causes", "CFA 2027"]},
                           {"title": "À surveiller", "sub": "Impact faible · peu urgent"}, {"title": "Gains rapides", "sub": "Impact faible · urgent"}]},
    tags=["schémas"],
))


# --- next_steps ----------------------------------------------------------------------------------

def _next_steps(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    steps = list(p["steps"])
    n = max(1, len(steps))
    gap = 10.0
    cw = (w - (n - 1) * gap) / n
    ts = max(theme.size("card_title"), theme.size("body") + 2)  # the step title stays visibly above its text
    bs = theme.size("body")
    # one geometry for the row: the tallest title places every text
    title_h = max([box_h(str(st.get("title", "")), cw, ts, bold=True) for st in steps] or [ts * LEADING + INSETS])
    body_y = 10 + title_h
    ops: list[dict] = []
    heights = []
    for i, st in enumerate(steps):
        x = i * (cw + gap)
        current = bool(st.get("current"))
        ops.append({"op": "box", "x": x, "y": 0, "w": cw, "h": 3, "fill": "accent" if current else "gray_2", "role": "rule"})
        ops.append({"op": "text", "x": x, "y": 10, "w": cw, "h": title_h, "text": str(st.get("title", "")), "style": "card_title", "size": ts,
                    "color": "ink", "role": "title"})
        th = box_h(st.get("text", ""), cw, bs)
        if st.get("text"):
            ops.append({"op": "text", "x": x, "y": body_y, "w": cw, "h": th, "markdown": str(st["text"]), "style": "body", "role": "body"})
        heights.append(body_y + (th if st.get("text") else 0))
    natural = max(heights, default=0.0)
    if h and natural > h + 1:
        ops.append(too_long("next_steps", "steps", max((str(st.get("text", "")) for st in steps), key=len, default="")))
    return ops, h or natural


register(Component(
    name="next_steps",
    description="Prochaines étapes en colonnes : filet supérieur (accent pour l'étape en cours, gris sinon), titre gras, texte.",
    props=[Prop("steps", "list", "Étapes : {title, text?, current?}.", required=True)],
    render=_next_steps,
    example={"steps": [{"title": "Aujourd'hui", "text": "Atelier : vos retours et vos priorités.", "current": True},
                       {"title": "D'ici fin septembre", "text": "Entretiens individuels, côté FDF et côté Periscope, data et benchmark."},
                       {"title": "1er ou 2 octobre", "text": "Restitution : conclusions, propositions et plan d'action."}]},
    tags=["schémas"],
))


# --- board_columns -------------------------------------------------------------------------------

def _board_columns(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    cols = list(p["columns"])
    n = max(1, len(cols))
    gap = 12.0
    cw = (w - (n - 1) * gap) / n
    pad = 12.0
    bs = theme.size("body")
    # the number's glyphs 9 pt into the card, the item's 9 pt after them, 7 pt clear of the card's right edge
    most = max([len(c.get("items") or []) for c in cols] or [1])
    digits_w = len(str(max(1, most))) * bs * 0.6
    num_x = pad + 9 - INSET_X
    tx = pad + 9 + digits_w + 9 - INSET_X
    tw = (cw - pad - 7 + INSET_X) - tx
    ops: list[dict] = []
    natural = []
    per_col: list[list[dict]] = []
    warned = False
    # one geometry for the row: the tallest column title places every first card
    heads = [_eyebrow_op(c.get("title", ""), pad, pad, cw - 2 * pad, lines=2) for c in cols]
    y0 = pad + max([e["h"] for e in heads] or [32.0]) + 6
    for c, head in zip(cols, heads):
        items = list(c.get("items") or [])
        col_ops: list[dict] = [head]
        y = y0
        if not items:
            eh = box_h(p["empty_text"], cw - 2 * pad, bs)
            col_ops.append({"op": "text", "x": pad, "y": y, "w": cw - 2 * pad, "h": eh, "text": str(p["empty_text"]), "style": "body",
                            "italic": True, "color": "muted", "role": "empty"})
            y += eh
        for k, it in enumerate(items, start=1):
            text = str(it)
            th = box_h(text, tw, bs)
            card_h = th + 12
            col_ops.append({"op": "box", "x": pad, "y": y, "w": cw - 2 * pad, "h": card_h, "shape": "ROUND_RECTANGLE", "fill": "background",
                            "line": {"color": "rule", "weight": 1}, "role": "card"})
            # the number at the item's size and top: both on the same baseline
            col_ops.append({"op": "text", "x": num_x, "y": y + 6, "w": digits_w + 2 * INSET_X + 2, "h": bs * LEADING + INSETS, "text": str(k),
                            "style": "card_label", "size": bs, "bold": True, "color": "accent_dark", "role": "num"})
            col_ops.append({"op": "text", "x": tx, "y": y + 6, "w": tw, "h": th, "markdown": text, "style": "body", "role": "item"})
            if not warned and _word_w(text, bs) > tw + 0.5:  # a word wider than the column breaks: the caller shortens or widens
                ops.append(too_long("board_columns", "items", max(text.split(), key=len)))
                warned = True
            y += card_h + 8
        natural.append(y + pad - 8 if items else y + pad)
        per_col.append(col_ops)
    height = h or max(natural, default=0.0)
    if h and max(natural, default=0.0) > h + 1:
        ops.append(too_long("board_columns", "items", max((str(it) for c in cols for it in c.get("items") or []), key=len, default="")))
    for i, col_ops in enumerate(per_col):
        x = i * (cw + gap)
        ops.append({"op": "box", "x": x, "y": 0, "w": cw, "h": height, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "column"})
        ops.extend(shift(col_ops, x, 0))
    return ops, height


register(Component(
    name="board_columns",
    description="Tableau d'atelier en colonnes (forces à garder, irritants, chantiers) : sur-titre par colonne, cartes numérotées, état vide en italique.",
    props=[
        Prop("columns", "list", "Colonnes : {title, items?: [texte markdown]}.", required=True),
        Prop("empty_text", "str", "Texte d'une colonne vide.", default="Rien de noté pour l'instant."),
    ],
    render=_board_columns,
    example={"columns": [{"title": "Les forces à garder"},
                         {"title": "Les irritants à traiter", "items": ["Trop d'interlocuteurs, sans filtre : besoin d'une cheffe de projet relais qui cadre et tient les plannings.",
                                                                        "La gouvernance des documents : difficile de retrouver ce qui a été validé.", "L'usage de Slack est à revoir, pas à abandonner."]},
                         {"title": "Les chantiers à lancer en priorité"}]},
    tags=["cartes"],
))


# --- session_plan --------------------------------------------------------------------------------

def _session_plan(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    sections = list(p["sections"] or [])
    slots = list(p["slots"] or [])
    gap = 12.0
    ops: list[dict] = []
    y = 0.0
    if sections:
        n = len(sections)
        cw = (w - (n - 1) * gap) / n
        bs = theme.size("body")
        # one geometry for the row: the tallest section title places every text
        title_h = max(box_h(str(s.get("title", "")), cw, 16, bold=True) for s in sections)
        text_y = 10 + title_h
        hs = []
        for i, s in enumerate(sections):
            x = i * (cw + gap)
            ops.append({"op": "box", "x": x, "y": 0, "w": cw, "h": 3, "fill": "accent", "role": "rule"})
            ops.append({"op": "text", "x": x, "y": 10, "w": cw, "h": title_h, "text": str(s.get("title", "")), "style": "card_title", "size": 16,
                        "color": "ink", "role": "section"})
            th = box_h(s.get("text", ""), cw, bs)
            if s.get("text"):
                ops.append({"op": "text", "x": x, "y": text_y, "w": cw, "h": th, "markdown": str(s["text"]), "style": "body", "role": "section_text"})
            hs.append(text_y + (th if s.get("text") else 0))
        y = max(hs) + 12
    if slots:
        ts = 11.0                   # the time: a small caption-like code (card_label, floor 10)
        ls = theme.size("label")    # the slot's name: a read text, bold, at the charter floor
        times = [str(s.get("time", "")) for s in slots]
        labels = [str(s.get("label", "")) for s in slots]
        weights = [float(s.get("weight") or 1) for s in slots]
        sgap = 4.0
        avail = w - (len(slots) - 1) * sgap
        # every slot holds its time on one line and the longest word of its name: those minimums come
        # first, min_slot_w next as far as the band allows, the weights share what is left
        need = [max(len(t) * ts * GLYPH_WRAP * BOLD_WRAP + 2 * INSET_X, _word_w(lb, ls, bold=True)) for t, lb in zip(times, labels)]
        extra = [max(0.0, float(p["min_slot_w"]) - nd) for nd in need]
        room = avail - sum(need)
        if room < 0:  # the names cannot hold at the floor in this width: the caller shortens them
            ops.append(too_long("session_plan", "slots", labels[max(range(len(slots)), key=lambda k: need[k])]))
            mins = [nd * avail / sum(need) for nd in need]
        else:
            f = min(1.0, room / sum(extra)) if sum(extra) else 0.0
            mins = [nd + f * ex for nd, ex in zip(need, extra)]
        widths = _spread(weights, mins, avail)
        time_h = ts * LEADING + INSETS
        label_h = max(_wrapped_lines(lb, sw, ls * BOLD_WRAP) for lb, sw in zip(labels, widths)) * ls * LEADING + INSETS
        slot_h = max(float(p["slot_h"]), 8 + time_h - 2 + label_h + 2)  # a name that wraps makes the whole band taller
        x = 0.0
        for s, sw, time, label in zip(slots, widths, times, labels):
            current = bool(s.get("current"))
            ops.append({"op": "box", "x": x, "y": y, "w": sw, "h": slot_h, "fill": "surface", "role": "slot"})
            ops.append({"op": "box", "x": x, "y": y, "w": sw, "h": 3, "fill": "accent" if current else "gray_2", "role": "slot_rule"})
            ops.append({"op": "text", "x": x, "y": y + 8, "w": sw, "h": time_h, "text": time, "style": "card_label",
                        "size": ts, "bold": True, "color": "accent_dark", "role": "time"})
            ops.append({"op": "text", "x": x, "y": y + slot_h - 2 - label_h, "w": sw, "h": label_h, "text": label, "style": "label",
                        "size": ls, "bold": True, "color": "ink", "role": "slot_label"})
            x += sw + sgap
        y += slot_h
    if h and y > h + 1:
        ops.append(too_long("session_plan", "sections", max((str(s.get("text", "")) for s in sections), key=len, default="")))
    return ops, h or y


def _spread(weights: list[float], mins: list[float], avail: float) -> list[float]:
    """Widths proportional to ``weights`` over ``avail``, none under its minimum (the others give the room back)."""
    n = len(weights)
    fixed: set[int] = set()
    while True:
        free = avail - sum(mins[i] for i in fixed)
        wsum = sum(weights[i] for i in range(n) if i not in fixed) or 1.0
        under = [i for i in range(n) if i not in fixed and free * weights[i] / wsum < mins[i]]
        if not under:
            return [mins[i] if i in fixed else free * weights[i] / wsum for i in range(n)]
        fixed.update(under)
        if len(fixed) == n:
            return list(mins)


register(Component(
    name="session_plan",
    description="Déroulé d'atelier : sections titrées avec filet accent et texte, puis bandeau horaire proportionnel (créneau, libellé, créneau en cours en accent).",
    props=[
        Prop("sections", "list", "Sections : {title, text?}."),
        Prop("slots", "list", "Créneaux : {time, label, weight? (durée relative), current?}."),
        Prop("slot_h", "number", "Hauteur minimale du bandeau horaire (un libellé sur deux lignes l'agrandit).", default=56),
        Prop("min_slot_w", "number", "Largeur minimale d'un créneau (les longs créneaux cèdent la place) ; chaque créneau tient au moins son horaire et le plus long mot de son libellé.", default=72),
    ],
    render=_session_plan,
    example={"sections": [{"title": "La collaboration", "text": "Ce qui fonctionne, ce qui ne fonctionne pas, pas assez ou plus."},
                          {"title": "Mission par mission", "text": "Un mini audit co-construit : quatre familles, quatre critères."},
                          {"title": "Les enjeux 2027", "text": "Les chantiers digitaux qui comptent, classés ensemble."}],
             "slots": [{"time": "0-5'", "label": "Ouverture", "weight": 5, "current": True}, {"time": "5-20'", "label": "Collaboration", "weight": 15},
                       {"time": "20-40'", "label": "Missions", "weight": 20}, {"time": "40-55'", "label": "Enjeux 2027", "weight": 15}, {"time": "55-60'", "label": "Clôture", "weight": 5}]},
    tags=["schémas"],
))


# --- attention_points ----------------------------------------------------------------------------

_LEVELS = {
    "critical": {"fill": "coral", "text": "on_dark", "outline": True},
    "warning": {"fill": "accent_alt", "text": "ink", "outline": False},
    "good": {"fill": "accent", "text": "ink", "outline": False},
}


def _attention_points(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ops: list[dict] = []
    y = 0.0
    if p["title"]:
        ts = 15.0
        title = str(p["title"])
        runs = [{"text": title, "bold": True, "size": ts}]
        if p["note"]:  # the note in its own small style (caption, 10 pt floor) after the 15 pt title
            runs.append({"text": "   " + str(p["note"]), "style": "caption", "color": "accent_dark"})
        th = box_h(title + ("   " + str(p["note"]) if p["note"] else ""), w - 16, ts, bold=True)
        ops.append({"op": "box", "x": 0, "y": caps_centre(0, ts) - 5, "w": 10, "h": 10, "fill": "accent", "role": "square"})  # on the capitals
        ops.append({"op": "text", "x": 16, "y": 0, "w": w - 16, "h": th, "runs": [runs], "style": "card_title", "role": "title"})
        y = th + 4
    tag_w = float(p["tag_w"])
    pad = 10.0
    bs = theme.size("body")
    for it in p["items"]:
        level = str(it.get("level") or "warning")
        lv = _LEVELS.get(level, _LEVELS["warning"])
        text = str(it.get("text", ""))
        tx = pad + tag_w + 12
        th = box_h(text, w - tx - pad, bs)
        card_h = max(th + 2 * pad, 44)
        text_y = y + pad - 4
        line = {"color": "coral", "weight": 1.5} if lv["outline"] else {"color": "rule", "weight": 1}
        ops.append({"op": "box", "x": 0, "y": y, "w": w, "h": card_h, "fill": "background", "line": line, "role": level})
        ops.append({"op": "box", "x": pad, "y": caps_centre(text_y, bs) - 11, "w": tag_w, "h": 22, "shape": "ROUND_RECTANGLE", "fill": lv["fill"],
                    "text": str(it.get("tag", level)).upper(), "style": "badge", "size": 9.5, "small_ok": True, "color": lv["text"],
                    "align": "CENTER", "valign": "MIDDLE", "role": "tag"})  # the pill on the first line of the text
        ops.append({"op": "text", "x": tx, "y": text_y, "w": w - tx - pad, "h": th, "markdown": text, "style": "body",
                    "highlight": "highlight_alt", "role": "text"})
        y += card_h + 8
    natural = max(0.0, y - 8)
    if h and natural > h + 1:
        ops.append(too_long("attention_points", "items", max((str(it.get("text", "")) for it in p["items"]), key=len, default="")))
    return ops, h or natural


register(Component(
    name="attention_points",
    description="Points d'attention : cartes avec pilule de niveau à gauche (critique corail avec contour, vigilance acide, favorable menthe) et texte riche (gras, ==chiffres surlignés==) ; titre avec carré accent et note.",
    props=[
        Prop("items", "list", "Points : {level: critical | warning | good, tag, text (markdown)}.", required=True),
        Prop("title", "str", "Titre du bloc."),
        Prop("note", "str", "Note à côté du titre (« seuils calculés automatiquement »)."),
        Prop("tag_w", "number", "Largeur des pilules.", default=110),
    ],
    render=_attention_points,
    example={"title": "Points d'attention", "note": "seuils calculés automatiquement, non rédigés",
             "items": [{"level": "critical", "tag": "Tracking / mobile", "text": "Mobile : **439 clics** et **181,74 €** pour **1 conversion**, soit 0,23 %. L'ordinateur est à 3,77 % : ==vérifier le tag mobile==."},
                       {"level": "warning", "tag": "Budget", "text": "Sous-consommation de **705,72 €** sur 1 400 € alloués (50 % consommés). Le report alimente les mois suivants."},
                       {"level": "good", "tag": "Qualité", "text": "**3** signaux de contact réels sur **20** conversions, soit 15 %. CPA sur signal réel : ==231,43 €=="}]},
    tags=["texte"],
))


# --- bar_list ------------------------------------------------------------------------------------

def _stripes(x: float, y: float, w: float, h: float, step: float = 8.0, color: str = "background") -> list[dict]:
    """Diagonal hatching inside a rectangle: 45° segments clipped to the box."""
    ops: list[dict] = []
    d = x - h  # start far enough left that the first stripe crosses the box
    while d < x + w:
        x1, y1 = d, y + h
        x2, y2 = d + h, y
        if x1 < x:
            y1 -= (x - x1)
            x1 = x
        if x2 > x + w:
            y2 += (x2 - (x + w))
            x2 = x + w
        if x2 > x1:
            ops.append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "weight": 2.5, "role": "stripe"})
        d += step
    return ops


def _bar_list(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    values = [_num(it.get("value")) or 0.0 for it in items]
    vmax = float(p["max"]) if p["max"] else (max(values) or 1.0)
    states = dict(p["states"] or {})
    ls = theme.size("label")    # the bar's name: a read text, bold, at the charter floor
    cs = theme.size("caption")  # sub-texts
    vs = 11.0                   # values: chart internals (chart_value / chart_label)
    inbar = bool(p["value_in_bar"])
    texts = [str(it.get("value_text") or fmt_value(v, p["unit"])) for it, v in zip(items, values)]
    labels = [str(it.get("label", "")) for it in items]
    ops: list[dict] = []
    # a long name (a URL) widens the label column up to 45 % before it breaks, a value its column up to 30 %
    word = max(labels, key=lambda t: _word_w(t, ls, bold=True), default="")
    label_w = max(w * float(p["label_ratio"]), min(_word_w(word, ls, bold=True), w * 0.45))
    if _word_w(word, ls, bold=True) > label_w + 0.5:
        ops.append(too_long("bar_list", "label", max(word.split(), key=len)))
    right = [str(it.get("sub_right") or "") for it in items] if inbar else texts
    right_need = max([len(t) * vs * GLYPH_WRAP * BOLD_WRAP + 2 * INSET_X for t in right if t] or [0.0])
    right_w = max(w * float(p["value_ratio"]), min(right_need, w * 0.3))
    bar_x = label_w + 12
    bar_w = w - bar_x - right_w - 12
    bar_h = float(p["bar_h"])
    y = 0.0
    if p["title"]:
        ts = max(theme.size("card_title"), ls + 2)  # the title stays visibly above the bold names
        th = box_h(p["title"], w, ts, bold=True)
        ops.append({"op": "text", "x": 0, "y": 0, "w": w, "h": th, "text": str(p["title"]), "style": "card_title", "size": ts,
                    "color": "ink", "role": "title"})
        y = th + 6
    for it, v, label, value_text in zip(items, values, labels, texts):
        color = it.get("color") or states.get(str(it.get("state") or ""), {}).get("color") if isinstance(states.get(str(it.get("state") or "")), dict) \
            else it.get("color") or states.get(str(it.get("state") or ""), "accent")
        # left: the bold name, its sub-text under it; the bar on the middle of that block's lines
        n_l = _wrapped_lines(label, label_w, ls * BOLD_WRAP)
        lh = n_l * ls * LEADING + INSETS
        ops.append({"op": "text", "x": 0, "y": y, "w": label_w, "h": lh, "text": label, "style": "label", "size": ls,
                    "bold": True, "color": "ink", "role": "label"})
        first_cc = y + caps_centre(0, ls)
        last_cc = first_cc + (n_l - 1) * ls * LEADING
        bottom = y + lh
        sub_y = y + lh - 5
        if it.get("sub"):
            n_s = _wrapped_lines(str(it["sub"]), label_w, cs)
            sh = n_s * cs * LEADING + INSETS
            ops.append({"op": "text", "x": 0, "y": sub_y, "w": label_w, "h": sh, "text": str(it["sub"]), "style": "caption", "size": cs,
                        "role": "sub"})
            last_cc = sub_y + caps_centre(0, cs) + (n_s - 1) * cs * LEADING
            bottom = sub_y + sh
        by = (first_cc + last_cc) / 2 - bar_h / 2
        ops.append({"op": "box", "x": bar_x, "y": by, "w": bar_w, "h": bar_h, "fill": "surface", "role": "track"})
        fw = max(4.0, bar_w * v / vmax) if v > 0 else 0.0
        if fw:
            ops.append({"op": "box", "x": bar_x, "y": by, "w": fw, "h": bar_h, "fill": color, "role": "bar"})
            if it.get("pattern") == "stripes":
                ops.extend(_stripes(bar_x, by, fw, bar_h))
        if inbar:
            ops.append({"op": "text", "x": bar_x, "y": by - 2, "w": bar_w - 4, "h": bar_h + 4, "text": value_text,
                        "style": "chart_value", "align": "END", "valign": "MIDDLE", "role": "value"})
        # right: the value on the name's first line, its sub-text under it
        vx = bar_x + bar_w + 12
        vy = first_cc - caps_centre(0, vs)
        right_text = value_text if not inbar else str(it.get("sub_right") or "")
        if right_text:  # an empty text box is refused by the Slides API
            vh = box_h(right_text, right_w, vs, bold=not inbar)
            ops.append({"op": "text", "x": vx, "y": vy, "w": right_w, "h": vh, "text": right_text,
                        "style": "chart_value" if not inbar else "chart_label", "size": vs, "bold": not inbar,
                        "color": "ink" if not inbar else "muted", "align": "END", "role": "value" if not inbar else "sub_right"})
            bottom = max(bottom, vy + vh)
            if it.get("sub_right") and not inbar:
                sr_y = max(vy + vh - 5, sub_y if it.get("sub") else 0.0)
                srh = box_h(str(it["sub_right"]), right_w, cs)
                ops.append({"op": "text", "x": vx, "y": sr_y, "w": right_w, "h": srh, "text": str(it["sub_right"]), "style": "caption",
                            "size": cs, "align": "END", "role": "sub_right"})
                bottom = max(bottom, sr_y + srh)
        y = max(bottom, by + bar_h + 4) + 6
    if states or p["note"]:
        lx = 0.0
        for name, spec in states.items():
            color = spec.get("color") if isinstance(spec, dict) else spec
            tw = len(name) * 5.6 + 2 * INSET_X
            if lx > 0 and lx + 12 + tw > w:  # the legend wraps rather than running off the block
                lx = 0.0
                y += 24
            ops.append({"op": "box", "x": lx, "y": caps_centre(y, theme.size("legend")) - 5, "w": 10, "h": 10, "fill": color, "role": "swatch"})
            ops.append({"op": "text", "x": lx + 12, "y": y, "w": tw, "h": 22, "text": str(name), "style": "legend", "role": "legend"})  # the swatch on its capitals
            lx += 12 + tw + 10
        if p["note"]:
            note = str(p["note"])
            nx = lx + 8 if lx > 0 else 0.0
            if nx > 0 and nx + len(note) * cs * GLYPH_WRAP + 2 * INSET_X > w:  # no room left on the legend's line: under it
                nx = 0.0
                y += 24
            nh = max(22.0, box_h(note, w - nx, cs))
            ops.append({"op": "text", "x": nx, "y": y, "w": w - nx, "h": nh, "text": note, "style": "caption", "size": cs,
                        "role": "note"})  # on the legend's line
            y += nh - 22
        y += 22 + 6  # the legend line's bottom, then the gap the rows leave
    natural = max(0.0, y - 6)
    if h and natural > h + 1:
        ops.append(too_long("bar_list", "items", max(labels, key=len, default="")))
    return ops, h or natural


register(Component(
    name="bar_list",
    description="Barres horizontales commentées : libellé gras + sous-texte à gauche, valeur + sous-texte à droite (ou valeur dans la barre), couleur par état, hachures pour un signal faible, légende des états et note d'échelle.",
    props=[
        Prop("items", "list", "Barres : {label, sub?, value, value_text?, sub_right?, state?, color?, pattern?: stripes}.", required=True),
        Prop("states", "dict", "États et leurs couleurs : {\"Page ayant généré un contact\": \"accent\", \"Aucun contact\": \"gray_2\"}."),
        Prop("max", "number", "Valeur pleine (défaut : le max)."),
        Prop("unit", "str", "Unité des valeurs formatées automatiquement.", default=""),
        Prop("title", "str", "Titre du bloc."),
        Prop("note", "str", "Note d'échelle après la légende."),
        Prop("value_in_bar", "bool", "Valeur alignée à droite dans la piste, sous-texte à droite.", default=False),
        Prop("label_ratio", "number", "Part de la largeur pour les libellés (élargie jusqu'à 45 % pour un mot long, une URL).", default=0.28),
        Prop("value_ratio", "number", "Part de la largeur pour les valeurs (élargie jusqu'à 30 % pour tenir la valeur sur une ligne).", default=0.2),
        Prop("bar_h", "number", "Hauteur des barres.", default=18),
    ],
    render=_bar_list,
    example={"items": [{"label": "transmettre.amnesty.fr", "sub": "LP mise en ligne le 07/09", "value": 999.59, "value_text": "999,59 € · 1 385 clics", "sub_right": "9 contacts · CPL 111,07 €", "state": "Page ayant généré au moins un contact"},
                       {"label": "questionnaire-legs.amnesty.fr", "sub": "LP dédiée aux campagnes Ads", "value": 511.88, "value_text": "511,88 € · 767 clics", "sub_right": "1 contact · CPL 511,88 €", "state": "Page ayant généré au moins un contact"},
                       {"label": "amnesty.fr/legs", "sub": "Page Legs du site, référencée en SEO", "value": 28.15, "value_text": "28,15 € · 82 clics", "sub_right": "aucun contact", "state": "Aucun contact sur la période"}],
             "states": {"Page ayant généré au moins un contact": "accent", "Aucun contact sur la période": "gray_2"},
             "max": 1539.62, "note": "Échelle : part des 1 539,62 € investis sur Google pendant le temps fort"},
    tags=["graphiques"],
))
