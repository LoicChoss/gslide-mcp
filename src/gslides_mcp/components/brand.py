"""Brand components from the Periscope design system (v1.0, 2026): buttons that
follow their ground, content cards on three grounds, plain hashtags, the
section header with its yellow highlight, the client ticker, tracked
eyebrows and the voice do / don't pairs.

Design-system rules carried here: every button is a pill; on white it is
filled dark or outlined dark, on dark outlined white or cyan, on cyan or
yellow filled dark; hashtags stay plain text (uppercase, no chip, no fill,
only lifted in accent on a dark ground); no gradients, no shadows.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register, shift
from .builtin import INSET_X, INSETS, LEADING, PAD, _text_height

GROUNDS = ("white", "dark", "cyan", "yellow")
THIN = " "  # thin space: the tracking of the eyebrows (Slides has no letter spacing)


def _ground(ground: str) -> dict:
    """Fill, text colours and the button rule for a ground."""
    if ground not in GROUNDS:
        raise ValueError(f"ground must be one of {', '.join(GROUNDS)}; got {ground!r}")
    return {
        "white": {"fill": "background", "line": {"color": "rule", "weight": 1}, "text": "text", "muted": "muted", "eyebrow": "ink",
                  "tags": "ink", "btn": "filled", "btn_color": "ink"},
        "dark": {"fill": "surface_dark", "line": None, "text": "on_dark", "muted": "on_dark", "eyebrow": "accent",
                 "tags": "accent", "btn": "outline", "btn_color": "on_dark"},
        "cyan": {"fill": "accent", "line": None, "text": "ink", "muted": "ink", "eyebrow": "ink",
                 "tags": "ink", "btn": "filled", "btn_color": "ink"},
        "yellow": {"fill": "accent_alt", "line": None, "text": "ink", "muted": "ink", "eyebrow": "ink",
                   "tags": "ink", "btn": "filled", "btn_color": "ink"},
    }[ground]


def _tracked(text: str) -> str:
    return THIN.join(str(text).upper())


# --- button / button_row ---------------------------------------------------------------------

def _button_op(text: str, ground: str, variant: str | None, size: float, x: float = 0.0, y: float = 0.0,
               color: str | None = None) -> tuple[dict, float, float]:
    """One pill button op following the ground rule. Returns (op, width, height)."""
    g = _ground(ground)
    variant = variant if variant in ("filled", "outline") else g["btn"]
    color = color or g["btn_color"]
    bw = len(str(text)) * size * 0.56 + 2 * INSET_X + 22
    bh = size * 1.2 + 14
    op: dict = {"op": "box", "x": x, "y": y, "w": bw, "h": bh, "shape": "ROUND_RECTANGLE", "text": str(text), "style": "pill",
                "size": size, "bold": False, "align": "CENTER", "valign": "MIDDLE", "role": "button"}
    if variant == "outline":
        op.update({"fill": None, "line": {"color": color, "weight": 1.25}, "color": color})
    else:
        op.update({"fill": color, "color": "on_dark" if color in ("ink", "surface_dark", "text") else "ink"})
    return op, bw, bh


def _button(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    op, bw, bh = _button_op(p["text"], p["ground"], p["variant"], float(p["size"]), color=p["color"])
    op["w"] = min(w, bw)
    return [op], h or bh


register(Component(
    name="button",
    description="Bouton pilule (radius 999) qui suit son fond : sur blanc plein dark ou contour dark, sur dark contour blanc, sur cyan ou jaune plein dark.",
    props=[
        Prop("text", "str", "Libellé.", required=True),
        Prop("ground", "choice", "Fond sur lequel le bouton est posé.", default="white", choices=list(GROUNDS)),
        Prop("variant", "choice", "Plein ou contour (défaut : la règle du fond).", choices=["filled", "outline"]),
        Prop("color", "color", "Couleur du bouton (défaut : la règle du fond, ex. accent pour un contour cyan sur dark)."),
        Prop("size", "number", "Taille du texte.", default=11),
    ],
    render=_button, example={"text": "Voir le show reel", "ground": "white"}, tags=["texte"],
))


def _button_row(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    ops: list[dict] = []
    x = 0.0
    bh = 0.0
    for it in p["items"]:
        spec = it if isinstance(it, dict) else {"text": str(it)}
        op, bw, bh = _button_op(spec.get("text", ""), spec.get("ground") or p["ground"], spec.get("variant") or p["variant"],
                                float(p["size"]), x=x, color=spec.get("color"))
        ops.append(op)
        x += bw + gap
    if p["align"] == "CENTER" and ops:
        ops = shift(ops, (w - (x - gap)) / 2, 0)
    return ops, h or bh


register(Component(
    name="button_row",
    description="Rangée de boutons pilule (CTA principal + secondaire) sur un même fond.",
    props=[
        Prop("items", "list", "Boutons : texte, ou {text, variant?, ground?, color?}.", required=True),
        Prop("ground", "choice", "Fond commun.", default="white", choices=list(GROUNDS)),
        Prop("variant", "choice", "Style commun (défaut : la règle du fond, le second bouton en contour).", choices=["filled", "outline"]),
        Prop("gap", "number", "Espace entre boutons.", default=10),
        Prop("align", "choice", "Alignement de la rangée.", default="START", choices=["START", "CENTER"]),
        Prop("size", "number", "Taille du texte.", default=11),
    ],
    render=_button_row,
    example={"items": [{"text": "Contact"}, {"text": "En savoir plus", "variant": "outline"}], "ground": "white"},
    tags=["texte"],
))


# --- hashtags ----------------------------------------------------------------------------------

def _hashtags(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    size = float(p["size"])
    color = p["color"] or ("accent" if p["dark"] else "ink")
    runs = []
    for i, tag in enumerate(p["items"]):
        t = str(tag).strip()
        if not t.startswith("#"):
            t = "#" + t
        if i:
            runs.append({"text": "    "})
        runs.append({"text": t.upper(), "bold": False, "color": color})
    text = "    ".join(r["text"] for r in runs if r["text"].strip())
    height = h or _text_height(text, w, size * 1.05)
    return [{"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": [runs], "style": "label", "size": size, "align": p["align"],
             "role": "hashtags"}], height


register(Component(
    name="hashtags",
    description="Hashtags inline en capitales, texte nu (ni chip ni fond) : encre sur clair, accent sur fond sombre.",
    props=[
        Prop("items", "list", "Tags (le # est ajouté s'il manque).", required=True),
        Prop("dark", "bool", "Sur fond sombre (tags en accent).", default=False),
        Prop("color", "color", "Couleur forcée."),
        Prop("size", "number", "Taille du texte.", default=11),
        Prop("align", "choice", "Alignement.", default="START", choices=["START", "CENTER", "END"]),
    ],
    render=_hashtags, example={"items": ["IA", "DATA", "ÉCO CONCEPTION", "ACCESSIBILITÉ", "UX", "SOCIAL"]}, tags=["texte"],
))


# --- eyebrow -----------------------------------------------------------------------------------

def _eyebrow(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    size = float(p["size"])
    text = _tracked(p["text"]) if p["tracking"] else str(p["text"]).upper()
    color = p["color"] or ("accent" if p["dark"] else "ink")
    height = h or (size * LEADING + INSETS)
    return [{"op": "text", "x": 0, "y": 0, "w": w, "h": height, "text": text, "style": "card_label", "size": size, "bold": True,
             "color": color, "align": p["align"], "role": "eyebrow"}], height


register(Component(
    name="eyebrow",
    description="Sur-titre en capitales espacées (« DIGITALE DEPUIS 1999 ») : le libellé tracké du design system, posé au-dessus d'un titre ou en légende.",
    props=[
        Prop("text", "str", "Texte.", required=True),
        Prop("tracking", "bool", "Espacer les lettres (espaces fines).", default=True),
        Prop("dark", "bool", "Sur fond sombre (accent).", default=False),
        Prop("color", "color", "Couleur forcée."),
        Prop("size", "number", "Taille.", default=10),
        Prop("align", "choice", "Alignement.", default="START", choices=["START", "CENTER", "END"]),
    ],
    render=_eyebrow, example={"text": "Digitale depuis 1999"}, tags=["texte"],
))


# --- content_card / content_cards -----------------------------------------------------------

def _content_card(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    g = _ground(p["ground"])
    pad = float(PAD) + 2
    inner = w - 2 * pad
    y = pad
    texts: list[dict] = []
    if p["eyebrow"]:
        texts.append({"op": "text", "x": pad, "y": y, "w": inner, "h": 12 + INSETS, "text": _tracked(p["eyebrow"]), "style": "card_label",
                      "size": 9.5, "bold": True, "color": g["eyebrow"], "small_ok": True, "role": "eyebrow"})
        y += 18
    if p["title"]:
        th = _text_height(p["title"], inner, 15 * 1.05)
        texts.append({"op": "text", "x": pad, "y": y, "w": inner, "h": th, "markdown": str(p["title"]), "style": "card_title", "size": 15,
                      "color": g["text"], "highlight": "highlight_alt", "role": "title"})
        y += th + 2
    if p["text"]:
        bh = _text_height(p["text"], inner, 11)
        texts.append({"op": "text", "x": pad, "y": y, "w": inner, "h": bh, "markdown": str(p["text"]), "style": "card_body", "color": g["text"],
                      "role": "body"})
        y += bh + 4
    if p["tags"]:
        tags = "    ".join(("#" + str(t).lstrip("#")).upper() for t in p["tags"])
        texts.append({"op": "text", "x": pad, "y": y, "w": inner, "h": 12 + INSETS, "text": tags, "style": "caption", "size": 10,
                      "color": g["tags"], "role": "tags"})
        y += 22
    if p["cta"]:
        y += 4
        op, bw, bh = _button_op(p["cta"], p["ground"], p["cta_variant"], 11, x=pad, y=y)
        texts.append(op)
        y += bh
    height = h or (y + pad)
    if h and p["cta"]:  # equalised rows: the CTA sits on the bottom edge
        texts[-1]["y"] = h - pad - texts[-1]["h"]
    frame = {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": g["fill"], "line": g["line"], "role": "card"}
    return [frame] + texts, height


_CARD_PROPS = [
    Prop("ground", "choice", "Fond de la carte : blanc (contour fin), dark, cyan, jaune.", default="white", choices=list(GROUNDS)),
    Prop("eyebrow", "str", "Sur-titre en capitales espacées (Réalisation, Engagement, Show reel)."),
    Prop("title", "markdown", "Titre (==surligné== possible).", required=True),
    Prop("text", "markdown", "Texte."),
    Prop("tags", "list", "Hashtags inline en pied de carte."),
    Prop("cta", "str", "Libellé du bouton pilule, style selon le fond."),
    Prop("cta_variant", "choice", "Plein ou contour (défaut : la règle du fond).", choices=["filled", "outline"]),
]


register(Component(
    name="content_card",
    description="Carte de contenu du design system sur un des trois fonds (blanc, cyan, dark) + jaune : eyebrow tracké, titre, texte, hashtags inline, bouton pilule qui suit le fond.",
    props=_CARD_PROPS,
    render=_content_card,
    example={"ground": "cyan", "eyebrow": "Engagement", "title": "60 periscopers pour concevoir des expériences durables.",
             "text": "Stratégie, data, IA, design, tech. Une équipe, un objectif.", "cta": "L'équipe"},
    tags=["cartes"],
))


def _content_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    from . import get, validate

    spec = get("content_card")
    cards = [validate(spec, c) for c in p["cards"]]
    cols = int(p["cols"] or len(cards) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    ops: list[dict] = []
    y = 0.0
    rows = [cards[i:i + cols] for i in range(0, len(cards), cols)]
    for row in rows:
        natural = [_content_card(c, theme, cw, None)[1] for c in row]
        rh = h or max(natural)
        for j, c in enumerate(row):
            sub, _ = _content_card(c, theme, cw, rh)
            ops.extend(shift(sub, j * (cw + gap), y))
        y += rh + gap
    return ops, (y - gap) if rows else 0.0


register(Component(
    name="content_cards",
    description="Rangée de cartes de contenu aux hauteurs égalisées, chacune sur son fond (blanc / cyan / dark) : réalisation, engagement, show reel.",
    props=[
        Prop("cards", "list", "Props de chaque carte (voir content_card).", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cartes.", default=16),
    ],
    render=_content_cards,
    example={"cards": [
        {"ground": "white", "eyebrow": "Réalisation", "title": "Mirova — refonte éco-conçue",
         "text": "Un site carbone-light, accessible AA, qui double le temps passé sur les articles.", "tags": ["UX", "ÉCO"]},
        {"ground": "cyan", "eyebrow": "Engagement", "title": "60 periscopers pour concevoir des expériences durables.",
         "text": "Stratégie, data, IA, design, tech. Une équipe, un objectif.", "cta": "L'équipe"},
        {"ground": "dark", "eyebrow": "Show reel", "title": "Nous sommes l'agence engagée, des marques engagées.",
         "text": "2 minutes pour comprendre comment Periscope travaille avec ses clients.", "cta": "▶  Lire la vidéo"}]},
    tags=["cartes"],
))


# --- section_header ----------------------------------------------------------------------------

def _section_header(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    dark = p["dark"]
    color = "on_dark" if dark else "ink"
    size = float(p["size"])
    ops: list[dict] = []
    y = 0.0
    if p["eyebrow"]:
        ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": 12 + INSETS, "text": _tracked(p["eyebrow"]), "style": "card_label", "size": 10,
                    "bold": True, "color": "accent" if dark else "ink", "align": p["align"], "role": "eyebrow"})
        y += 22
    th = _text_height(p["title"], w, size)  # bold Barlow titles run narrower than the estimate
    ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": th, "markdown": str(p["title"]), "style": "title", "size": size, "color": color,
                "highlight": p["highlight"], "align": p["align"], "role": "title"})
    y += th + 4
    if p["text"]:
        bh = _text_height(p["text"], w, 12)
        ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": bh, "markdown": str(p["text"]), "style": "body", "size": 12, "color": color,
                    "align": p["align"], "role": "body"})
        y += bh + 6
    if p["tags"]:
        sub, sh = _hashtags({"items": p["tags"], "dark": dark, "color": None, "size": 11, "align": p["align"]}, theme, w, None)
        ops.extend(shift(sub, 0, y))
        y += sh
    return ops, h or y


register(Component(
    name="section_header",
    description="En-tête de section signature : eyebrow tracké, titre avec ==surlignage jaune== du mot clé, paragraphe, hashtags inline.",
    props=[
        Prop("title", "markdown", "Titre, avec ==…== sur le passage à surligner.", required=True),
        Prop("eyebrow", "str", "Sur-titre en capitales espacées."),
        Prop("text", "markdown", "Paragraphe sous le titre."),
        Prop("tags", "list", "Hashtags inline."),
        Prop("highlight", "color", "Couleur du surlignage.", default="highlight_alt"),
        Prop("size", "number", "Taille du titre.", default=22),
        Prop("dark", "bool", "Sur fond sombre.", default=False),
        Prop("align", "choice", "Alignement.", default="START", choices=["START", "CENTER"]),
    ],
    render=_section_header,
    example={"eyebrow": "Équipe", "title": "60 periscopers pour concevoir des expériences ==éco-conçues==.",
             "text": "De la stratégie à l'identité de marque, en passant par la création de sites web et la stratégie marketing.",
             "tags": ["IA", "DATA", "ÉCO CONCEPTION", "ACCESSIBILITÉ", "UX", "SOCIAL"]},
    tags=["texte"],
))


# --- client_ticker -----------------------------------------------------------------------------

def _client_ticker(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    dark = p["dark"]
    size = float(p["size"])
    height = h or (size * LEADING + 2 * float(p["pad"]))
    runs = []
    for i, name in enumerate(p["names"]):
        if i:
            runs.append({"text": f"  {p['separator']}  ", "color": "accent" if dark else "muted"})
        runs.append({"text": str(name), "bold": True})
    ops: list[dict] = [
        {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": "surface_dark" if dark else "surface", "role": "band"},
        {"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": [runs], "style": "label", "size": size, "color": "on_dark" if dark else "ink",
         "align": "CENTER", "valign": "MIDDLE", "role": "names"},
    ]
    return ops, height


register(Component(
    name="client_ticker",
    description="Bandeau clients en texte seul (pas de logos) : noms en gras séparés par des points, blanc sur dark.",
    props=[
        Prop("names", "list", "Noms des clients.", required=True),
        Prop("dark", "bool", "Bandeau sombre (sinon gris clair).", default=True),
        Prop("separator", "str", "Séparateur.", default="·"),
        Prop("size", "number", "Taille du texte.", default=12),
        Prop("pad", "number", "Marge verticale.", default=12),
    ],
    render=_client_ticker,
    example={"names": ["Médecins Sans Frontières", "UCPA", "Miléade", "Mirova", "Carbios", "Surfrider Foundation"]},
    tags=["cartes"],
))


# --- do_dont -----------------------------------------------------------------------------------

def _do_dont(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    cw = (w - gap) / 2
    pad = 12.0
    ops: list[dict] = []
    y = 0.0
    for pair in p["pairs"]:
        sides = (("do", "success_bg", "success_ink", p["do_label"]), ("dont", "danger_bg", "danger_ink", p["dont_label"]))
        cards = []
        for key, bg, ink, label in sides:
            quote = str(pair.get(key, ""))
            note = pair.get(f"{key}_note") or pair.get(f"note_{key}")
            qh = _text_height(quote, cw - 2 * pad, 11.5)
            nh = _text_height(note, cw - 2 * pad, 10) if note else 0.0
            ch = pad + 16 + qh + (nh + 2 if note else 0) + pad
            cards.append((key, bg, ink, label, quote, note, qh, nh, ch))
        rh = max(c[-1] for c in cards)
        for j, (key, bg, ink, label, quote, note, qh, nh, ch) in enumerate(cards):
            x = j * (cw + gap)
            ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": rh, "shape": "ROUND_RECTANGLE", "fill": bg, "role": key})
            ops.append({"op": "text", "x": x + pad, "y": y + pad - 4, "w": cw - 2 * pad, "h": 12 + INSETS, "text": str(label), "style": "card_label",
                        "size": 10, "color": ink, "role": f"{key}_label"})
            ops.append({"op": "text", "x": x + pad, "y": y + pad + 12, "w": cw - 2 * pad, "h": qh, "markdown": quote, "style": "quote", "size": 11.5,
                        "color": "ink", "role": f"{key}_text"})
            if note:
                ops.append({"op": "text", "x": x + pad, "y": y + pad + 12 + qh, "w": cw - 2 * pad, "h": nh, "markdown": str(note), "style": "caption",
                            "size": 10, "role": f"{key}_note"})
        y += rh + gap
    return ops, h or max(0.0, y - gap)


register(Component(
    name="do_dont",
    description="Paires ✓ / ✕ côte à côte (on-brand / off-brand) : verbatim en gras italique sur fond vert pâle ou rouge pâle, commentaire en dessous.",
    props=[
        Prop("pairs", "list", "Paires : {do, dont, do_note?, dont_note?}.", required=True),
        Prop("do_label", "str", "Libellé de la colonne ✓.", default="✓  On-brand"),
        Prop("dont_label", "str", "Libellé de la colonne ✕.", default="✕  Off-brand"),
        Prop("gap", "number", "Espace entre cartes.", default=12),
    ],
    render=_do_dont,
    example={"pairs": [
        {"do": "« Nous sommes l'agence engagée, des marques engagées. »", "do_note": "Court, symétrique, sans qualificatif.",
         "dont": "« Nous sommes une agence digitale de premier plan, leader dans l'accompagnement des marques engagées. »",
         "dont_note": "Superlatifs et adjectifs de remplissage."},
        {"do": "« Digitale depuis 1999. »", "do_note": "Trois mots, toute l'autorité nécessaire.",
         "dont": "« Fort de plus de 25 ans d'expertise dans le domaine du digital… »", "dont_note": "Trois clichés en une phrase."}]},
    tags=["texte"],
))
