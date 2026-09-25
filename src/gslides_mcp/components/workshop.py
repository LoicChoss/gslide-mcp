"""Workshop and reporting blocks drawn from the Periscope restitution dashboards:
score_matrix, ranked_bars, chip_cloud, quadrant_matrix, next_steps, board_columns,
session_plan, attention_points, bar_list.

Grounds are light: transparent or ``surface`` panels; only headers, tags and
tiles carry a colour. Same contract as ``builtin``: ``render(props, theme, w, h)
-> (ops, height)`` at origin, theme roles and named text styles only.
"""

from __future__ import annotations

import math

from ..themes import Theme
from . import Component, Prop, get, register, shift, validate
from .axes import fmt_value
from .brand import THIN
from .builtin import INSET_X, INSETS, LEADING, PAD, _text_height

EYEBROW = {"style": "card_label", "size": 9.5, "bold": True, "small_ok": True}


def _eyebrow_op(text: str, x: float, y: float, w: float, color: str = "muted", align: str = "START") -> dict:
    return {"op": "text", "x": x, "y": y, "w": w, "h": 12 + INSETS, "text": THIN.join(str(text).upper()), "color": color, "align": align,
            "role": "eyebrow", **EYEBROW}


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
    gap = 8.0
    tile_w = (w - label_w - (len(cols) - 1) * gap) / max(1, len(cols))
    tile_h = float(p["tile_h"])
    ops: list[dict] = [_eyebrow_op(p["row_title"], 0, 0, label_w)]
    for j, c in enumerate(cols):
        ops.append(_eyebrow_op(c, label_w + j * (tile_w + gap), 0, tile_w, align="CENTER"))
    y = 26.0
    for r in rows:
        values = list(r.get("values") or [])
        counts = list(r.get("counts") or [])
        ops.append({"op": "text", "x": 0, "y": y + tile_h / 2 - 22, "w": label_w - 8, "h": 18 + INSETS, "text": str(r.get("label", "")),
                    "style": "card_title", "size": 14, "color": "ink", "role": "row_label"})
        if r.get("sub"):
            ops.append({"op": "text", "x": 0, "y": y + tile_h / 2 - 1, "w": label_w - 8, "h": 14 + INSETS, "text": str(r["sub"]),
                        "style": "caption", "size": 10, "role": "row_sub"})
        for j in range(len(cols)):
            v = _num(values[j]) if j < len(values) else None
            fill = threshold_color(v, thresholds)
            fill = "#BFF5E6" if fill == "mint_pale" else fill
            x = label_w + j * (tile_w + gap)
            ops.append({"op": "box", "x": x, "y": y, "w": tile_w, "h": tile_h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "tile"})
            text = "–" if v is None else fmt_value(v, "")
            ops.append({"op": "text", "x": x, "y": y + 4, "w": tile_w, "h": tile_h - 22, "text": text, "style": "kpi_value", "size": 24,
                        "color": "ink", "align": "CENTER", "valign": "MIDDLE", "role": "score"})
            if j < len(counts) and counts[j] is not None:
                ops.append({"op": "text", "x": x, "y": y + tile_h - 20, "w": tile_w, "h": 12 + INSETS,
                            "text": f"{counts[j]} {p['count_label']}", "style": "caption", "size": 9.5, "color": "ink", "small_ok": True,
                            "align": "CENTER", "role": "count"})
        y += tile_h + gap
    if p["legend"]:
        lx = 0.0
        prev = None
        for t in thresholds:
            color = "#BFF5E6" if t.get("color") == "mint_pale" else t.get("color") or "surface"
            if t.get("max") is None:
                name = f"{fmt_value(prev, '')} et plus" if prev is not None else "reste"
            elif prev is None:
                name = f"moins de {fmt_value(float(t['max']), '')}"
            else:
                name = f"{fmt_value(prev, '')} à {fmt_value(float(t['max']), '')}"
            prev = t.get("max")
            ops.append({"op": "box", "x": lx, "y": y + 6, "w": 10, "h": 10, "shape": "ROUND_RECTANGLE", "fill": color, "role": "swatch"})
            tw = len(name) * 5.6 + 2 * INSET_X
            ops.append({"op": "text", "x": lx + 12, "y": y, "w": tw, "h": 22, "text": name, "style": "legend", "valign": "MIDDLE"})
            lx += 12 + tw + 8
        y += 24
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
        Prop("tile_h", "number", "Hauteur d'une tuile.", default=64),
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
    bar_w = w - bar_x - 48
    bar_h = float(p["bar_h"])
    ops: list[dict] = []
    y = 0.0
    if p["eyebrow"]:
        ops.append(_eyebrow_op(p["eyebrow"], 0, 0, w))
        y = 26.0
    for i, (it, v) in enumerate(zip(items, values)):
        lead = i < top and v > 0
        lh = _text_height(it.get("label", ""), label_w, 12)
        row_h = max(lh, bar_h + 12)
        ops.append({"op": "text", "x": 0, "y": y + (row_h - lh) / 2, "w": label_w, "h": lh, "text": str(it.get("label", "")), "style": "label",
                    "size": 12, "bold": lead, "color": "ink", "role": "label"})
        by = y + (row_h - bar_h) / 2
        ops.append({"op": "box", "x": bar_x, "y": by, "w": bar_w, "h": bar_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "track"})
        if v > 0:
            ops.append({"op": "box", "x": bar_x, "y": by, "w": max(bar_h, bar_w * v / vmax), "h": bar_h, "shape": "ROUND_RECTANGLE",
                        "fill": "accent" if lead else "gray_2", "role": "bar"})
        ops.append({"op": "text", "x": bar_x + bar_w + 6, "y": y + (row_h - 26) / 2, "w": 42, "h": 26, "text": fmt_value(v, ""),
                    "style": "kpi_value", "size": 16, "color": "ink", "align": "END", "valign": "MIDDLE", "role": "count"})
        y += row_h + 4
    return ops, h or (y - 4)


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
    size = float(p["size"])
    gap = float(p["gap"])
    ch = size * 1.2 + 14
    ops: list[dict] = []
    x = y = 0.0
    for it in items:
        text = str(it.get("text", ""))
        count = it.get("count")
        runs = [{"text": text}]
        cw = len(text) * size * 0.55 + 2 * INSET_X + 14
        if count and int(count) > 1:
            runs.append({"text": f"  ×{int(count)}", "bold": True, "color": "accent_dark"})
            cw += (2 + len(str(count))) * size * 0.55 + 6
        cw = min(cw, w)
        if x + cw > w and x > 0:
            x = 0.0
            y += ch + gap
        ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": ch, "shape": "ROUND_RECTANGLE", "fill": p["fill"], "runs": [runs],
                    "style": "label", "size": size, "color": "ink", "align": "CENTER", "valign": "MIDDLE", "role": "chip"})
        x += cw + gap
    return ops, h or (y + ch)


