"""Lot 4 asset-backed components: person_card, team_grid, logo_grid, logo_wall,
kpi_cards.

Photos and logos come from the Drive assets folder (``image`` props: asset
name or local path) or from a public URL (``logo_url``). Images placed with
``contain`` keep their aspect inside their cell when the resolver knows the
source size; a URL keeps the box as given.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register, shift
from .builtin import BOLD_WRAP, INSETS, LEADING, PAD, _text_height, _wrapped_lines, caps_centre


def _rows(items: list, cols: int) -> list[list]:
    return [items[i:i + cols] for i in range(0, len(items), cols)]


def _bold_h(text: str, w: float, size: float) -> float:
    """Box height of a bold text wrapped in ``w`` (bold glyphs run wider)."""
    return _wrapped_lines(text, w, size * BOLD_WRAP) * size * LEADING + INSETS


def _too_long(component: str, field: str, text: str) -> dict:
    """Note to the caller (insert_component's ``warnings``): the text cannot fit at the charter size."""
    t = " ".join(str(text).split())
    return {"op": "warning", "text": f"{component} : {field} « {t[:40] + '…' if len(t) > 40 else t} » trop long, raccourcir"}


def _row_heights(naturals: list[float], h: float | None, gap: float) -> tuple[list[float], bool]:
    """Heights of the rows of a grid: natural, or sharing a forced total ``h``.

    A row never goes under what its texts need (they keep the charter size
    rather than overlap); the flag says a forced ``h`` was too small.
    """
    if h is None or not naturals:
        return naturals, False
    share = (h - (len(naturals) - 1) * gap) / len(naturals)
    return [max(n, share) for n in naturals], any(n > share + 0.5 for n in naturals)


def _logo_op(item: dict, x: float, y: float, w: float, h: float, tint=None) -> dict | None:
    if item.get("logo"):
        op = {"op": "image", "x": x, "y": y, "w": w, "h": h, "asset": str(item["logo"]), "contain": True}
        if tint:
            op["tint"] = tint
        return op
    if item.get("logo_url"):
        return {"op": "image", "x": x, "y": y, "w": w, "h": h, "url": str(item["logo_url"])}
    return None


# --- person_card / team_grid -----------------------------------------------------------

def _person_geo(p: dict, theme: Theme, w: float) -> dict:
    """Box heights of a person's texts at the theme's sizes (0 = no such text)."""
    s = float(p["photo_size"])
    tw = w - (0.0 if p["layout"] == "top" else s + 12)
    return {
        "name": _bold_h(str(p.get("name", "")), tw, theme.size("card_title")),
        "role": _bold_h(str(p["role"]), tw, theme.size("card_label")) if p.get("role") else 0.0,
        "bio": _text_height(str(p["bio"]), tw, theme.size("body")) if p.get("bio") else 0.0,
        "contact": _text_height(str(p["contact"]), tw, theme.size("caption")) if p.get("contact") else 0.0,
    }


def _person(p: dict, theme: Theme, w: float, h: float | None, geo: dict | None = None) -> tuple[list[dict], float]:
    """One person; ``geo`` (box heights shared by a team_grid row) keeps the names, roles
    and bios of a row on the same lines."""
    s = float(p["photo_size"])
    top = p["layout"] == "top"
    tx = 0.0 if top else s + 12
    tw = w - tx
    geo = geo or _person_geo(p, theme, w)
    ops: list[dict] = []
    if p.get("photo"):
        ops.append({"op": "image", "x": 0, "y": 0, "w": s, "h": s, "asset": str(p["photo"]), "cover": True, "role": "photo"})
    else:
        ops.append({"op": "box", "x": 0, "y": 0, "w": s, "h": s, "fill": "photo_bg", "role": "photo",
                    "text": "".join(part[:1] for part in str(p.get("name", "")).split()[:2]).upper(),
                    "style": "card_num", "color": "muted", "align": "CENTER", "valign": "MIDDLE"})
    # the next box overlaps the bottom inset (and the descenders' room) of the one above
    y = s + 8 if top else -2.0
    ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": geo["name"], "text": str(p.get("name", "")), "style": "card_title",
                "role": "name"})
    y += geo["name"] - 4
    if geo["role"]:
        if p.get("role"):
            ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": geo["role"], "text": str(p["role"]), "style": "card_label",
                        "color": "ink", "role": "role"})
        y += geo["role"] - 5.5
    if geo["bio"]:
        if p.get("bio"):
            ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": geo["bio"], "markdown": str(p["bio"]), "style": "body", "role": "bio"})
        y += geo["bio"]
    if geo["contact"]:
        if p.get("contact"):
            ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": geo["contact"], "text": str(p["contact"]), "style": "caption",
                        "role": "contact"})
        y += geo["contact"] - 5.5
    natural = max(y, s)
    if h is not None and h < natural - 0.5:
        # the texts keep the charter size: the card keeps its natural height rather than overlap
        ops.append(_too_long("person_card", "bio" if p.get("bio") else "name", p.get("bio") or p.get("name", "")))
        return ops, natural
    return ops, h or natural


