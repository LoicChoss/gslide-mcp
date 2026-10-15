"""Lot 4 text / structure components: agenda, numbered_list, big_numbers,
phase_cards, compare_cards, before_after, stat_pair, palette.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only. Markdown props accept
``==texte==`` for the marker highlight (role ``highlight``).

Body texts are drawn at the theme's size (13 pt on the charter) and never
shrink: a long text wraps and its block grows, the items of a row sharing one
geometry (titles, texts, rules at the same height). A text that cannot hold —
a word wider than its column, a height forced by the caller — leaves a
``warning`` op, which ``insert_component`` returns in ``warnings``.
"""

from __future__ import annotations

import re

from ..themes import Theme
from . import Component, Prop, register, shift
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, PAD, _wrapped_lines, caps_centre, too_long

_DARK = {"surface_dark", "surface_dark_2", "ink", "text", "device_frame"}
CAPS_BOLD = 1.3  # bold capitals (eyebrows, uppercase titles) run this much wider than the wrap estimate
_MD = re.compile(r"\*\*|__|==|`")


def _fg(fill: str | None) -> str:
    return "on_dark" if fill in _DARK else "ink"


def _rows(items: list, cols: int) -> list[list]:
    return [items[i:i + cols] for i in range(0, len(items), cols)]


def _box_h(text, width: float, size: float, wide: float = 1.0) -> float:
    """Text-box height of ``text`` (markdown marks ignored) wrapped in ``width`` pt at ``size`` pt, insets included.

    ``wide`` widens the glyphs of the wrap estimate: ``BOLD_WRAP`` for bold, ``CAPS_BOLD`` for bold capitals.
    """
    return _wrapped_lines(_MD.sub("", str(text)), width, size * wide) * size * LEADING + INSETS


def _long_word(text, width: float, size: float, wide: float = 1.0) -> str | None:
    """The longest word of ``text`` when it is wider than a ``width`` pt box at ``size`` (the renderer cuts it), else None."""
    words = _MD.sub("", str(text)).split()
    if not words:
        return None
    word = max(words, key=len)
    return word if len(word) * size * GLYPH_WRAP * wide > width - 2 * INSET_X + 1 else None


def _ink_span(top: float, size: float, lines: int = 1) -> tuple[float, float]:
    """Top of the capitals of the first line and baseline of the last line of a top-anchored text box at ``top``.

    The metrics of ``caps_centre`` and ``label_top``: capitals 0.7 × size tall,
    the baseline 0.35 × size under their centre.
    """
    c = caps_centre(top, size)
    return c - 0.35 * size, c + 0.35 * size + (lines - 1) * size * LEADING


def _check_words(out: list[dict], component: str, field: str, texts, width: float, size: float, wide: float = 1.0) -> None:
    """A warning in ``out`` for each text whose longest word does not hold in ``width`` at ``size``."""
    for t in texts:
        word = _long_word(t, width, size, wide) if t else None
        if word:
            out.append(too_long(component, field, word))


def _auto_cols(n: int, w: float, gap: float, fits) -> int:
    """Columns for ``n`` items when the caller gives none: all on one row, one column less while a
    word does not hold in a column (``fits(column_width)``) — the block grows a row rather than cut it."""
    cols = max(1, n)
    while cols > 1 and not fits((w - (cols - 1) * gap) / cols):
        cols -= 1
    return cols


# --- agenda -------------------------------------------------------------------------

