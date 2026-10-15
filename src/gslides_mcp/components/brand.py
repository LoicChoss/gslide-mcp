"""Brand components from the Periscope design system (v1.0, 2026): buttons that
follow their ground, content cards on three grounds, plain hashtags, the
section header with its yellow highlight (or as a lot opener: giant kicker,
pixel icon, key figures at the foot), the client ticker, tracked eyebrows and
the voice do / don't pairs.

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
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, PAD, _text_height, _wrapped_lines

GROUNDS = ("white", "dark", "cyan", "yellow")
THIN = " "  # thin space: the tracking of the eyebrows (Slides has no letter spacing)


def _bold_h(text: str, w: float, size: float) -> float:
    """Box height of a bold text wrapped in ``w`` (bold glyphs run wider)."""
    return _wrapped_lines(text, w, size * BOLD_WRAP) * size * LEADING + INSETS


def _too_long(component: str, field: str, text: str) -> dict:
    """Note to the caller (insert_component's ``warnings``): the text cannot fit at the charter size."""
    t = " ".join(str(text).split())
    return {"op": "warning", "text": f"{component} : {field} « {t[:40] + '…' if len(t) > 40 else t} » trop long, raccourcir"}


def _word_w(text: str, size: float, bold: bool = False) -> float:
    """Width of the longest word of ``text``: the renderer cuts a word wider than its box."""
    longest = max((len(word) for word in str(text).split()), default=0)
    return longest * GLYPH_WRAP * size * (BOLD_WRAP if bold else 1.0)


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


def _pill_size(theme: Theme, size) -> float:
    """A button's text size, raised to the pill style's floor: the pill is sized from what is drawn."""
    return max(float(size), float(theme.size_floor("pill") or 0))


def _button(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    op, bw, bh = _button_op(p["text"], p["ground"], p["variant"], _pill_size(theme, p["size"]), color=p["color"])
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
                                _pill_size(theme, p["size"]), x=x, color=spec.get("color"))
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
    # tags, not a sentence: the small caption style (10 pt floor), like a content card's tags
    size = max(float(p["size"]), float(theme.size_floor("caption") or 0))
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
    natural = _text_height(text, w, size * 1.05)  # capitals run wider than the average glyph
    ops = [{"op": "text", "x": 0, "y": 0, "w": w, "h": max(h or 0.0, natural), "runs": [runs], "style": "caption", "size": size,
            "align": p["align"], "role": "hashtags"}]
    if h is not None and h < natural - 0.5:
        ops.append(_too_long("hashtags", "items", text))
        return ops, natural
    return ops, h or natural


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
    height = h or (max(size, float(theme.size_floor("card_label") or 0)) * LEADING + INSETS)  # the size drawn, floor included
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

CARD_PAD = float(PAD) + 2   # content card: padding inside the frame
CARD_PAD_MIN = 8.0          # the side padding a narrow card gives up before a word is cut
CONTENT_TITLE_SIZE = 15.0   # over the 13 pt card body
EYEBROW_SIZE = 9.5          # the design system's tracked eyebrow (small_ok: a sur-titre)


def _tag_line(tags: list) -> str:
    return "    ".join(("#" + str(t).lstrip("#")).upper() for t in tags)


def _card_side_pad(p: dict, theme: Theme, w: float) -> float:
    """Side padding of a content card: the design's 16 pt, less in a narrow card so that the
    longest word of the title, text and tags fits (the text keeps its size, the box widens)."""
    need = max(_word_w(p["title"] or "", CONTENT_TITLE_SIZE, bold=True), _word_w(p["text"] or "", theme.size("card_body")),
               _word_w(_tag_line(p["tags"] or []), theme.size("caption"))) + 2 * INSET_X
    return max(CARD_PAD_MIN, min(CARD_PAD, (w - need) / 2))


def _content_card(p: dict, theme: Theme, w: float, h: float | None, px: float | None = None) -> tuple[list[dict], float]:
    """One card; ``px`` (side padding shared by a content_cards row) keeps the row's texts aligned."""
    g = _ground(p["ground"])
    pad = CARD_PAD
    px = _card_side_pad(p, theme, w) if px is None else px
    inner = w - 2 * px
    y = pad
    texts: list[dict] = []
    warnings: list[dict] = []
    if p["eyebrow"]:
        texts.append({"op": "text", "x": px, "y": y, "w": inner, "h": 12 + INSETS, "text": _tracked(p["eyebrow"]), "style": "card_label",
                      "size": EYEBROW_SIZE, "bold": True, "color": g["eyebrow"], "small_ok": True, "role": "eyebrow"})
        y += 18
    if p["title"]:
        th = _bold_h(p["title"], inner, CONTENT_TITLE_SIZE)
        texts.append({"op": "text", "x": px, "y": y, "w": inner, "h": th, "markdown": str(p["title"]), "style": "card_title",
                      "size": CONTENT_TITLE_SIZE, "color": g["text"], "highlight": "highlight_alt", "role": "title"})
        y += th + 2
    if p["text"]:
        bh = _text_height(p["text"], inner, theme.size("card_body"))
        texts.append({"op": "text", "x": px, "y": y, "w": inner, "h": bh, "markdown": str(p["text"]), "style": "card_body", "color": g["text"],
                      "role": "body"})
        y += bh + 4
    if p["tags"]:
        tags = _tag_line(p["tags"])
        tg = _text_height(tags, inner, theme.size("caption"))
        texts.append({"op": "text", "x": px, "y": y, "w": inner, "h": tg, "text": tags, "style": "caption",
                      "color": g["tags"], "role": "tags"})
        y += tg + 0.5
    for field, text, size, bold in (("title", p["title"], CONTENT_TITLE_SIZE, True), ("text", p["text"], theme.size("card_body"), False)):
        if text and _word_w(text, size, bold) > inner - 2 * INSET_X + 2:
            word = max(str(text).split(), key=len)
            warnings.append(_too_long("content_card", f"{field}, mot", word))
    if p["cta"]:
        y += 4
        op, bw, bh = _button_op(p["cta"], p["ground"], p["cta_variant"], theme.size("pill"), x=px, y=y)
        op["w"] = min(bw, w - px - 4)  # in a narrow card the pill may take the right padding, never cross the card's edge
        texts.append(op)
        y += bh
    natural = y + pad
    height = h or natural
    if h is not None and h < natural - 0.5:
        # the texts keep the charter size: the card keeps its natural height rather than overlap
        warnings.append(_too_long("content_card", "text" if p["text"] else "title", p["text"] or p["title"]))
        height = natural
    elif h and p["cta"]:  # equalised rows: the CTA sits on the bottom edge
        texts[-1]["y"] = h - pad - texts[-1]["h"]
    frame = {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": g["fill"], "line": g["line"], "role": "card"}
    return [frame] + texts + warnings, height


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
    # one geometry per row: the same side padding, the heights equalised
    pxs = [min(_card_side_pad(c, theme, cw) for c in row) for row in rows]
    naturals = [max(_content_card(c, theme, cw, None, px)[1] for c in row) for row, px in zip(rows, pxs)]
    share = (h - (len(rows) - 1) * gap) / len(rows) if h is not None and rows else None
    for row, px, natural in zip(rows, pxs, naturals):
        rh = max(natural, share) if share is not None else natural  # never under what the texts need
        for j, c in enumerate(row):
            sub, _ = _content_card(c, theme, cw, rh, px)
            ops.extend(shift(sub, j * (cw + gap), y))
        y += rh + gap
    if share is not None and any(n > share + 0.5 for n in naturals):
        longest = max(cards, key=lambda c: len(str(c["text"] or "")) + len(str(c["title"] or "")))
        ops.append(_too_long("content_cards", "text", longest["text"] or longest["title"]))
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

KICKER_SIZE = 54.0       # « LOT 1 » over the title of a lot opener
HEADER_STAT_SIZE = 36.0  # the figures along the foot of a lot opener
HEADER_STAT_GAP = 16.0


def _header_stats(items: list, theme: Theme, w: float, color: str, align: str) -> tuple[list[dict], float]:
    """Big figures side by side with a short label under each, the foot of a lot opener."""
    rows = [(str(it.get("value", "")), str(it.get("label", ""))) if isinstance(it, dict) else (str(it[0]), str(it[1])) for it in items]
    n = max(1, len(rows))
    cw = (w - (n - 1) * HEADER_STAT_GAP) / n
    longest = max((len(v) for v, _ in rows), default=1)
    # one size for the row, the longest figure on one line (Barlow bold digits ≈ 0.58 × size)
    size = max(20.0, min(HEADER_STAT_SIZE, (cw - 2 * INSET_X) / (longest * 0.58)))
    vh = size * 1.2 + INSETS
    lh = max((_text_height(label, cw, theme.size("body")) for _, label in rows), default=0.0)  # the label is read: body size
    ops: list[dict] = []
    for i, (value, label) in enumerate(rows):
        x = i * (cw + HEADER_STAT_GAP)
        ops.append({"op": "text", "x": x, "y": 0, "w": cw, "h": vh, "text": value, "style": "title", "size": round(size, 1), "color": color,
                    "align": align, "role": "stat_value"})
        ops.append({"op": "text", "x": x, "y": vh - 6, "w": cw, "h": lh, "text": label, "style": "body", "color": color,
                    "align": align, "role": "stat_label"})
    return ops, vh - 6 + lh


def _section_header(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    dark = p["dark"]
    color = "on_dark" if dark else "ink"
    size = float(p["size"])
    ops: list[dict] = []
    y = 0.0
    hw = w  # the texts keep clear of the icon
    if p["icon"]:
        d = float(p["icon_size"])
        hw = w - d - 24
        ops.append({"op": "image", "x": w - d, "y": 0, "w": d, "h": d, "asset": str(p["icon"]), "contain": True,
                    "tint": p["icon_color"] or ("accent" if dark else "ink"), "role": "icon"})
    if p["eyebrow"]:
        ops.append({"op": "text", "x": 0, "y": y, "w": hw, "h": 12 + INSETS, "text": _tracked(p["eyebrow"]), "style": "card_label", "size": 10,
                    "bold": True, "color": "accent" if dark else "ink", "align": p["align"], "role": "eyebrow"})
        y += 22
    if p["kicker"]:
        kh = KICKER_SIZE * 1.2 + INSETS
        ops.append({"op": "text", "x": 0, "y": y, "w": hw, "h": kh, "text": str(p["kicker"]), "style": "title", "size": KICKER_SIZE,
                    "color": color, "align": p["align"], "role": "kicker"})
        y += kh - 4
    th = _text_height(p["title"], hw, size)  # bold Barlow titles run narrower than the estimate
    ops.append({"op": "text", "x": 0, "y": y, "w": hw, "h": th, "markdown": str(p["title"]), "style": "title", "size": size, "color": color,
                "highlight": p["highlight"], "align": p["align"], "role": "title"})
    y += th + 4
    if p["text"]:
        bh = _text_height(p["text"], hw, theme.size("body"))
        ops.append({"op": "text", "x": 0, "y": y, "w": hw, "h": bh, "markdown": str(p["text"]), "style": "body", "color": color,
                    "align": p["align"], "role": "body"})
        y += bh + 6
    if p["tags"]:
        sub, sh = _hashtags({"items": p["tags"], "dark": dark, "color": None, "size": 11, "align": p["align"]}, theme, hw, None)
        ops.extend(shift(sub, 0, y))
        y += sh
    if p["icon"]:
        y = max(y, float(p["icon_size"]))
    if p["stats"]:
        sub, sh = _header_stats(list(p["stats"]), theme, w, color, p["align"])
        # at the foot of the box when it is given (a lot opener fills the slide), else under the title
        sy = max(y + 28, (h - sh) if h else 0.0)
        ops.extend(shift(sub, 0, sy))
        y = sy + sh
    if h is not None and h < y - 0.5:
        # the texts keep the charter size: the header keeps its natural height rather than overlap
        if p["stats"]:
            field, text = "stats", " ".join(str(o["text"]) for o in ops if o.get("role") == "stat_label")
        else:
            field, text = ("text", p["text"]) if p["text"] else ("title", p["title"])
        ops.append(_too_long("section_header", field, text))
        return ops, y
    return ops, h or y


register(Component(
    name="section_header",
    description="En-tête de section signature : eyebrow tracké, titre avec ==surlignage jaune== du mot clé, paragraphe, hashtags inline ; "
                "en ouverture de lot : « LOT 1 » géant, picto pixel à droite, chiffres clés en pied.",
    props=[
        Prop("title", "markdown", "Titre, avec ==…== sur le passage à surligner.", required=True),
        Prop("eyebrow", "str", "Sur-titre en capitales espacées."),
        Prop("text", "markdown", "Paragraphe sous le titre."),
        Prop("tags", "list", "Hashtags inline."),
        Prop("highlight", "color", "Couleur du surlignage.", default="highlight_alt"),
        Prop("size", "number", "Taille du titre.", default=22),
        Prop("dark", "bool", "Sur fond sombre.", default=False),
        Prop("align", "choice", "Alignement.", default="START", choices=["START", "CENTER"]),
        Prop("kicker", "str", "Très grand mot au-dessus du titre (54 pt) : « LOT 1 », « 02 », « PARTIE 3 »."),
        Prop("icon", "image", "Picto pixel en haut à droite (asset du dossier Drive, ex. 'px-heart'), teinté encre (accent sur fond sombre)."),
        Prop("icon_size", "number", "Côté du picto en pt (48 à 120 selon la charte).", default=112),
        Prop("icon_color", "color", "Teinte du picto (défaut : encre, accent sur fond sombre)."),
        Prop("stats", "list", "Chiffres clés en pied : {value, label} (ou paires), côte à côte ; collés en bas quand la hauteur est donnée."),
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
    size = max(float(p["size"]), float(theme.size_floor("label") or 0))  # names are read: body floor
    runs = []
    for i, name in enumerate(p["names"]):
        if i:
            runs.append({"text": f"  {p['separator']}  ", "color": "accent" if dark else "muted"})
        runs.append({"text": str(name), "bold": True})
    # a long list wraps onto a second line (the band grows) rather than shrink under the floor
    text_h = _wrapped_lines("".join(r["text"] for r in runs), w, size * BOLD_WRAP) * size * LEADING
    natural = text_h + 2 * float(p["pad"])
    height = h or natural
    warn = h is not None and h < text_h + INSETS - 0.5
    if warn:
        height = natural
    ops: list[dict] = [
        {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": "surface_dark" if dark else "surface", "role": "band"},
        {"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": [runs], "style": "label", "size": size, "color": "on_dark" if dark else "ink",
         "align": "CENTER", "valign": "MIDDLE", "role": "names"},
    ]
    if warn:
        ops.append(_too_long("client_ticker", "names", ", ".join(str(n) for n in p["names"])))
    return ops, height


register(Component(
    name="client_ticker",
    description="Bandeau clients en texte seul (pas de logos) : noms en gras séparés par des points, blanc sur dark.",
    props=[
        Prop("names", "list", "Noms des clients.", required=True),
        Prop("dark", "bool", "Bandeau sombre (sinon gris clair).", default=True),
        Prop("separator", "str", "Séparateur.", default="·"),
        Prop("size", "number", "Taille du texte (13 pt minimum, la taille du corps).", default=13),
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
    qs, ns = theme.size("quote"), theme.size("caption")
    ops: list[dict] = []
    y = 0.0
    for pair in p["pairs"]:
        sides = (("do", "success_bg", "success_ink", p["do_label"]), ("dont", "danger_bg", "danger_ink", p["dont_label"]))
        cards = []
        for key, bg, ink, label in sides:
            quote = str(pair.get(key, ""))
            note = pair.get(f"{key}_note") or pair.get(f"note_{key}")
            qh = _bold_h(quote, cw - 2 * pad, qs)  # the verbatim is bold italic
            nh = _text_height(note, cw - 2 * pad, ns) if note else 0.0
            ch = pad + 16 + qh + (nh + 2 if note else 0) + pad
            cards.append((key, bg, ink, label, quote, note, qh, nh, ch))
        rh = max(c[-1] for c in cards)
        for j, (key, bg, ink, label, quote, note, qh, nh, ch) in enumerate(cards):
            x = j * (cw + gap)
            ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": rh, "shape": "ROUND_RECTANGLE", "fill": bg, "role": key})
            ops.append({"op": "text", "x": x + pad, "y": y + pad - 4, "w": cw - 2 * pad, "h": 12 + INSETS, "text": str(label), "style": "card_label",
                        "color": ink, "role": f"{key}_label"})
            ops.append({"op": "text", "x": x + pad, "y": y + pad + 12, "w": cw - 2 * pad, "h": qh, "markdown": quote, "style": "quote",
                        "color": "ink", "role": f"{key}_text"})
            if note:
                ops.append({"op": "text", "x": x + pad, "y": y + pad + 12 + qh, "w": cw - 2 * pad, "h": nh, "markdown": str(note), "style": "caption",
                            "role": f"{key}_note"})
        y += rh + gap
    natural = max(0.0, y - gap)
    if h is not None and h < natural - 0.5:
        # the verbatims keep the charter size: the pairs keep their natural height rather than overlap
        longest = max((str(pair.get(k, "")) for pair in p["pairs"] for k in ("do", "dont")), key=len)
        ops.append(_too_long("do_dont", "verbatim", longest))
        return ops, natural
    return ops, h or natural


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