register(Component(
    name="chip_cloud",
    description="Nappe de chips arrondies (chantiers cités, tags) avec compteur « ×2 » en gras quand un élément revient plusieurs fois.",
    props=[
        Prop("items", "list", "Chips : texte, ou {text, count}.", required=True),
        Prop("fill", "color", "Fond des chips.", default="surface"),
        Prop("size", "number", "Taille du texte.", default=11),
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
    axis_w = 22.0 if p["y_label"] else 0.0
    axis_h = 20.0 if p["x_label"] else 0.0
    gap = 10.0
    height = h or float(p["height"])
    grid_h = height - axis_h - (26 if p["eyebrow"] else 0)
    top = 26.0 if p["eyebrow"] else 0.0
    qw = (w - axis_w - gap) / 2
    qh = (grid_h - gap) / 2
    ops: list[dict] = []
    if p["eyebrow"]:
        ops.append(_eyebrow_op(p["eyebrow"], 0, 0, w))
    for i, q in enumerate(quads[:4]):
        x = axis_w + (i % 2) * (qw + gap)
        y = top + (i // 2) * (qh + gap)
        hl = bool(q.get("highlight"))
        ops.append({"op": "box", "x": x, "y": y, "w": qw, "h": qh, "shape": "ROUND_RECTANGLE", "fill": "accent" if hl else "surface",
                    "role": "quadrant"})
        ops.append({"op": "text", "x": x + 10, "y": y + 8, "w": qw - 20, "h": 18 + INSETS, "text": str(q.get("title", "")), "style": "card_title",
                    "size": 14, "color": "ink", "role": "title"})
        if q.get("sub"):
            ops.append(_eyebrow_op(q["sub"], x + 10, y + 32, qw - 20, color="ink" if hl else "muted"))
        if q.get("items"):
            spec = get("chevrons")
            sub, _ = spec.render(validate(spec, {"items": [str(i) for i in q["items"]], "size": 11, "spacing": 4}), theme, qw - 20, None)
            sub[0].update({"x": x + 10, "y": y + 54, "h": min(sub[0]["h"], qh - 60), "color": "ink"})
            ops.append(sub[0])
    if p["y_label"]:
        ops.append(_eyebrow_op(f"{p['y_label']} ↑", 0, top + qh - 8, axis_w + 60, color="muted"))
    if p["x_label"]:
        ops.append(_eyebrow_op(f"{p['x_label']} →", axis_w, top + grid_h + 2, w - axis_w, color="muted", align="CENTER"))
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
    ops: list[dict] = []
    heights = []
    for i, st in enumerate(steps):
        x = i * (cw + gap)
        current = bool(st.get("current"))
        ops.append({"op": "box", "x": x, "y": 0, "w": cw, "h": 3, "fill": "accent" if current else "gray_2", "role": "rule"})
        ops.append({"op": "text", "x": x, "y": 10, "w": cw, "h": 16 + INSETS, "text": str(st.get("title", "")), "style": "card_title", "size": 13,
                    "color": "ink", "role": "title"})
        th = _text_height(st.get("text", ""), cw, 11)
        if st.get("text"):
            ops.append({"op": "text", "x": x, "y": 34, "w": cw, "h": th, "markdown": str(st["text"]), "style": "body", "role": "body"})
        heights.append(34 + (th if st.get("text") else 0))
    return ops, h or max(heights, default=0.0)


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
    ops: list[dict] = []
    natural = []
    per_col: list[list[dict]] = []
    for c in cols:
        items = list(c.get("items") or [])
        col_ops: list[dict] = [_eyebrow_op(c.get("title", ""), pad, pad, cw - 2 * pad)]
        y = pad + 26
        if not items:
            col_ops.append({"op": "text", "x": pad, "y": y, "w": cw - 2 * pad, "h": 14 + INSETS, "text": str(p["empty_text"]), "style": "body",
                            "italic": True, "color": "muted", "role": "empty"})
            y += 14 + INSETS
        for k, it in enumerate(items, start=1):
            text = str(it)
            th = _text_height(text, cw - 2 * pad - 24, 11)
            card_h = th + 12
            col_ops.append({"op": "box", "x": pad, "y": y, "w": cw - 2 * pad, "h": card_h, "shape": "ROUND_RECTANGLE", "fill": "background",
                            "line": {"color": "rule", "weight": 1}, "role": "card"})
            col_ops.append({"op": "text", "x": pad + 4, "y": y + 6, "w": 22, "h": 14 + INSETS, "text": str(k), "style": "card_label", "size": 11,
                            "bold": True, "color": "accent_dark", "role": "num"})
            col_ops.append({"op": "text", "x": pad + 24, "y": y + 6, "w": cw - 2 * pad - 28, "h": th, "markdown": text, "style": "body", "role": "item"})
            y += card_h + 8
        natural.append(y + pad - 8 if items else y + pad)
        per_col.append(col_ops)
    height = h or max(natural, default=0.0)
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
        hs = []
        for i, s in enumerate(sections):
            x = i * (cw + gap)
            ops.append({"op": "box", "x": x, "y": 0, "w": cw, "h": 3, "fill": "accent", "role": "rule"})
            ops.append({"op": "text", "x": x, "y": 10, "w": cw, "h": 20 + INSETS, "text": str(s.get("title", "")), "style": "card_title", "size": 16,
                        "color": "ink", "role": "section"})
            th = _text_height(s.get("text", ""), cw, 11)
            if s.get("text"):
                ops.append({"op": "text", "x": x, "y": 38, "w": cw, "h": th, "markdown": str(s["text"]), "style": "body", "role": "section_text"})
            hs.append(38 + (th if s.get("text") else 0))
        y = max(hs) + 12
    if slots:
        weights = [float(s.get("weight") or 1) for s in slots]
        total = sum(weights) or 1.0
        sgap = 4.0
        avail = w - (len(slots) - 1) * sgap
        x = 0.0
        slot_h = float(p["slot_h"])
        for s, wt in zip(slots, weights):
            sw = avail * wt / total
            current = bool(s.get("current"))
            ops.append({"op": "box", "x": x, "y": y, "w": sw, "h": slot_h, "fill": "surface", "role": "slot"})
            ops.append({"op": "box", "x": x, "y": y, "w": sw, "h": 3, "fill": "accent" if current else "gray_2", "role": "slot_rule"})
            ops.append({"op": "text", "x": x + 4, "y": y + 10, "w": sw - 8, "h": 14 + INSETS, "text": str(s.get("time", "")), "style": "card_label",
                        "size": 11, "bold": True, "color": "accent_dark", "role": "time"})
            ops.append({"op": "text", "x": x + 4, "y": y + slot_h - 24, "w": sw - 8, "h": 14 + INSETS, "text": str(s.get("label", "")), "style": "label",
                        "size": 11, "bold": True, "color": "ink", "role": "slot_label"})
            x += sw + sgap
        y += slot_h
    return ops, h or y


register(Component(
    name="session_plan",
    description="Déroulé d'atelier : sections titrées avec filet accent et texte, puis bandeau horaire proportionnel (créneau, libellé, créneau en cours en accent).",
    props=[
        Prop("sections", "list", "Sections : {title, text?}."),
        Prop("slots", "list", "Créneaux : {time, label, weight? (durée relative), current?}."),
        Prop("slot_h", "number", "Hauteur du bandeau horaire.", default=56),
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
        ops.append({"op": "box", "x": 0, "y": 6, "w": 10, "h": 10, "fill": "accent", "role": "square"})
        runs = [{"text": str(p["title"]), "bold": True, "size": 15}]
        if p["note"]:
            runs.append({"text": "   " + str(p["note"]), "size": 10.5, "color": "accent_dark"})
        ops.append({"op": "text", "x": 16, "y": -2, "w": w - 16, "h": 22 + INSETS, "runs": [runs], "style": "card_title", "role": "title"})
        y = 34.0
    tag_w = float(p["tag_w"])
    pad = 10.0
    for it in p["items"]:
        level = str(it.get("level") or "warning")
        lv = _LEVELS.get(level, _LEVELS["warning"])
        text = str(it.get("text", ""))
        tx = pad + tag_w + 12
        th = _text_height(text, w - tx - pad, 11)
        card_h = max(th + 2 * pad, 44)
        line = {"color": "coral", "weight": 1.5} if lv["outline"] else {"color": "rule", "weight": 1}
        ops.append({"op": "box", "x": 0, "y": y, "w": w, "h": card_h, "fill": "background", "line": line, "role": level})
        ops.append({"op": "box", "x": pad, "y": y + pad, "w": tag_w, "h": 22, "shape": "ROUND_RECTANGLE", "fill": lv["fill"],
                    "text": str(it.get("tag", level)).upper(), "style": "badge", "size": 9.5, "small_ok": True, "color": lv["text"],
                    "align": "CENTER", "valign": "MIDDLE", "role": "tag"})
        ops.append({"op": "text", "x": tx, "y": y + pad - 4, "w": w - tx - pad, "h": th, "markdown": text, "style": "body",
                    "highlight": "highlight_alt", "role": "text"})
        y += card_h + 8
    return ops, h or max(0.0, y - 8)


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
    label_w = w * float(p["label_ratio"])
    right_w = w * float(p["value_ratio"])
    bar_x = label_w + 12
    bar_w = w - bar_x - right_w - 12
    bar_h = float(p["bar_h"])
    ops: list[dict] = []
    y = 0.0
    if p["title"]:
        ops.append({"op": "text", "x": 0, "y": 0, "w": w, "h": 16 + INSETS, "text": str(p["title"]), "style": "card_title", "size": 13,
                    "color": "ink", "role": "title"})
        y = 30.0
    for it, v in zip(items, values):
        color = it.get("color") or states.get(str(it.get("state") or ""), {}).get("color") if isinstance(states.get(str(it.get("state") or "")), dict) \
            else it.get("color") or states.get(str(it.get("state") or ""), "accent")
        row_h = max(bar_h + 8, 34.0 if it.get("sub") or it.get("sub_right") else bar_h + 8)
        ops.append({"op": "text", "x": 0, "y": y - 2, "w": label_w, "h": 14 + INSETS, "text": str(it.get("label", "")), "style": "label", "size": 11,
                    "bold": True, "color": "ink", "role": "label"})
        if it.get("sub"):
            ops.append({"op": "text", "x": 0, "y": y + 14, "w": label_w, "h": 12 + INSETS, "text": str(it["sub"]), "style": "caption", "size": 10,
                        "role": "sub"})
        by = y + (row_h - bar_h) / 2 - 2
        ops.append({"op": "box", "x": bar_x, "y": by, "w": bar_w, "h": bar_h, "fill": "surface", "role": "track"})
        fw = max(4.0, bar_w * v / vmax) if v > 0 else 0.0
        if fw:
            ops.append({"op": "box", "x": bar_x, "y": by, "w": fw, "h": bar_h, "fill": color, "role": "bar"})
            if it.get("pattern") == "stripes":
                ops.extend(_stripes(bar_x, by, fw, bar_h))
        if p["value_in_bar"]:
            ops.append({"op": "text", "x": bar_x, "y": by - 2, "w": bar_w - 4, "h": bar_h + 4, "text": str(it.get("value_text") or fmt_value(v, p["unit"])),
                        "style": "chart_value", "align": "END", "valign": "MIDDLE", "role": "value"})
        vx = bar_x + bar_w + 12
        ops.append({"op": "text", "x": vx, "y": y - 2, "w": right_w, "h": 14 + INSETS,
                    "text": str(it.get("value_text") or fmt_value(v, p["unit"])) if not p["value_in_bar"] else str(it.get("sub_right") or ""),
                    "style": "label", "size": 11, "bold": not p["value_in_bar"], "color": "ink" if not p["value_in_bar"] else "muted",
                    "align": "END", "role": "value" if not p["value_in_bar"] else "sub_right"})
        if it.get("sub_right") and not p["value_in_bar"]:
            ops.append({"op": "text", "x": vx, "y": y + 14, "w": right_w, "h": 12 + INSETS, "text": str(it["sub_right"]), "style": "caption",
                        "size": 10, "align": "END", "role": "sub_right"})
        y += row_h + 6
    if states or p["note"]:
        lx = 0.0
        for name, spec in states.items():
            color = spec.get("color") if isinstance(spec, dict) else spec
            ops.append({"op": "box", "x": lx, "y": y + 6, "w": 10, "h": 10, "fill": color, "role": "swatch"})
            tw = len(name) * 5.6 + 2 * INSET_X
            ops.append({"op": "text", "x": lx + 12, "y": y, "w": tw, "h": 22, "text": str(name), "style": "legend", "valign": "MIDDLE"})
            lx += 12 + tw + 10
        if p["note"]:
            ops.append({"op": "text", "x": lx + 8, "y": y, "w": w - lx - 8, "h": 22, "text": str(p["note"]), "style": "caption", "size": 10,
                        "valign": "MIDDLE", "role": "note"})
        y += 24
    return ops, h or max(0.0, y - 6)


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
        Prop("label_ratio", "number", "Part de la largeur pour les libellés.", default=0.28),
        Prop("value_ratio", "number", "Part de la largeur pour les valeurs.", default=0.2),
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
