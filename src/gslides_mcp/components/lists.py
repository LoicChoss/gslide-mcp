"""Lot 4 text / structure components: agenda, numbered_list, big_numbers,
phase_cards, compare_cards, before_after, stat_pair, palette.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only. Markdown props accept
``==texte==`` for the marker highlight (role ``highlight``).
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register, shift
from .builtin import INSETS, LEADING, PAD, _text_height

_DARK = {"surface_dark", "surface_dark_2", "ink", "text", "device_frame"}


def _fg(fill: str | None) -> str:
    return "on_dark" if fill in _DARK else "ink"


def _rows(items: list, cols: int) -> list[list]:
    return [items[i:i + cols] for i in range(0, len(items), cols)]


# --- agenda -------------------------------------------------------------------------

def _agenda(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    row = float(p["row_h"])
    size = float(p["size"])
    color = "on_dark" if p["dark"] else "ink"
    text_h = size * LEADING + INSETS
    ops: list[dict] = []
    for i, it in enumerate(items):
        num, title = (it.get("num"), it.get("title", "")) if isinstance(it, dict) else (None, it)
        num = str(num) if num is not None else f"{i + 1:02d}"
        y = i * row
        ops.append({"op": "box", "x": 0, "y": y + (row - 16) / 2, "w": 28, "h": 16, "fill": "chip", "role": "chip",
                    "text": num, "style": "badge", "size": 10, "color": "on_chip", "align": "CENTER", "valign": "MIDDLE"})
        ops.append({"op": "text", "x": 38, "y": y + (row - text_h) / 2, "w": w - 38, "h": text_h, "text": str(title),
                    "style": "label", "size": size, "color": color, "valign": "MIDDLE"})
    return ops, h or row * len(items)


register(Component(
    name="agenda", description="Sommaire : chip numérotée (acide) + titre de section par ligne (dark=True sur fond sombre).",
    props=[
        Prop("items", "list", "Sections : texte, ou {num, title}.", required=True),
        Prop("dark", "bool", "Texte clair (fond sombre).", default=False),
        Prop("size", "number", "Taille des titres.", default=12),
        Prop("row_h", "number", "Hauteur d'une ligne.", default=24),
    ],
    render=_agenda,
    example={"items": ["Contexte & objectifs", "Accompagnement créatif", "Méthodologie", {"num": "A", "title": "Annexes"}]},
    tags=["texte"],
))


# --- numbered_list ----------------------------------------------------------------------

def _numbered_list(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = [it if isinstance(it, dict) else {"title": str(it)} for it in p["items"]]
    square = p["marker"] == "square"
    d = 18.0 if square else 40.0
    gap = float(p["gap"])
    start = int(p["start"])
    indexed = not square and any(it.get("icon") for it in items)  # picto in the disc, « #n » beside it; otherwise the number sits in the disc
    text_x = d + 56 if indexed else d + 12
    text_w = w - text_x - (PAD if p["card"] else 0)
    ops_bg: list[dict] = []
    ops: list[dict] = []
    y = 0.0
    centers: list[float] = []
    for i, it in enumerate(items):
        title = str(it.get("title", ""))
        sub = it.get("sub")
        title_h = _text_height(title.upper() if square else title, text_w, 11)
        sub_h = _text_height(str(sub), text_w, 11) if sub else 0
        row_h = max(d + 4, title_h + sub_h)
        cy = y + row_h / 2
        centers.append(cy)
        if p["card"]:
            ops_bg.append({"op": "box", "x": d / 2, "y": y, "w": w - d / 2, "h": row_h, "fill": "surface", "role": "card"})
        n = f"{start + i}"
        if square:
            ops.append({"op": "box", "x": 0, "y": cy - d / 2, "w": d, "h": d, "fill": "accent", "role": "marker",
                        "text": n, "style": "badge", "size": 10, "color": "on_accent", "align": "CENTER", "valign": "MIDDLE"})
        else:
            disc: dict = {"op": "box", "x": 0, "y": cy - d / 2, "w": d, "h": d, "shape": "ELLIPSE", "fill": "accent", "role": "marker"}
            if it.get("icon"):
                ops.append(disc)
                ops.append({"op": "image", "x": 10, "y": cy - 10, "w": 20, "h": 20, "asset": str(it["icon"]), "tint": "ink"})
            else:
                disc.update({"text": n, "style": "step_number", "size": 13, "color": "on_accent", "align": "CENTER", "valign": "MIDDLE"})
                ops.append(disc)
            if indexed:
                ops.append({"op": "text", "x": d + 8, "y": cy - 11, "w": 40, "h": 14 + INSETS, "text": f"#{n}",
                            "style": "card_title", "size": 11, "color": "ink", "role": "index"})
                ops.append({"op": "line", "x1": d + 48, "y1": y + 4, "x2": d + 48, "y2": y + row_h - 4, "color": "rule", "weight": 1})
        ty = cy - (title_h + sub_h) / 2
        ops.append({"op": "text", "x": text_x, "y": ty, "w": text_w, "h": title_h, "text": title.upper() if square else title,
                    "style": "card_title", "size": 11, "role": "title"})
        if sub:
            ops.append({"op": "text", "x": text_x, "y": ty + title_h - 2, "w": text_w, "h": sub_h, "markdown": str(sub),
                        "style": "body", "size": 11, "color": "muted"})
        y += row_h + gap
    connector: list[dict] = []
    if p["connector"] and len(centers) > 1:
        connector.append({"op": "line", "x1": d / 2, "y1": centers[0], "x2": d / 2, "y2": centers[-1], "color": "accent", "weight": 4,
                          "role": "connector"})
    return ops_bg + connector + ops, h or (y - gap)


register(Component(
    name="numbered_list", description="Liste verticale numérotée : disque accent (picto ou numéro) + « #n » + titre et sous-texte, ou chip carrée + titre en capitales. Cartes et connecteur optionnels.",
    props=[
        Prop("items", "list", "Éléments : {title, sub?, icon?} ou texte.", required=True),
        Prop("marker", "choice", "Style du marqueur.", default="circle", choices=["circle", "square"]),
        Prop("start", "number", "Premier numéro.", default=1),
        Prop("card", "bool", "Chaque ligne sur une carte claire.", default=False),
        Prop("connector", "bool", "Trait vertical accent reliant les marqueurs.", default=False),
        Prop("gap", "number", "Espace entre lignes.", default=10),
    ],
    render=_numbered_list,
    example={"items": [{"title": "Transformer la refonte en moteur de conversion", "sub": "CRO, UX et optimisation des parcours", "icon": "bolt"},
                       {"title": "Sécuriser et renforcer le capital SEO", "sub": "Transfert de visibilité", "icon": "search"},
                       {"title": "Créer de nouveaux carrefours d'audience", "sub": "Contenus, social, IA", "icon": "people"}],
             "card": True, "connector": True},
    tags=["texte"],
))


# --- big_numbers ------------------------------------------------------------------------

def _big_numbers(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    cols = int(p["cols"] or len(items) or 1)
    col_w = w / cols
    ops: list[dict] = []
    height = 0.0
    for i, it in enumerate(items):
        x = (i % cols) * col_w
        y0 = (i // cols) * float(p["row_gap"])
        num = str(it.get("num", i + 1))
        ops.append({"op": "text", "x": x, "y": y0, "w": col_w, "h": 60 + INSETS, "text": num, "style": "stat_value",
                    "size": 54, "color": "ink", "align": "CENTER", "role": "number"})
        y = y0 + 66
        title = str(it.get("title", ""))
        if title:
            paras = [[{"text": line, "bold": True, "highlight": p["highlight"]}] for line in title.split("\n")]
            th = len(paras) * 11 * LEADING + INSETS
            ops.append({"op": "text", "x": x + 8, "y": y, "w": col_w - 16, "h": th, "runs": paras, "style": "label",
                        "size": 11, "align": "CENTER", "role": "title"})
            y += th
        if it.get("text"):
            th = _text_height(it["text"], col_w - 16, 11)
            ops.append({"op": "text", "x": x + 8, "y": y + 4, "w": col_w - 16, "h": th, "markdown": str(it["text"]),
                        "style": "body", "size": 11, "align": "CENTER"})
            y += th + 4
        height = max(height, y)
    return ops, h or height


register(Component(
    name="big_numbers", description="Colonnes « 1 2 3 » : chiffre géant, titre surligné (marqueur), paragraphe centré.",
    props=[
        Prop("items", "list", "Colonnes : {num?, title, text?} (title accepte des sauts de ligne).", required=True),
        Prop("cols", "number", "Colonnes par rangée (défaut : toutes)."),
        Prop("row_gap", "number", "Hauteur d'une rangée quand il y en a plusieurs.", default=170),
        Prop("highlight", "color", "Couleur du surlignage des titres.", default="highlight"),
    ],
    render=_big_numbers,
    example={"items": [{"title": "3 niveaux,\njamais 4", "text": "Toute page du site est atteignable en trois clics depuis l'accueil."},
                       {"title": "Une page,\nune intention", "text": "Un carrefour oriente et ne raconte rien."},
                       {"title": "La fiscalité est une porte", "text": "La page « don et impôt » pèse près de 10 % des pages vues."}]},
    tags=["texte"],
))


# --- phase_cards ------------------------------------------------------------------------

def _phase_card(ph: dict, w: float, h: float | None, num_size: float) -> tuple[list[dict], float]:
    top = num_size + 8
    inner = w - 2 * 12
    texts: list[dict] = []
    y = top + 12
    title_h = _text_height(str(ph.get("title", "")), inner, 11)
    texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": title_h, "text": str(ph.get("title", "")),
                  "style": "card_title", "size": 11, "role": "title"})
    y += title_h
    if ph.get("text"):
        th = _text_height(ph["text"], inner, 11)
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": th, "markdown": str(ph["text"]), "style": "body", "size": 11})
        y += th
    if ph.get("icon") or ph.get("note"):
        y += 6
        nx = 12 + (34 if ph.get("icon") else 0)
        nh = _text_height(str(ph.get("note", "")), w - nx - 12, 11) if ph.get("note") else 26
        if ph.get("icon"):
            texts.append({"op": "image", "x": 12, "y": y + 2, "w": 26, "h": 26, "asset": str(ph["icon"]), "tint": "accent"})
        if ph.get("note"):
            texts.append({"op": "text", "x": nx, "y": y, "w": w - nx - 12, "h": nh, "markdown": str(ph["note"]), "style": "body", "size": 11})
        y += max(nh, 30 if ph.get("icon") else 0)
    if ph.get("deliverables"):
        y += 6
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": 14 + INSETS, "text": "LIVRABLES", "style": "card_label", "role": "deliverables"})
        y += 16
        runs = [[{"text": "→  ", "bold": True, "color": "accent"}, {"text": str(d)}] for d in ph["deliverables"]]
        lh = len(runs) * 9 * LEADING + INSETS
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": lh, "runs": runs, "style": "body", "size": 11})
        y += lh
    height = h or (y + 12)
    ops: list[dict] = [
        {"op": "text", "x": 0, "y": 0, "w": 60, "h": num_size + INSETS, "text": str(ph.get("num", "")), "style": "card_big",
         "size": num_size, "color": "accent", "role": "number"},
        {"op": "box", "x": 0, "y": top, "w": w, "h": height - top, "shape": "ROUND_RECTANGLE", "fill": "background",
         "line": {"color": "accent", "weight": 1.5}, "role": "card"},
    ]
    return ops + texts, height


def _phase_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    phases = [dict(ph) for ph in p["phases"]]
    for i, ph in enumerate(phases):
        ph.setdefault("num", i + 1)
    cols = int(p["cols"] or len(phases) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    ops: list[dict] = []
    y = 0.0
    for row in _rows(phases, cols):
        natural = [_phase_card(ph, cw, None, float(p["num_size"]))[1] for ph in row]
        row_h = h or max(natural)
        for j, ph in enumerate(row):
            sub, _ = _phase_card(ph, cw, row_h, float(p["num_size"]))
            ops.extend(shift(sub, j * (cw + gap), y))
        y += row_h + gap
    return ops, y - gap if phases else 0.0


register(Component(
    name="phase_cards", description="Cartes de phases : gros numéro accent au-dessus d'une carte à contour accent (titre, texte, picto + note, livrables →).",
    props=[
        Prop("phases", "list", "Phases : {num?, title, text?, icon?, note?, deliverables?: [..]}.", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cartes.", default=14),
        Prop("num_size", "number", "Taille du numéro.", default=30),
    ],
    render=_phase_cards,
    example={"phases": [
        {"title": "Exploration & cadrage", "text": "Nous affinons ensemble le périmètre projet.", "icon": "search",
         "note": "Nous rédigeons nos recommandations.", "deliverables": ["Liste des KPI", "Cadrage projet"]},
        {"title": "Conception & création", "text": "Dispositifs, gabarits, maquettes.", "icon": "lightbulb",
         "note": "Cette phase comprend les maquettes graphiques.", "deliverables": ["Maquettes"]},
        {"title": "Développement", "text": "Prototype mobile first, socle technique.", "icon": "bolt",
         "note": "Tests et formation à la contribution.", "deliverables": ["Site en recette", "Formation"]}]},
    tags=["cartes"],
))


# --- compare_cards ----------------------------------------------------------------------

_KIND = {
    # kind: (fill, mark, label color, title color, text color)
    "bad": ("surface", "✗  ", "coral", "ink", "text"),
    "good": ("accent", "✓  ", "ink", "ink", "ink"),
    "neutral": ("surface", "", "muted", "ink", "text"),
}


def _compare_card(c: dict, w: float, h: float | None) -> tuple[list[dict], float]:
    fill, mark, label_col, title_col, text_col = _KIND[c.get("kind", "neutral")]
    inner = w - 2 * PAD
    texts: list[dict] = []
    y = float(PAD) - 2
    if c.get("label"):
        texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": 14 + INSETS, "text": mark + str(c["label"]).upper(),
                      "style": "card_label", "color": label_col, "role": "label"})
        y += 16
    title_h = _text_height(str(c.get("title", "")), inner, 11)
    texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": title_h, "markdown": str(c.get("title", "")),
                  "style": "card_title", "size": 11, "color": title_col, "role": "title"})
    y += title_h
    if c.get("text"):
        th = (h - y - PAD) if h else _text_height(c["text"], inner, 11)
        texts.append({"op": "text", "x": PAD, "y": y + 2, "w": inner, "h": th, "markdown": str(c["text"]),
                      "style": "body", "size": 11, "color": text_col})
        y += th + 2
    height = h or (y + PAD)
    return [{"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "card"}] + texts, height


def _compare_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    cards = list(p["cards"])
    for c in cards:
        if c.get("kind", "neutral") not in _KIND:
            raise ValueError(f"compare_cards: kind must be one of {', '.join(_KIND)}; got {c.get('kind')!r}")
    cols = int(p["cols"] or len(cards) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    ops: list[dict] = []
    y = 0.0
    for row in _rows(cards, cols):
        row_h = h or max(_compare_card(c, cw, None)[1] for c in row)
        for j, c in enumerate(row):
            sub, _ = _compare_card(c, cw, row_h)
            ops.extend(shift(sub, j * (cw + gap), y))
        y += row_h + gap
    return ops, y - gap if cards else 0.0


register(Component(
    name="compare_cards", description="Idée reçue / réponse : cartes arrondies ✗ (gris, libellé corail), ✓ (menthe) ou neutres (gris), hauteurs égalisées.",
    props=[
        Prop("cards", "list", "Cartes : {kind: bad|good|neutral, label?, title, text?}.", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cartes.", default=10),
    ],
    render=_compare_cards,
    example={"cards": [
        {"kind": "bad", "label": "Idée reçue A", "title": "« Une seule page très experte suffit »", "text": "Une page dense capte la requête principale, **mais** ne couvre pas les sous-sujets."},
        {"kind": "good", "label": "La réponse en 2026", "title": "Page mère experte + cocon de pages enfants", "text": "La page mère domine la requête principale ; les pages enfants captent les sous-intentions."},
        {"kind": "bad", "label": "Idée reçue B", "title": "« Plusieurs pages = plus de positions »", "text": "Des pages légères diluent l'autorité."}]},
    tags=["cartes"],
))


# --- before_after -----------------------------------------------------------------------

def _panel(side: dict, w: float, h: float | None, good: bool) -> tuple[list[dict], float]:
    fill, ink, mark = ("accent", "ink", "✓  ") if good else ("surface", "coral", "✗  ")
    inner = w - 2 * 12
    texts: list[dict] = []
    y = 8.0
    texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": 14 + INSETS, "text": mark + str(side.get("title", "")).upper(),
                  "style": "card_label", "color": ink, "role": "title"})
    y += 20
    rules: list[dict] = []
    for it in side.get("items", []):
        th = _text_height(str(it), inner, 11)
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": th, "markdown": str(it), "style": "body", "size": 11})
        y += th
        rules.append({"op": "line", "x1": 12, "y1": y, "x2": w - 12, "y2": y, "color": "background", "weight": 1, "role": "rule"})
    if side.get("note"):
        nh = _text_height(str(side["note"]), inner, 10)
        texts.append({"op": "text", "x": 12, "y": y + 4, "w": inner, "h": nh, "text": str(side["note"]), "style": "caption",
                      "size": 10, "italic": True, "color": ink, "role": "note"})
        y += nh + 4
    height = h or (y + 8)
    box = {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "panel"}
    return [box] + rules + texts, height


def _before_after(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    pw = (w - gap) / 2
    natural = max(_panel(p["before"], pw, None, False)[1], _panel(p["after"], pw, None, True)[1])
    height = h or natural
    left, _ = _panel(p["before"], pw, height, False)
    right, _ = _panel(p["after"], pw, height, True)
    ops = left + shift(right, pw + gap, 0)
    if p["arrow"]:
        ops.append({"op": "text", "x": pw, "y": height / 2 - 16, "w": gap, "h": 32, "text": "→", "style": "label", "size": 18,
                    "bold": True, "align": "CENTER", "valign": "MIDDLE", "role": "arrow"})
    return ops, height


register(Component(
    name="before_after", description="Avant / après : panneau ✗ gris (titre corail) et panneau ✓ menthe (titre caps, lignes séparées par des filets, note en italique), flèche entre les deux.",
    props=[
        Prop("before", "dict", "{title, items: [markdown…], note?} — l'existant.", required=True),
        Prop("after", "dict", "{title, items: [markdown…], note?} — la cible.", required=True),
        Prop("arrow", "bool", "Flèche → entre les panneaux.", default=True),
        Prop("gap", "number", "Espace entre panneaux.", default=28),
    ],
    render=_before_after,
    example={"before": {"title": "URLs actuelles — structure plate", "items": ["opc.fr/==cataracte==", "opc.fr/cataracte-definition", "opc.fr/l-operation-de-la-cataracte"], "note": "Aucun signal hiérarchique"},
             "after": {"title": "Structure cible — répertoire /conseils/", "items": ["opc.fr/conseils/==cataracte/==", "opc.fr/conseils/cataracte/**definition/**", "opc.fr/conseils/cataracte/**operation/**"], "note": "Silo lisible, maillage naturel"}},
    tags=["cartes"],
))


# --- stat_pair --------------------------------------------------------------------------

def _stat_pair(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    pairs = list(p["pairs"])
    cols = int(p["cols"] or len(pairs) or 1)
    cw = w / cols
    ops: list[dict] = []
    row_h = 58.0
    for i, pr in enumerate(pairs):
        x, y = (i % cols) * cw, (i // cols) * row_h
        ops.append({"op": "text", "x": x, "y": y, "w": cw, "h": 14 + INSETS, "text": str(pr.get("label", "")).upper(),
                    "style": "card_label", "color": "muted", "role": "label"})
        runs = [[{"text": str(pr.get("before", "")), "color": "muted", "size": 20},
                 {"text": "  →  ", "color": "muted", "size": 14},
                 {"text": str(pr.get("after", "")), "bold": True, "color": "ink", "size": 20}]]
        ops.append({"op": "text", "x": x, "y": y + 18, "w": cw, "h": 28 + INSETS, "runs": runs, "style": "kpi_value", "size": 20, "role": "values"})
    rows = -(-len(pairs) // cols)
    return ops, h or rows * row_h


register(Component(
    name="stat_pair", description="Paires avant → après : libellé caps, valeur avant (grisée) → valeur après (grasse).",
    props=[
        Prop("pairs", "list", "Paires : {label, before, after}.", required=True),
        Prop("cols", "number", "Paires par rangée (défaut : toutes)."),
    ],
    render=_stat_pair,
    example={"pairs": [{"label": "Pages indexées", "before": "16 913", "after": "15 588"}, {"label": "Erreurs 404", "before": "13 207", "after": "2 323"}]},
    tags=["chiffres"],
))


# --- palette ----------------------------------------------------------------------------

def _palette(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    sw = list(p["swatches"])
    cols = int(p["cols"] or 1)
    cw = w / cols
    row_h = 30.0
    ops: list[dict] = []
    for i, s in enumerate(sw):
        s = s if isinstance(s, dict) else {"color": s}
        x, y = (i % cols) * cw, (i // cols) * row_h
        ops.append({"op": "box", "x": x, "y": y + 3, "w": 44, "h": 22, "fill": s["color"], "line": {"color": "rule", "weight": 0.75},
                    "text": str(s.get("sample") or p["sample"]), "style": "label", "size": 11, "bold": True,
                    "color": s.get("text") or "ink", "align": "CENTER", "valign": "MIDDLE", "role": "swatch"})
        runs: list[list[dict]] = []
        if s.get("name"):
            runs.append([{"text": str(s["name"]), "bold": True}])
        if s.get("ratio"):
            runs.append([{"text": str(s["ratio"]), "color": "positive"}])
        if runs:
            ops.append({"op": "text", "x": x + 50, "y": y + 1, "w": cw - 50, "h": row_h - 2, "runs": runs, "style": "caption",
                        "size": 10, "valign": "MIDDLE"})
    rows = -(-len(sw) // cols) if sw else 0
    return ops, h or rows * row_h


register(Component(
    name="palette", description="Nuancier / contrastes : pastille « Aa » (fond + couleur de texte) avec nom et ratio de contraste.",
    props=[
        Prop("swatches", "list", "Pastilles : {color, text?, name?, ratio?, sample?} ou couleur seule.", required=True),
        Prop("cols", "number", "Pastilles par rangée.", default=2),
        Prop("sample", "str", "Texte d'exemple.", default="Aa"),
    ],
    render=_palette,
    example={"swatches": [{"color": "background", "text": "ink", "name": "Navy sur blanc", "ratio": "17.04:1"},
                          {"color": "surface_dark", "text": "on_dark", "name": "Blanc sur navy", "ratio": "8.12:1"},
                          {"color": "accent", "text": "ink", "name": "Navy sur menthe", "ratio": "11.4:1"},
                          {"color": "accent_alt", "text": "ink", "name": "Navy sur acide", "ratio": "14.13:1"}]},
    tags=["données"],
))