def _agenda(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    row = float(p["row_h"])
    # titles at the label size (13 pt), never under the floor: a long one wraps and its row grows
    size = max(float(p["size"] or theme.size("label")), float(theme.size_floor("label") or 0))
    color = "on_dark" if p["dark"] else "ink"
    entries = []
    for i, it in enumerate(items):
        num, title, current = (it.get("num"), it.get("title", ""), bool(it.get("current"))) if isinstance(it, dict) else (None, it, False)
        entries.append((str(num) if num is not None else f"{i + 1:02d}", str(title), current))
    # the chip grows with the row (16 pt in a 24 pt row); a date or a longer label widens it into a rounded pill
    chip_h = max(16.0, row - 8)
    chip_size = 11.0 if chip_h >= 24 else 10.0
    longest = max((len(n) for n, _, _ in entries), default=2)
    wide = longest > 3
    chip_w = max(28.0, longest * chip_size * 0.6 + 2 * INSET_X + 10) if wide else 28.0
    tx = chip_w + 10
    tw = w - tx
    ops: list[dict] = []
    warnings: list[dict] = []
    y = 0.0
    for num, title, current in entries:
        lines = _wrapped_lines(title, tw, size)
        # one line keeps the row (a 13 pt line holds in 24 pt, centred: the box stays in its row);
        # a wrapped title makes its row as tall as its text
        rh = max(row, lines * size * LEADING + INSETS) if lines > 1 else row
        text_h = min(lines * size * LEADING + INSETS, rh)
        fill = "accent" if current else p["chip_fill"]
        chip: dict = {"op": "box", "x": 0, "y": y + (rh - chip_h) / 2, "w": chip_w, "h": chip_h, "fill": fill, "role": "chip",
                      "text": num, "style": "badge", "size": chip_size, "color": "on_dark" if fill in _DARK else "on_chip",
                      "align": "CENTER", "valign": "MIDDLE"}
        if wide:
            chip["shape"] = "ROUND_RECTANGLE"
        ops.append(chip)
        ops.append({"op": "text", "x": tx, "y": y + (rh - text_h) / 2, "w": tw, "h": text_h, "text": title,
                    "style": "label", "size": size, "color": color, "valign": "MIDDLE"})
        y += rh
    _check_words(warnings, "agenda", "items", [t for _, t, _ in entries], tw, size)
    if h is not None and y > h + 0.5:
        warnings.append(too_long("agenda", "items", max((t for _, t, _ in entries), key=len, default="")))
    return ops + warnings, h or y


register(Component(
    name="agenda", description="Sommaire : chip numérotée (acide) + titre de section par ligne (dark=True sur fond sombre) ; "
                               "avec des dates en guise de numéros, un calendrier en pastilles arrondies, l'échéance en cours en menthe.",
    props=[
        Prop("items", "list", "Sections : texte, ou {num, title, current} ; num peut être une date (« 13 · 14 · 15 oct. ») : "
                              "la pastille s'élargit et s'arrondit ; current la passe en menthe.", required=True),
        Prop("dark", "bool", "Texte clair (fond sombre).", default=False),
        Prop("size", "number", "Taille des titres (défaut : style label du thème, 13 pt ; jamais moins : un titre long passe à la ligne)."),
        Prop("row_h", "number", "Hauteur d'une ligne ; la pastille fait 8 pt de moins (40 pour un calendrier). Un titre sur deux lignes agrandit la sienne.",
             default=24),
        Prop("chip_fill", "color", "Fond des pastilles (surface : gris, pour un calendrier).", default="chip"),
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
    ts, bs = theme.size("card_title"), theme.size("body")
    wide = CAPS_BOLD if square else BOLD_WRAP
    ops_bg: list[dict] = []
    ops: list[dict] = []
    warnings: list[dict] = []
    y = 0.0
    centers: list[float] = []
    for i, it in enumerate(items):
        title = str(it.get("title", ""))
        title = title.upper() if square else title
        sub = it.get("sub")
        t_lines = _wrapped_lines(title, text_w, ts * wide)
        title_h = t_lines * ts * LEADING + INSETS
        s_lines = _wrapped_lines(_MD.sub("", str(sub)), text_w, bs) if sub else 0
        sub_h = s_lines * bs * LEADING + INSETS if sub else 0.0
        group_h = title_h + (sub_h - 2 if sub else 0.0)  # the sub's box starts 2 pt into the title's bottom inset
        if square:
            # a chip in front of the first line, like a bullet: centred on its capitals
            row_h = max(d + 4, group_h)
            ty = y + (row_h - group_h) / 2
            cy = caps_centre(ty, ts)
        else:
            # the disc centred on the ink of the text (first capitals to last baseline), the text boxes inside the row
            ink_top = _ink_span(0, ts)[0]
            ink_bottom = _ink_span(title_h - 2, bs, s_lines)[1] if sub else _ink_span(0, ts, t_lines)[1]
            mid = (ink_top + ink_bottom) / 2
            row_h = max(d + 4, 2 * max(mid, group_h - mid))
            cy = y + row_h / 2
            ty = cy - mid
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
                # « #n » on the disc's centre line: its capitals centred on it
                ops.append({"op": "text", "x": d + 8, "y": cy - caps_centre(0, ts), "w": 40, "h": ts * LEADING + INSETS, "text": f"#{n}",
                            "style": "card_title", "size": ts, "color": "ink", "role": "index"})
                ops.append({"op": "line", "x1": d + 48, "y1": y + 4, "x2": d + 48, "y2": y + row_h - 4, "color": "rule", "weight": 1})
        ops.append({"op": "text", "x": text_x, "y": ty, "w": text_w, "h": title_h, "text": title,
                    "style": "card_title", "size": ts, "role": "title"})
        if sub:
            ops.append({"op": "text", "x": text_x, "y": ty + title_h - 2, "w": text_w, "h": sub_h, "markdown": str(sub),
                        "style": "body", "size": bs, "color": "muted"})
        _check_words(warnings, "numbered_list", "title", [title], text_w, ts, wide)
        _check_words(warnings, "numbered_list", "sub", [sub], text_w, bs)
        y += row_h + gap
    connector: list[dict] = []
    if p["connector"] and len(centers) > 1:
        connector.append({"op": "line", "x1": d / 2, "y1": centers[0], "x2": d / 2, "y2": centers[-1], "color": "accent", "weight": 4,
                          "role": "connector"})
    height = y - gap if items else 0.0
    if h is not None and height > h + 0.5:
        warnings.append(too_long("numbered_list", "items", max((str(it.get("title", "")) for it in items), key=len, default="")))
    return ops_bg + connector + ops + warnings, h or height


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
    ls, bs = theme.size("label"), theme.size("body")
    cols = int(p["cols"] or _auto_cols(len(items), w, 0.0, lambda cw: not any(
        _long_word(it.get("title", ""), cw - 16, ls, BOLD_WRAP) or _long_word(it.get("text", ""), cw - 16, bs) for it in items)))
    col_w = w / cols
    tw = col_w - 16
    ops: list[dict] = []
    warnings: list[dict] = []
    height = 0.0
    y0 = 0.0
    for r, row in enumerate(_rows(items, cols)):
        titles = [str(it.get("title", "")) for it in row]
        # one geometry per row: the numbers, then the titles, then the texts each start at one height
        title_h = max((sum(_wrapped_lines(line, tw, ls * BOLD_WRAP) for line in t.split("\n")) * ls * LEADING + INSETS
                       for t in titles if t), default=0.0)
        ty = y0 + 66
        by = ty + title_h + 4
        bottom = ty
        for j, it in enumerate(row):
            x = j * col_w
            num = str(it.get("num", r * cols + j + 1))
            ops.append({"op": "text", "x": x, "y": y0, "w": col_w, "h": 60 + INSETS, "text": num, "style": "stat_value",
                        "size": 54, "color": "ink", "align": "CENTER", "role": "number"})
            if titles[j]:
                paras = [[{"text": line, "bold": True, "highlight": p["highlight"]}] for line in titles[j].split("\n")]
                ops.append({"op": "text", "x": x + 8, "y": ty, "w": tw, "h": title_h, "runs": paras, "style": "label",
                            "size": ls, "align": "CENTER", "role": "title"})
                bottom = max(bottom, ty + title_h)
            if it.get("text"):
                th = _box_h(it["text"], tw, bs)
                ops.append({"op": "text", "x": x + 8, "y": by, "w": tw, "h": th, "markdown": str(it["text"]),
                            "style": "body", "size": bs, "align": "CENTER"})
                bottom = max(bottom, by + th)
        _check_words(warnings, "big_numbers", "title", titles, tw, ls, BOLD_WRAP)
        _check_words(warnings, "big_numbers", "text", [it.get("text") for it in row], tw, bs)
        height = max(height, bottom)
        # row_gap is the pitch of the rows; a taller row pushes the next one down
        y0 += max(float(p["row_gap"]), bottom - y0 + 16)
    if h is not None and height > h + 0.5:
        warnings.append(too_long("big_numbers", "text", max((str(it.get("text") or it.get("title", "")) for it in items), key=len, default="")))
    return ops + warnings, h or height


register(Component(
    name="big_numbers", description="Colonnes « 1 2 3 » : chiffre géant, titre surligné (marqueur), paragraphe centré.",
    props=[
        Prop("items", "list", "Colonnes : {num?, title, text?} (title accepte des sauts de ligne).", required=True),
        Prop("cols", "number", "Colonnes par rangée (défaut : toutes, une de moins tant qu'un mot ne tient pas dans sa colonne)."),
        Prop("row_gap", "number", "Pas des rangées quand il y en a plusieurs (une rangée plus haute repousse la suivante).", default=170),
        Prop("highlight", "color", "Couleur du surlignage des titres.", default="highlight"),
    ],
    render=_big_numbers,
    example={"items": [{"title": "3 niveaux,\njamais 4", "text": "Toute page du site est atteignable en trois clics depuis l'accueil."},
                       {"title": "Une page,\nune intention", "text": "Un carrefour oriente et ne raconte rien."},
                       {"title": "La fiscalité est une porte", "text": "La page « don et impôt » pèse près de 10 % des pages vues."}]},
    tags=["texte"],
))


# --- phase_cards ------------------------------------------------------------------------

_ICON_W = 34.0  # picto (26 pt) + gap before the note beside it


def _note_beside(ph: dict, w: float, size: float) -> bool:
    """The note fits beside the picto: its longest word holds in the narrower column."""
    return not (ph.get("icon") and ph.get("note")) or _long_word(ph["note"], w - 12 - _ICON_W - 12, size) is None


def _phase_parts(ph: dict, w: float, theme: Theme, beside: bool) -> dict:
    """Heights of a phase card's sections (title, text, picto + note, deliverables), each with its leading gap."""
    inner = w - 2 * 12
    ts, bs = theme.size("card_title"), theme.size("body")
    parts = {"title": _box_h(ph.get("title", ""), inner, ts, BOLD_WRAP), "text": _box_h(ph["text"], inner, bs) if ph.get("text") else 0.0,
             "note": 0.0, "deliv": 0.0}
    icon, note = ph.get("icon"), ph.get("note")
    if icon or note:
        nw = w - 12 - _ICON_W - 12 if icon and beside else inner
        nh = _box_h(note, nw, bs) if note else 0.0
        if icon and note and not beside:
            block = 30 + nh  # the picto on its own line, the note under it at full width
        else:
            block = max(nh, 30 if icon else 0)
        parts["note"] = 6 + block
    if ph.get("deliverables"):
        lines = sum(_wrapped_lines(f"→  {d}", inner, bs) for d in ph["deliverables"])
        parts["deliv"] = 6 + 16 + lines * bs * LEADING + INSETS
    return parts


def _phase_card(ph: dict, w: float, h: float, num_size: float, theme: Theme, slots: dict, beside: bool) -> list[dict]:
    """One card at origin, its sections at the row's heights (``slots``) so they line up from card to card."""
    top = num_size + 8
    inner = w - 2 * 12
    bs = theme.size("body")
    texts: list[dict] = []
    y = top + 12
    texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": slots["title"], "text": str(ph.get("title", "")),
                  "style": "card_title", "size": theme.size("card_title"), "role": "title"})
    y += slots["title"]
    if ph.get("text"):
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": slots["text"], "markdown": str(ph["text"]), "style": "body", "size": bs})
    y += slots["text"]
    if slots["note"]:
        by = y + 6
        icon, note = ph.get("icon"), ph.get("note")
        if icon and note and not beside:
            texts.append({"op": "image", "x": 12, "y": by + 2, "w": 26, "h": 26, "asset": str(icon), "tint": "accent"})
            texts.append({"op": "text", "x": 12, "y": by + 30, "w": inner, "h": slots["note"] - 36, "markdown": str(note), "style": "body", "size": bs})
        else:
            nx = 12 + (_ICON_W if icon else 0)
            if icon:
                # the picto centred on the capitals of the note's first line
                iy = caps_centre(by, bs) - 13 if note else by + 2
                texts.append({"op": "image", "x": 12, "y": iy, "w": 26, "h": 26, "asset": str(icon), "tint": "accent"})
            if note:
                texts.append({"op": "text", "x": nx, "y": by, "w": w - nx - 12, "h": slots["note"] - 6, "markdown": str(note),
                              "style": "body", "size": bs})
    y += slots["note"]
    if ph.get("deliverables"):
        dy = y + 6
        texts.append({"op": "text", "x": 12, "y": dy, "w": inner, "h": 14 + INSETS, "text": "LIVRABLES", "style": "card_label", "role": "deliverables"})
        runs = [[{"text": "→  ", "bold": True, "color": "accent"}, {"text": str(d)}] for d in ph["deliverables"]]
        texts.append({"op": "text", "x": 12, "y": dy + 16, "w": inner, "h": slots["deliv"] - 22, "runs": runs, "style": "body", "size": bs})
    ops: list[dict] = [
        {"op": "text", "x": 0, "y": 0, "w": 60, "h": num_size + INSETS, "text": str(ph.get("num", "")), "style": "card_big",
         "size": num_size, "color": "accent", "role": "number"},
        {"op": "box", "x": 0, "y": top, "w": w, "h": h - top, "shape": "ROUND_RECTANGLE", "fill": "background",
         "line": {"color": "accent", "weight": 1.5}, "role": "card"},
    ]
    return ops + texts


def _phase_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    phases = [dict(ph) for ph in p["phases"]]
    for i, ph in enumerate(phases):
        ph.setdefault("num", i + 1)
    gap = float(p["gap"])
    ts, bs = theme.size("card_title"), theme.size("body")

    def fits(cw: float) -> bool:
        inner = cw - 2 * 12
        return not any(_long_word(ph.get("title", ""), inner, ts, BOLD_WRAP) or any(_long_word(t, inner, bs) for t in (
            ph.get("text", ""), ph.get("note", ""), *(ph.get("deliverables") or []))) for ph in phases)

    cols = int(p["cols"] or _auto_cols(len(phases), w, gap, fits))
    cw = (w - (cols - 1) * gap) / cols
    num_size = float(p["num_size"])
    inner = cw - 2 * 12
    ops: list[dict] = []
    warnings: list[dict] = []
    y = 0.0
    for row in _rows(phases, cols):
        # one geometry per row: titles, texts, notes and deliverables start at the same height in every card
        beside = all(_note_beside(ph, cw, bs) for ph in row)
        parts = [_phase_parts(ph, cw, theme, beside) for ph in row]
        slots = {k: max(pt[k] for pt in parts) for k in ("title", "text", "note", "deliv")}
        natural = num_size + 8 + 12 + sum(slots.values()) + 12
        row_h = h or natural
        if h is not None and natural > h + 0.5:
            longest = max(row, key=lambda ph: len(str(ph.get("text", ""))) + len(str(ph.get("note", ""))))
            warnings.append(too_long("phase_cards", "text", longest.get("text") or longest.get("note") or longest.get("title", "")))
        for j, ph in enumerate(row):
            ops.extend(shift(_phase_card(ph, cw, row_h, num_size, theme, slots, beside), j * (cw + gap), y))
            _check_words(warnings, "phase_cards", "title", [ph.get("title")], inner, ts, BOLD_WRAP)
            _check_words(warnings, "phase_cards", "text", [ph.get("text")], inner, bs)
            _check_words(warnings, "phase_cards", "note", [ph.get("note")], inner, bs)
            _check_words(warnings, "phase_cards", "deliverables", ph.get("deliverables") or [], inner, bs)
        y += row_h + gap
    return ops + warnings, y - gap if phases else 0.0


register(Component(
    name="phase_cards", description="Cartes de phases : gros numéro accent au-dessus d'une carte à contour accent (titre, texte, picto + note, livrables →).",
    props=[
        Prop("phases", "list", "Phases : {num?, title, text?, icon?, note?, deliverables?: [..]}.", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes, une de moins tant qu'un mot ne tient pas dans sa carte)."),
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


def _compare_parts(c: dict, inner: float, theme: Theme) -> dict:
    """Heights of a card's label (with the advance to the title), title and text."""
    mark = _KIND[c.get("kind", "neutral")][1]
    label = mark + str(c["label"]).upper() if c.get("label") else ""
    return {"label": _box_h(label, inner, theme.size("card_label"), CAPS_BOLD) - 6 if label else 0.0,
            "title": _box_h(c.get("title", ""), inner, theme.size("card_title"), BOLD_WRAP),
            "text": _box_h(c["text"], inner, theme.size("body")) + 2 if c.get("text") else 0.0}


def _compare_card(c: dict, w: float, h: float, theme: Theme, slots: dict) -> list[dict]:
    fill, mark, label_col, title_col, text_col = _KIND[c.get("kind", "neutral")]
    inner = w - 2 * PAD
    texts: list[dict] = []
    y = float(PAD) - 2
    if c.get("label"):
        texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": slots["label"] + 6, "text": mark + str(c["label"]).upper(),
                      "style": "card_label", "color": label_col, "role": "label"})
    y += slots["label"]
    texts.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": slots["title"], "markdown": str(c.get("title", "")),
                  "style": "card_title", "size": theme.size("card_title"), "color": title_col, "role": "title"})
    y += slots["title"]
    if c.get("text"):
        texts.append({"op": "text", "x": PAD, "y": y + 2, "w": inner, "h": max(h - y - 2 - PAD, slots["text"] - 2), "markdown": str(c["text"]),
                      "style": "body", "size": theme.size("body"), "color": text_col})
    return [{"op": "box", "x": 0, "y": 0, "w": w, "h": h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "card"}] + texts


def _compare_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    cards = list(p["cards"])
    for c in cards:
        if c.get("kind", "neutral") not in _KIND:
            raise ValueError(f"compare_cards: kind must be one of {', '.join(_KIND)}; got {c.get('kind')!r}")
    gap = float(p["gap"])
    ts, bs = theme.size("card_title"), theme.size("body")
    cols = int(p["cols"] or _auto_cols(len(cards), w, gap, lambda cw: not any(
        _long_word(c.get("title", ""), cw - 2 * PAD, ts, BOLD_WRAP) or _long_word(c.get("text", ""), cw - 2 * PAD, bs) for c in cards)))
    cw = (w - (cols - 1) * gap) / cols
    inner = cw - 2 * PAD
    ops: list[dict] = []
    warnings: list[dict] = []
    y = 0.0
    for row in _rows(cards, cols):
        # one geometry per row: labels, titles and texts start at the same height in every card
        parts = [_compare_parts(c, inner, theme) for c in row]
        slots = {k: max(pt[k] for pt in parts) for k in ("label", "title", "text")}
        natural = PAD - 2 + sum(slots.values()) + PAD
        row_h = h or natural
        if h is not None and natural > h + 0.5:
            longest = max(row, key=lambda c: len(str(c.get("text", ""))) + len(str(c.get("title", ""))))
            warnings.append(too_long("compare_cards", "text" if longest.get("text") else "title", longest.get("text") or longest.get("title", "")))
        for j, c in enumerate(row):
            ops.extend(shift(_compare_card(c, cw, row_h, theme, slots), j * (cw + gap), y))
            _check_words(warnings, "compare_cards", "title", [c.get("title")], inner, theme.size("card_title"), BOLD_WRAP)
            _check_words(warnings, "compare_cards", "text", [c.get("text")], inner, theme.size("body"))
        y += row_h + gap
    return ops + warnings, y - gap if cards else 0.0


register(Component(
    name="compare_cards", description="Idée reçue / réponse : cartes arrondies ✗ (gris, libellé corail), ✓ (menthe) ou neutres (gris), hauteurs égalisées.",
    props=[
        Prop("cards", "list", "Cartes : {kind: bad|good|neutral, label?, title, text?}.", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes, une de moins tant qu'un mot ne tient pas dans sa carte)."),
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

def _ba_mark(good: bool) -> tuple[str, str, str]:
    return ("accent", "ink", "✓  ") if good else ("surface", "coral", "✗  ")


def _ba_layout(sides: list[dict], inner: float, theme: Theme, paired: bool) -> tuple[float, list[list[float]], float]:
    """Title height, item heights per side and note height; ``paired`` gives item k one height on both sides."""
    bs, cs, ls = theme.size("body"), theme.size("caption"), theme.size("card_label")
    title_h = max(_box_h(_ba_mark(k == 1)[2] + str(s.get("title", "")).upper(), inner, ls, CAPS_BOLD) for k, s in enumerate(sides))
    items = [[_box_h(it, inner, bs) for it in s.get("items", [])] for s in sides]
    if paired:
        n = max(len(hs) for hs in items)
        row = [max(hs[k] for hs in items if k < len(hs)) for k in range(n)]
        items = [row[:len(hs)] for hs in items]
    note_h = max((_box_h(s["note"], inner, cs) for s in sides if s.get("note")), default=0.0)
    return title_h, items, note_h


def _panel(side: dict, w: float, h: float, good: bool, theme: Theme, title_h: float, item_hs: list[float], rows_h: float,
           note_h: float) -> list[dict]:
    """A panel at origin: caps title, items separated by rules, note in italics (at ``rows_h`` under the title, on both panels)."""
    fill, ink, mark = _ba_mark(good)
    inner = w - 2 * 12
    texts: list[dict] = []
    rules: list[dict] = []
    y = 8.0
    texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": title_h, "text": mark + str(side.get("title", "")).upper(),
                  "style": "card_label", "color": ink, "role": "title"})
    y += title_h - 2
    items_top = y
    for it, th in zip(side.get("items", []), item_hs):
        texts.append({"op": "text", "x": 12, "y": y, "w": inner, "h": th, "markdown": str(it), "style": "body", "size": theme.size("body")})
        y += th
        rules.append({"op": "line", "x1": 12, "y1": y, "x2": w - 12, "y2": y, "color": "background", "weight": 1, "role": "rule"})
    if side.get("note"):
        texts.append({"op": "text", "x": 12, "y": items_top + rows_h + 4, "w": inner, "h": note_h, "text": str(side["note"]), "style": "caption",
                      "size": theme.size("caption"), "italic": True, "color": ink, "role": "note"})
    box = {"op": "box", "x": 0, "y": 0, "w": w, "h": h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "panel"}
    return [box] + rules + texts


def _panel_h(title_h: float, rows_h: float, note_h: float) -> float:
    return 8 + title_h - 2 + rows_h + (4 + note_h if note_h else 0.0) + 8


def _before_after(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    bs = theme.size("body")
    sides = [p["before"], p["after"]]
    pw = (w - gap) / 2
    texts = [it for s in sides for it in s.get("items", [])]
    # side by side, item k of the before facing item k of the after; when a word (a URL) does not hold
    # in a half-width panel at 13 pt, the panels stack, the arrow pointing down
    stacked = h is None and any(_long_word(t, pw - 24, bs) for t in texts)
    warnings: list[dict] = []
    _check_words(warnings, "before_after", "items", texts, (w if stacked else pw) - 24, bs)
    if stacked:
        ops: list[dict] = []
        y = 0.0
        for k, s in enumerate(sides):
            title_h, (item_hs,), note_h = _ba_layout([s], w - 24, theme, False)
            ph = _panel_h(title_h, sum(item_hs), note_h if s.get("note") else 0.0)
            ops += shift(_panel(s, w, ph, k == 1, theme, title_h, item_hs, sum(item_hs), note_h), 0, y)
            if k == 0 and p["arrow"]:
                ops.append({"op": "text", "x": w / 2 - 16, "y": ph + gap / 2 - 16, "w": 32, "h": 32, "text": "↓", "style": "label", "size": 18,
                            "bold": True, "align": "CENTER", "valign": "MIDDLE", "role": "arrow"})
            y += ph + gap
        return ops + warnings, y - gap
    title_h, (before_hs, after_hs), note_h = _ba_layout(sides, pw - 24, theme, True)
    rows_h = max(sum(before_hs), sum(after_hs))
    natural = _panel_h(title_h, rows_h, note_h)
    if h is not None and natural > h + 0.5:
        warnings.append(too_long("before_after", "items", max(texts, key=lambda t: len(str(t)), default="")))
    height = h or natural
    left = _panel(p["before"], pw, height, False, theme, title_h, before_hs, rows_h, note_h)
    right = _panel(p["after"], pw, height, True, theme, title_h, after_hs, rows_h, note_h)
    ops = left + shift(right, pw + gap, 0)
    if p["arrow"]:
        ops.append({"op": "text", "x": pw, "y": height / 2 - 16, "w": gap, "h": 32, "text": "→", "style": "label", "size": 18,
                    "bold": True, "align": "CENTER", "valign": "MIDDLE", "role": "arrow"})
    return ops + warnings, height


register(Component(
    name="before_after", description="Avant / après : panneau ✗ gris (titre corail) et panneau ✓ menthe (titre caps, lignes séparées par des filets, note en italique), flèche entre les deux ; "
                                     "les lignes se font face, et les panneaux s'empilent quand un mot (une URL) ne tient pas dans une demi-largeur.",
    props=[
        Prop("before", "dict", "{title, items: [markdown…], note?} — l'existant.", required=True),
        Prop("after", "dict", "{title, items: [markdown…], note?} — la cible.", required=True),
        Prop("arrow", "bool", "Flèche → entre les panneaux (↓ quand ils s'empilent).", default=True),
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
    ls = theme.size("card_label")
    ops: list[dict] = []
    y = 0.0
    for row in _rows(pairs, cols):
        labels = [str(pr.get("label", "")).upper() for pr in row]
        values = [f"{pr.get('before', '')}  →  {pr.get('after', '')}" for pr in row]
        # one geometry per row; a label or a pair of values on two lines makes the whole row taller
        label_h = 14 + INSETS + (max(_wrapped_lines(t, cw, ls * CAPS_BOLD) for t in labels) - 1) * ls * LEADING
        values_h = 28 + INSETS + (max(_wrapped_lines(t, cw, 20 * BOLD_WRAP) for t in values) - 1) * 20 * LEADING
        for j, pr in enumerate(row):
            x = j * cw
            ops.append({"op": "text", "x": x, "y": y, "w": cw, "h": label_h, "text": labels[j],
                        "style": "card_label", "color": "muted", "role": "label"})
            runs = [[{"text": str(pr.get("before", "")), "color": "muted", "size": 20},
                     {"text": "  →  ", "color": "muted", "size": 14},
                     {"text": str(pr.get("after", "")), "bold": True, "color": "ink", "size": 20}]]
            ops.append({"op": "text", "x": x, "y": y + label_h - 4, "w": cw, "h": values_h, "runs": runs, "style": "kpi_value", "size": 20,
                        "role": "values"})
        y += label_h - 4 + values_h + 4
    return ops, h or y


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
    sw = [s if isinstance(s, dict) else {"color": s} for s in p["swatches"]]
    cols = int(p["cols"] or 1)
    cw = w / cols
    row_h = 30.0
    size = theme.size("label")  # the « Aa » sample is body text: 13 pt
    longest = max((len(str(s.get("sample") or p["sample"])) for s in sw), default=2)
    sw_w = max(44.0, longest * size * GLYPH_WRAP * BOLD_WRAP + 2 * INSET_X + 4)  # one swatch width for the whole palette
    ops: list[dict] = []
    for i, s in enumerate(sw):
        x, y = (i % cols) * cw, (i // cols) * row_h
        ops.append({"op": "box", "x": x, "y": y + 3, "w": sw_w, "h": 24, "fill": s["color"], "line": {"color": "rule", "weight": 0.75},
                    "text": str(s.get("sample") or p["sample"]), "style": "label", "size": size, "bold": True,
                    "color": s.get("text") or "ink", "align": "CENTER", "valign": "MIDDLE", "role": "swatch"})
        runs: list[list[dict]] = []
        if s.get("name"):
            runs.append([{"text": str(s["name"]), "bold": True}])
        if s.get("ratio"):
            runs.append([{"text": str(s["ratio"]), "color": "positive"}])
        if runs:
            ops.append({"op": "text", "x": x + sw_w + 6, "y": y + 1, "w": cw - sw_w - 6, "h": row_h - 2, "runs": runs, "style": "caption",
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