def _person_card(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    return _person(p, theme, w, h)


_PERSON_PROPS = [
    Prop("photo", "image", "Photo : nom d'un fichier du dossier d'assets Drive ou chemin local (recadrée en carré)."),
    Prop("name", "str", "Nom.", required=True),
    Prop("role", "str", "Fonction (petites capitales)."),
    Prop("bio", "markdown", "Bio ou rôle sur le projet."),
    Prop("contact", "str", "E-mail ou téléphone."),
    Prop("photo_size", "number", "Côté de la photo.", default=64),
    Prop("layout", "choice", "Photo à gauche ou au-dessus des textes.", default="side", choices=["side", "top"]),
]

register(Component(
    name="person_card", description="Fiche personne : photo carrée (ou initiales), nom, fonction, bio markdown, contact.",
    props=_PERSON_PROPS, render=_person_card,
    example={"name": "Aurélie M.", "role": "Directrice de clientèle", "bio": "Diplômée en marketing, elle coordonne le projet.", "contact": "aurelie@periscope.digital"},
    tags=["personnes"],
))


def _team_grid(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    people = list(p["people"])
    cols = int(p["cols"] or len(people) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    base = {"photo_size": p["photo_size"], "layout": p["layout"]}
    rows = [[{**base, **pe} for pe in row] for row in _rows(people, cols)]
    # one geometry per row: names, roles and bios of a row start on the same lines
    geos = [{k: max(_person_geo(pe, theme, cw)[k] for pe in row) for k in ("name", "role", "bio", "contact")} for row in rows]
    naturals = [_person(row[0], theme, cw, None, geo)[1] for row, geo in zip(rows, geos)]
    row_hs, short = _row_heights(naturals, h, gap)
    ops: list[dict] = []
    y = 0.0
    for row, geo, row_h in zip(rows, geos, row_hs):
        for j, pe in enumerate(row):
            sub, _ = _person(pe, theme, cw, row_h, geo)
            ops.extend(shift(sub, j * (cw + gap), y))
        y += row_h + gap
    if short:
        longest = max(people, key=lambda pe: len(str(pe.get("bio") or "")))
        ops.append(_too_long("team_grid", "bio", longest.get("bio") or longest.get("name", "")))
    return ops, y - gap if people else 0.0


register(Component(
    name="team_grid", description="Équipe : fiches personne (photo, nom, fonction, bio) en grille aux hauteurs égalisées.",
    props=[
        Prop("people", "list", "Personnes : {photo?, name, role?, bio?, contact?}.", required=True),
        Prop("cols", "number", "Fiches par rangée.", default=2),
        Prop("gap", "number", "Espace entre fiches.", default=16),
        Prop("photo_size", "number", "Côté des photos.", default=64),
        Prop("layout", "choice", "Photo à gauche ou au-dessus.", default="side", choices=["side", "top"]),
    ],
    render=_team_grid,
    example={"people": [{"name": "Arnaud M.", "role": "Directeur associé", "bio": "Supervision stratégique, garantie de la qualité des livrables."},
                        {"name": "Aurélie M.", "role": "Directrice de clientèle", "bio": "Pilote le projet et l'accompagnement."},
                        {"name": "Théo L.", "role": "UX/UI designer", "bio": "Maquettes, prototypes, tests utilisateurs."},
                        {"name": "Sébastien N.", "role": "Développeur web", "bio": "Intégration et développement WordPress."}]},
    tags=["personnes"],
))


# --- logo_grid / logo_wall ---------------------------------------------------------------

LOGO_GRID_LOGO = 22.0  # side of a logo_grid logo


def _logo_grid(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    cols = int(p["cols"] or len(items) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    inner = cw - 2 * PAD
    ns, ts, xs = theme.size("card_title"), theme.size("label"), theme.size("caption")
    # the name's first line is centred on the logo (capitals on its centre line), not its box
    name_dy = LOGO_GRID_LOGO / 2 - caps_centre(0, ns)
    ops: list[dict] = []
    tops: list[float] = []
    row_cells: list[list[list[dict]]] = []
    naturals: list[float] = []
    for row in _rows(items, cols):
        # one geometry per row: names, titles and texts of a row start on the same lines
        has_logo = [bool(it.get("logo") or it.get("logo_url")) for it in row]
        name_hs = [_bold_h(str(it["name"]), inner - (28 if lg else 0), ns) if it.get("name") else 0.0 for it, lg in zip(row, has_logo)]
        head = max(LOGO_GRID_LOGO + 8, name_dy + max(name_hs) + 4) if any(has_logo) or any(name_hs) else 0.0
        title_h = max(_bold_h(str(it["title"]), inner, ts) if it.get("title") else 0.0 for it in row)
        text_h = max(_text_height(str(it["text"]), inner, xs) if it.get("text") else 0.0 for it in row)
        cells = []
        for it, lg, nh in zip(row, has_logo, name_hs):
            cell: list[dict] = []
            y = float(PAD)
            logo = _logo_op(it, PAD, y, LOGO_GRID_LOGO, LOGO_GRID_LOGO, p["tint"])
            nx = PAD + (28 if logo else 0)
            if logo:
                cell.append(logo)
            if it.get("name"):
                cell.append({"op": "text", "x": nx, "y": y + name_dy, "w": inner - (nx - PAD), "h": nh, "text": str(it["name"]),
                             "style": "card_title", "role": "name"})
            y += head
            if it.get("title"):
                cell.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": title_h,
                             "runs": [[{"text": str(it["title"]), "bold": True, "highlight": p["highlight"]}]], "style": "label", "role": "title"})
            y += title_h
            if it.get("text"):
                cell.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": text_h, "markdown": str(it["text"]), "style": "caption",
                             "color": "text", "role": "text"})
            cells.append(cell)
        row_cells.append(cells)
        naturals.append(PAD + head + title_h + text_h + PAD)
    row_hs, short = _row_heights(naturals, h, gap)
    y0 = 0.0
    for cells, rh in zip(row_cells, row_hs):
        tops.append(y0)
        for c, cell in enumerate(cells):
            ops.extend(shift(cell, c * (cw + gap), y0))
        y0 += rh + gap
    rows = len(row_cells)
    height = y0 - gap if rows else 0.0
    if short:
        longest = max(items, key=lambda it: len(str(it.get("text") or it.get("title") or "")))
        ops.append(_too_long("logo_grid", "text", longest.get("text") or longest.get("title") or longest.get("name", "")))
    if p["dividers"]:
        for c in range(1, cols):
            x = c * (cw + gap) - gap / 2
            ops.append({"op": "line", "x1": x, "y1": 0, "x2": x, "y2": height, "color": "divider", "weight": 0.75, "dash": "DASH", "role": "divider"})
        for r in range(1, rows):
            y = tops[r] - gap / 2
            ops.append({"op": "line", "x1": 0, "y1": y, "x2": w, "y2": y, "color": "divider", "weight": 0.75, "dash": "DASH", "role": "divider"})
    return ops, height


register(Component(
    name="logo_grid", description="Grille d'outils / partenaires : logo + nom, titre surligné, texte ; séparateurs pointillés.",
    props=[
        Prop("items", "list", "Cases : {logo? (asset), logo_url?, name?, title?, text?}.", required=True),
        Prop("cols", "number", "Cases par rangée.", default=3),
        Prop("gap", "number", "Espace entre cases.", default=12),
        Prop("dividers", "bool", "Séparateurs pointillés entre cases.", default=True),
        Prop("highlight", "color", "Couleur du surlignage des titres.", default="highlight"),
        Prop("tint", "color", "Teinte appliquée aux logos du dossier d'assets (pictos blancs) ; vide = couleurs d'origine."),
    ],
    render=_logo_grid,
    example={"items": [{"logo": "google", "name": "Google Drive", "title": "Pour le stockage des documents", "text": "Stockage sécurisé, droits adaptés selon les livrables."},
                       {"logo": "video", "name": "Loom", "title": "Pour la recette du site", "text": "Gestion des sprints et des tickets."},
                       {"logo": "share", "name": "Slack", "title": "Pour l'échange au quotidien", "text": "Conservation des échanges et des comptes rendus."}],
             "tint": "ink"},
    tags=["cartes"],
))


def _logo_wall(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    logos = [lg if isinstance(lg, dict) else {"logo": str(lg)} for lg in p["logos"]]
    cols = int(p["cols"] or len(logos) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    cell_h = float(p["cell_h"])
    lh = min(float(p["logo_h"]), cell_h)
    lw = cw * 0.8
    ops: list[dict] = []
    for i, lg in enumerate(logos):
        x = (i % cols) * (cw + gap) + (cw - lw) / 2
        y = (i // cols) * (cell_h + gap) + (cell_h - lh) / 2
        op = _logo_op(lg, x, y, lw, lh, p["tint"])
        if op is None:
            raise ValueError("logo_wall: each logo needs 'logo' (asset) or 'logo_url'")
        ops.append(op)
        if lg.get("name") and p["names"]:
            ops.append({"op": "text", "x": x - lw * 0.1, "y": y + lh, "w": lw * 1.2, "h": 14 + INSETS, "text": str(lg["name"]),
                        "style": "caption", "size": 10, "color": "on_dark" if p["dark"] else "muted", "align": "CENTER"})
    rows = -(-len(logos) // cols) if logos else 0
    return ops, h or (rows * (cell_h + gap) - gap if rows else 0.0)


register(Component(
    name="logo_wall", description="Mur de logos (clients, références) en grille, chaque logo ajusté dans sa case en gardant son ratio.",
    props=[
        Prop("logos", "list", "Logos : nom d'asset, ou {logo?, logo_url?, name?}.", required=True),
        Prop("cols", "number", "Logos par rangée.", default=5),
        Prop("gap", "number", "Espace entre cases.", default=12),
        Prop("logo_h", "number", "Hauteur max d'un logo.", default=28),
        Prop("cell_h", "number", "Hauteur d'une case.", default=56),
        Prop("names", "bool", "Afficher le nom sous chaque logo.", default=False),
        Prop("dark", "bool", "Noms en clair (fond sombre).", default=False),
        Prop("tint", "color", "Teinte appliquée aux logos du dossier d'assets (pictos blancs) ; vide = couleurs d'origine."),
    ],
    render=_logo_wall,
    example={"logos": ["google", "star", "megaphone", "video", "share"], "cols": 5, "tint": "ink"},
    tags=["cartes"],
))


# --- kpi_cards --------------------------------------------------------------------------

KPI_CARD_VALUE = 14.0  # the value of a kpi card (over its 10 pt label)


def _kpi_cards(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    cols = int(p["cols"] or len(items) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    ch = float(p["card_h"])
    ops: list[dict] = []
    for i, it in enumerate(items):
        x = (i % cols) * (cw + gap)
        y = (i // cols) * (ch + gap)
        ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": ch, "shape": "ROUND_RECTANGLE", "fill": "background",
                    "line": {"color": "rule", "weight": 1}, "role": "card"})
        lx = x + 10
        if it.get("icon"):
            ops.append({"op": "image", "x": x + 10, "y": y + 9, "w": 12, "h": 12, "asset": str(it["icon"]),
                        **({"tint": p["icon_tint"]} if p["icon_tint"] else {})})
            lx = x + 26
        ops.append({"op": "text", "x": lx, "y": y + 4, "w": cw - (lx - x) - 54, "h": 14 + INSETS, "text": str(it.get("label", "")),
                    "style": "card_label", "size": 10, "color": "muted", "role": "label"})
        if it.get("delta"):
            d = str(it["delta"]).strip()
            up = d.startswith("+")
            ops.append({"op": "text", "x": x + cw - 60, "y": y + 4, "w": 52, "h": 14 + INSETS, "text": d + ("  ▲" if up else "  ▼"),
                        "style": "kpi_delta", "size": 10, "color": "positive" if up else "negative", "align": "END", "role": "delta"})
        color = it.get("color") or f"series_{i % 6 + 1}"
        vy = y + ch - 31
        # the series dot is centred on the value's capitals (digits are cap height), not on its box
        ops.append({"op": "box", "x": x + 12, "y": caps_centre(vy, KPI_CARD_VALUE) - 3, "w": 6, "h": 6, "shape": "ELLIPSE", "fill": color,
                    "role": "dot"})
        ops.append({"op": "text", "x": x + 22, "y": vy, "w": cw - 30, "h": KPI_CARD_VALUE * LEADING + INSETS, "text": str(it.get("value", "")),
                    "style": "kpi_value", "size": KPI_CARD_VALUE, "role": "value"})
    rows = -(-len(items) // cols) if items else 0
    return ops, h or (rows * (ch + gap) - gap if rows else 0.0)


register(Component(
    name="kpi_cards", description="Cartes KPI bordées : picto + libellé, delta ▲/▼ coloré à droite, point de série + valeur.",
    props=[
        Prop("items", "list", "Cartes : {label, value, delta?, icon?, color?}.", required=True),
        Prop("cols", "number", "Cartes par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cartes.", default=10),
        Prop("card_h", "number", "Hauteur d'une carte.", default=54),
        Prop("icon_tint", "color", "Teinte des pictos (rôle) ; vide = couleurs d'origine."),
    ],
    render=_kpi_cards,
    example={"items": [{"label": "ChatGPT", "value": "11 454", "delta": "+12 %"}, {"label": "Perplexity", "value": "5 950", "delta": "+5 %"},
                       {"label": "Claude Bot", "value": "4 391", "delta": "-3 %"}, {"label": "Copilot", "value": "3 504", "delta": "+8 %"}]},
    tags=["chiffres"],
))
