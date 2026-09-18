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
from .builtin import INSETS, LEADING, PAD, _text_height


def _rows(items: list, cols: int) -> list[list]:
    return [items[i:i + cols] for i in range(0, len(items), cols)]


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

def _person(p: dict, w: float, h: float | None) -> tuple[list[dict], float]:
    s = float(p["photo_size"])
    top = p["layout"] == "top"
    tx = 0.0 if top else s + 12
    tw = w - tx
    ops: list[dict] = []
    if p.get("photo"):
        ops.append({"op": "image", "x": 0, "y": 0, "w": s, "h": s, "asset": str(p["photo"]), "cover": True, "role": "photo"})
    else:
        ops.append({"op": "box", "x": 0, "y": 0, "w": s, "h": s, "fill": "photo_bg", "role": "photo",
                    "text": "".join(part[:1] for part in str(p.get("name", "")).split()[:2]).upper(),
                    "style": "card_num", "color": "muted", "align": "CENTER", "valign": "MIDDLE"})
    y = s + 8 if top else -2.0
    ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": 14 + INSETS, "text": str(p.get("name", "")), "style": "card_title",
                "size": 11, "role": "name"})
    y += 18
    if p.get("role"):
        ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": 14 + INSETS, "text": str(p["role"]), "style": "card_label",
                    "size": 10, "color": "ink", "role": "role"})
        y += 16
    if p.get("bio"):
        bh = _text_height(str(p["bio"]), tw, 11)
        ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": bh, "markdown": str(p["bio"]), "style": "body", "size": 11})
        y += bh
    if p.get("contact"):
        ops.append({"op": "text", "x": tx, "y": y, "w": tw, "h": 14 + INSETS, "text": str(p["contact"]), "style": "caption", "size": 10})
        y += 16
    return ops, h or max(y, s)


def _person_card(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    return _person(p, w, h)


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
    ops: list[dict] = []
    y = 0.0
    for row in _rows(people, cols):
        row_h = h or max(_person({**base, **pe}, cw, None)[1] for pe in row)
        for j, pe in enumerate(row):
            sub, _ = _person({**base, **pe}, cw, row_h)
            ops.extend(shift(sub, j * (cw + gap), y))
        y += row_h + gap
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

def _logo_grid(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    cols = int(p["cols"] or len(items) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    inner = cw - 2 * PAD
    ops: list[dict] = []
    heights: list[float] = []
    cells: list[tuple[int, int, list[dict], float]] = []
    for i, it in enumerate(items):
        cell: list[dict] = []
        y = float(PAD)
        logo = _logo_op(it, PAD, y, 22, 22, p["tint"])
        nx = PAD + (28 if logo else 0)
        if logo:
            cell.append(logo)
        if it.get("name"):
            cell.append({"op": "text", "x": nx, "y": y, "w": inner - (nx - PAD), "h": 22, "text": str(it["name"]), "style": "card_title",
                         "size": 11, "valign": "MIDDLE", "role": "name"})
        y += 30
        if it.get("title"):
            th = _text_height(str(it["title"]), inner, 11)
            cell.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": th,
                         "runs": [[{"text": str(it["title"]), "bold": True, "highlight": p["highlight"]}]], "style": "label", "size": 11, "role": "title"})
            y += th
        if it.get("text"):
            th = _text_height(str(it["text"]), inner, 10)
            cell.append({"op": "text", "x": PAD, "y": y, "w": inner, "h": th, "markdown": str(it["text"]), "style": "caption", "size": 10, "color": "text"})
            y += th
        cells.append((i // cols, i % cols, cell, y + PAD))
    rows = -(-len(items) // cols) if items else 0
    row_hs = [h or max(c[3] for c in cells if c[0] == r) for r in range(rows)]
    y0 = 0.0
    tops: list[float] = []
    for r in range(rows):
        tops.append(y0)
        y0 += row_hs[r] + gap
    for r, c, cell, _ in cells:
        ops.extend(shift(cell, c * (cw + gap), tops[r]))
    height = y0 - gap if rows else 0.0
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
        ops.append({"op": "box", "x": x + 12, "y": y + ch - 20, "w": 6, "h": 6, "shape": "ELLIPSE", "fill": color, "role": "dot"})
        ops.append({"op": "text", "x": x + 22, "y": y + ch - 31, "w": cw - 30, "h": 18 + INSETS, "text": str(it.get("value", "")),
                    "style": "kpi_value", "size": 14, "role": "value"})
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
