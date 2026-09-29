"""Bilan média reporting blocks: analysis_block, source_note, stat_box, takeaways,
placeholder, ad_scoreboard, gallery, media_plan, timeline_arrow.

The blocks a media / analytics bilan repeats on every slide (« Notre
analyse », « * Sources : … »), the transposed ad results table with its
creative thumbnails, the campaign set-up recap and the milestone arrow. Empty
states are drawn (dashed frames « à déposer », placeholder panels) so a deck
generated before every asset is in stays presentable.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, get, register, shift, validate
from .builtin import INSET_X, INSETS, LEADING, PAD, _text_height, rendered_row_h

DASH = {"color": "divider", "weight": 1, "dash": "DASH"}


def _chevrons(items: list, w: float, size: float = 11.0, spacing: float = 6.0) -> tuple[dict, float]:
    """The ``chevrons`` component's single text op, for reuse inside other blocks."""
    spec = get("chevrons")
    ops, height = spec.render(validate(spec, {"items": [str(i) for i in items], "size": size, "spacing": spacing}), None, w, None)
    return ops[0], height


# --- analysis_block ------------------------------------------------------------------------

def _analysis_block(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    pad = float(PAD) if p["box"] else 0.0
    inner = w - 2 * pad
    size = float(p["size"])
    y = pad
    ops: list[dict] = []
    if p["title"]:
        ops.append({"op": "text", "x": pad, "y": y, "w": inner, "h": 14 + INSETS, "text": str(p["title"]), "style": "callout_title",
                    "role": "title"})
        y += 16 + INSETS
    if p["items"]:
        body, bh = _chevrons(p["items"], inner, size)
        body.update({"x": pad, "y": y, "role": "body"})
        ops.append(body)
        y += bh
    elif p["text"]:
        bh = (h - y - pad) if h else _text_height(p["text"], inner, size)
        ops.append({"op": "text", "x": pad, "y": y, "w": inner, "h": bh, "markdown": str(p["text"]), "style": "body", "size": size,
                    "role": "body"})
        y += bh
    height = h or (y + pad)
    if p["box"]:
        ops.insert(0, {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": None, "line": {"color": "accent", "weight": 1.5},
                       "role": "frame"})
    return ops, height


register(Component(
    name="analysis_block",
    description="Bloc « Notre analyse : » : titre en gras puis points en chevrons › (ou un paragraphe markdown), contour accent optionnel.",
    props=[
        Prop("title", "str", "Titre en gras.", default="Notre analyse :"),
        Prop("items", "list", "Points de l'analyse, un par ligne (chevrons ›)."),
        Prop("text", "markdown", "Paragraphe à la place des points (markdown)."),
        Prop("box", "bool", "Contour accent autour du bloc.", default=False),
        Prop("size", "number", "Taille du texte.", default=11),
    ],
    render=_analysis_block,
    example={"items": ["Google porte 77 % de la collecte déclarée par les régies et affiche le meilleur ROAS (3,90).",
                       "Écart de mesure important entre régie et GA4 : la comparaison N / N-1 est à lire avec prudence."]},
    tags=["texte"],
))


# --- source_note ---------------------------------------------------------------------------

def _source_note(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    text = str(p["text"]).strip()
    if not text.lower().startswith(("*", "source")):
        text = "* Sources : " + text
    align = p["align"]
    name = str(p["platform"] or "").strip()
    if name and name.lower() not in text.lower():
        text += " · " + name  # one line only: the platform joins the source text
    height = 12.0 + INSETS
    ops: list[dict] = []
    tx, tw = 0.0, w
    if p["logo"]:
        lw = 14.0
        need = len(text) * 4.4 + 2 * INSET_X
        lx = max(0.0, w - need - lw - 4) if align == "END" else 0.0
        ops.append({"op": "image", "x": lx, "y": 3, "w": lw, "h": lw, "asset": str(p["logo"]), "contain": True, "role": "logo",
                    **({"tint": p["tint"]} if p["tint"] else {})})
        tx, tw = lx + lw + 4, w - lx - lw - 4
    ops.append({"op": "text", "x": tx, "y": 0, "w": tw, "h": height, "text": text, "style": "caption", "size": 10,
                "italic": True, "align": align, "role": "source"})
    return ops, h or height


register(Component(
    name="source_note",
    description="Mention de source sur une ligne en petit italique (« * Sources : Google Ads du … au … »), alignée à droite, logo de la plateforme devant en option.",
    props=[
        Prop("text", "str", "Sources et période ; le préfixe « * Sources : » est ajouté s'il manque.", required=True),
        Prop("platform", "str", "Nom de la plateforme, ajouté en fin de ligne s'il n'est pas déjà dans le texte."),
        Prop("logo", "image", "Logo de la plateforme (asset) devant le nom."),
        Prop("align", "choice", "Alignement.", default="END", choices=["START", "CENTER", "END"]),
        Prop("tint", "color", "Teinte du logo (pictos blancs du dossier d'assets)."),
    ],
    render=_source_note,
    example={"text": "Google Ads du 01/12/2025 au 31/12/2025", "platform": "Google Ads"},
    tags=["texte"],
))


# --- stat_box ------------------------------------------------------------------------------

def _stat_box(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    boxes = list(p["boxes"])
    n = max(1, len(boxes))
    bw, bh = float(p["box_w"]), float(p["box_h"])
    op_w = 40.0
    total = n * bw + (n - 1) * op_w
    x = max(0.0, (w - total) / 2)
    ops: list[dict] = []
    for i, b in enumerate(boxes):
        ops.append({"op": "box", "x": x, "y": 0, "w": bw, "h": bh, "fill": None, "line": {"color": "accent", "weight": 1.5}, "role": "stat_box"})
        ops.append({"op": "text", "x": x, "y": bh / 2 - 30, "w": bw, "h": 30, "text": str(b.get("value", "")), "style": "kpi_value",
                    "size": 22, "align": "CENTER", "valign": "BOTTOM", "role": "value"})
        ops.append({"op": "text", "x": x + 4, "y": bh / 2, "w": bw - 8, "h": bh / 2 - 10, "text": str(b.get("label", "")),
                    "style": "label", "align": "CENTER", "role": "label"})  # 10 pt of air under the label
        x += bw
        if i < n - 1:
            ops.append({"op": "text", "x": x, "y": bh / 2 - 16, "w": op_w, "h": 32, "text": str(p["operator"]), "style": "label",
                        "size": 20, "bold": True, "align": "CENTER", "valign": "MIDDLE", "role": "operator"})
            x += op_w
    return ops, h or bh


register(Component(
    name="stat_box",
    description="Chiffres encadrés (contour accent, valeur en gros, libellé) reliés par un opérateur : « 63 % acceptation = 63 % des données remontées ».",
    props=[
        Prop("boxes", "list", "Boîtes : {value, label}.", required=True),
        Prop("operator", "str", "Signe entre les boîtes (=, →, ×, +).", default="="),
        Prop("box_w", "number", "Largeur d'une boîte.", default=130),
        Prop("box_h", "number", "Hauteur d'une boîte.", default=84),
    ],
    render=_stat_box,
    example={"boxes": [{"value": "63 %", "label": "Acceptation des cookies"}, {"value": "63 %", "label": "Des données sont remontées"}]},
    tags=["chiffres"],
))


# --- takeaways -----------------------------------------------------------------------------

def _takeaways(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    ops: list[dict] = []
    y = 0.0
    for it in p["items"]:
        title, text = (it.get("title"), it.get("text", "")) if isinstance(it, dict) else (None, str(it))
        if title:
            th = _text_height(title, w, 11.5)
            op: dict = {"op": "text", "x": 0, "y": y, "w": w, "h": th, "style": "card_title", "size": 11.5, "bold": True, "role": "title"}
            if p["highlight"]:
                op["markdown"] = f"=={title}=="
            else:
                op["text"] = str(title)
            ops.append(op)
            y += th - 4
        if text:
            bh = _text_height(text, w, 11)
            ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": bh, "markdown": str(text), "style": "body", "role": "body"})
            y += bh
        y += gap
    return ops, h or max(0.0, y - gap)


register(Component(
    name="takeaways",
    description="Enseignements / recos : titre en gras (surligné en option) et paragraphe par point, ou simples paragraphes.",
    props=[
        Prop("items", "list", "Points : {title, text} ou texte seul (markdown).", required=True),
        Prop("highlight", "bool", "Surligner les titres (marqueur accent).", default=False),
        Prop("gap", "number", "Espace entre les points.", default=10),
    ],
    render=_takeaways,
    example={"items": [{"title": "Sécuriser le budget des derniers jours", "text": "Les 7 derniers jours concentrent 52 % de la collecte GA4 : prévoir une réserve d'OI activable sur cette période."},
                       {"title": "Réévaluer le budget search", "text": "Environ 56 851 € de collecte potentielle perdue faute de budget (estimation haute)."}]},
    tags=["texte"],
))


# --- placeholder ---------------------------------------------------------------------------

def _placeholder(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    height = h or float(p["height"])
    line = dict(DASH) if p["dash"] else {"color": "divider", "weight": 1}
    return [{"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": "surface", "line": line, "text": str(p["text"]),
             "style": "caption", "size": 10.5, "color": "muted", "align": "CENTER", "valign": "MIDDLE", "role": "placeholder"}], height


register(Component(
    name="placeholder",
    description="Cadre gris clair à contour pointillé avec un message centré : la place d'un élément à venir (export en attente, capture à déposer).",
    props=[
        Prop("text", "str", "Message centré.", required=True),
        Prop("height", "number", "Hauteur du cadre.", default=120),
        Prop("dash", "bool", "Contour pointillé.", default=True),
    ],
    render=_placeholder, example={"text": "En attente des exports de dons des années précédentes (5 ans idéalement)"},
    tags=["texte"],
))


# --- ad_scoreboard -------------------------------------------------------------------------

def _ad_scoreboard(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ads = list(p["ads"])
    metrics = [str(m) for m in p["metrics"]]
    row_h = float(p["row_h"])
    img_h = float(p["image_h"])
    first_w = float(p["first_col_w"])
    n = max(1, len(ads))
    cw = (w - first_w) / n
    rows = [[str(p["name_label"])] + [str(a.get("name", "")) for a in ads],
            [str(p["image_label"])] + [""] * len(ads)]
    for m in metrics:
        rows.append([m] + [str((a.get("values") or {}).get(m, "")) for a in ads])
    size = float(p["size"])
    heights = [rendered_row_h(row_h, 10.5), img_h + 8] + [rendered_row_h(row_h, size)] * len(metrics)
    table: dict = {
        "op": "table", "x": 0, "y": 0, "w": w, "rows": rows, "col_w": [first_w] + [cw] * len(ads), "row_h": row_h, "row_heights": heights,
        "header": {"fill": "ink", "color": "on_dark", "bold": True}, "banding": ["background", "surface"], "first_col_bold": True,
        "borders": {"color": "rule", "weight": 1}, "align": [None] + ["CENTER"] * len(ads), "size": p["size"],
        "cell_fills": {(i, 0): "surface" for i in range(1, len(rows))},
    }
    ops: list[dict] = [table]
    y = heights[0] + 4
    for j, a in enumerate(ads):
        # every visual cell is an image slot: an empty one shows the dashed placeholder, and
        # replace_images can put next month's visual in without moving anything
        img = {"op": "image", "x": first_w + j * cw + 4, "y": y, "w": cw - 8, "h": img_h, "slot": True, "fit": "inside",
               "role": "slot"}
        if a.get("image"):
            img["asset"] = str(a["image"])
        elif a.get("image_url"):
            img["url"] = str(a["image_url"])
        ops.append(img)
    height = sum(heights)
    if p["top_note"]:
        ops.append({"op": "text", "x": w / 2, "y": height + 14, "w": w / 2, "h": 12 + INSETS, "text": str(p["top_note"]), "style": "caption",
                    "size": 10, "italic": True, "align": "END", "role": "top_note"})
        height += 14 + 12 + INSETS
    return ops, h or height


register(Component(
    name="ad_scoreboard",
    description="Résultats par publicité : tableau transposé, une colonne par annonce (nom en en-tête sombre, vignette dans un emplacement d'image : cadre pointillé tant qu'il est vide, visuel remplaçable ensuite par replace_images sans rien déplacer ; avec name, les emplacements sont <name>_slot_1…n), une ligne par métrique, première colonne grise en gras ; note « Top annonce » en italique.",
    props=[
        Prop("ads", "list", "Annonces : {name, image? (asset), image_url?, values: {métrique: valeur formatée}}.", required=True),
        Prop("metrics", "list", "Métriques affichées, dans l'ordre des lignes (Dépenses, CTR, Dons, CPA).", required=True),
        Prop("image_h", "number", "Hauteur de la ligne des vignettes.", default=56),
        Prop("row_h", "number", "Hauteur des autres lignes.", default=24),
        Prop("first_col_w", "number", "Largeur de la colonne des libellés.", default=76),
        Prop("name_label", "str", "Libellé de l'en-tête.", default="Nom visuel"),
        Prop("image_label", "str", "Libellé de la ligne des vignettes.", default="Visuel"),
        Prop("top_note", "str", "Note en italique sous le tableau (Top annonce : …)."),
        Prop("size", "number", "Taille de police des cellules.", default=9.5),
    ],
    render=_ad_scoreboard,
    example={"ads": [{"name": "Post vidéo", "values": {"Dépenses": "7 237,84 €", "CTR (clics)": "0,13 %", "Dons (régie)": "238", "CPA": "30,41 €"}},
                     {"name": "Post defisc", "values": {"Dépenses": "2 944,20 €", "CTR (clics)": "0,11 %", "Dons (régie)": "130", "CPA": "22,65 €"}},
                     {"name": "Carrousel defisc", "values": {"Dépenses": "224,50 €", "CTR (clics)": "0,14 %", "Dons (régie)": "16", "CPA": "14,03 €"}}],
             "metrics": ["Dépenses", "CTR (clics)", "Dons (régie)", "CPA"], "top_note": "Top annonce : Carrousel defisc"},
    tags=["données"],
))


# --- gallery -------------------------------------------------------------------------------

def _gallery(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = [it if isinstance(it, dict) or it is None else {"asset": str(it)} for it in p["images"]]
    cols = int(p["cols"] or len(items) or 1)
    gap = float(p["gap"])
    cw = (w - (cols - 1) * gap) / cols
    ch = cw / float(p["ratio"])
    cap_h = 14.0 + INSETS if p["captions"] else 0.0
    ops: list[dict] = []
    for i, it in enumerate(items):
        x = (i % cols) * (cw + gap)
        y = (i // cols) * (ch + cap_h + gap)
        if it and (it.get("asset") or it.get("url")):
            img = {"op": "image", "x": x, "y": y, "w": cw, "h": ch, "contain": True, "role": "image"}
            img.update({"asset": str(it["asset"])} if it.get("asset") else {"url": str(it["url"])})
            ops.append(img)
        else:
            ops.append({"op": "box", "x": x, "y": y, "w": cw, "h": ch, "fill": "surface", "line": dict(DASH), "text": str(p["placeholder_text"]),
                        "style": "caption", "size": 10, "color": "muted", "align": "CENTER", "valign": "MIDDLE", "role": "placeholder"})
        if p["captions"] and it and it.get("caption"):
            ops.append({"op": "text", "x": x, "y": y + ch + 2, "w": cw, "h": cap_h, "text": str(it["caption"]), "style": "caption",
                        "align": "CENTER", "role": "caption"})
    rows = -(-len(items) // cols) if items else 0
    return ops, h or (rows * (ch + cap_h + gap) - gap if rows else 0.0)


register(Component(
    name="gallery",
    description="Rangée(s) d'images à ratio fixe (captures d'annonces, visuels), légende optionnelle ; case vide = cadre pointillé « à déposer ».",
    props=[
        Prop("images", "list", "Images : nom d'asset, {asset | url, caption?}, ou null pour une case à remplir.", required=True),
        Prop("cols", "number", "Images par rangée (défaut : toutes)."),
        Prop("gap", "number", "Espace entre cases.", default=12),
        Prop("ratio", "number", "Largeur / hauteur d'une case (0,62 = portrait, 1 = carré, 1,78 = 16:9).", default=0.62),
        Prop("captions", "bool", "Légende sous chaque image.", default=False),
        Prop("placeholder_text", "str", "Texte des cases vides.", default="Capture de l'annonce\n(à déposer)"),
    ],
    render=_gallery, example={"images": [None, None, None, None]},
    tags=["cartes"],
))


# --- media_plan ----------------------------------------------------------------------------

def _media_plan(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    levers = list(p["levers"])
    obj = p["objective"]
    split = float(p["split"])
    left_w = (w * (1 - split) - 16) if obj else w
    ops: list[dict] = []
    y = 0.0
    ops.append({"op": "text", "x": 0, "y": y, "w": left_w, "h": 14 + INSETS, "text": str(p["heading"]), "style": "card_title",
                "size": 11, "role": "heading"})
    y += 26
    for lv in levers:
        name = str(lv.get("name", "")).upper()
        ops.append({"op": "box", "x": 0, "y": y + 4, "w": 10, "h": 10, "shape": "ELLIPSE", "fill": "accent", "role": "dot"})
        ops.append({"op": "text", "x": 16, "y": y - 3, "w": left_w - 16, "h": 14 + INSETS, "text": name, "style": "card_title",
                    "size": 11, "bold": True, "role": "lever"})
        lx = 16 + INSET_X + len(name) * 11 * 0.62 + 8
        for logo in lv.get("logos") or []:
            ops.append({"op": "image", "x": lx, "y": y, "w": 18, "h": 18, "asset": str(logo), "contain": True, "role": "logo",
                        **({"tint": p["tint"]} if p["tint"] else {})})
            lx += 22
        y += 22
        for label, key in ((p["budget_label"], "budget"), (p["dates_label"], "dates")):
            if lv.get(key):
                ops.append({"op": "text", "x": 16, "y": y, "w": left_w - 16, "h": 12 + INSETS,
                            "runs": [[{"text": str(label)}, {"text": str(lv[key]), "bold": True}]], "style": "body",
                            "role": "detail"})
                y += 16
        y += 12
    left_h = y
    if not obj:
        return ops, h or left_h
    px = w * (1 - split)
    pw = w * split
    items = list(obj.get("items") or [])
    oy = 24.0
    pad = 16.0
    obj_ops: list[dict] = [{"op": "text", "x": px + pad, "y": pad, "w": pw - 2 * pad, "h": 12 + INSETS, "text": "\u2009".join(str(p["objective_eyebrow"]).upper()),
                            "style": "card_label", "size": 9.5, "small_ok": True, "bold": True, "color": "ink", "role": "objective_eyebrow"},
                           {"op": "text", "x": px + pad, "y": pad + 18, "w": pw - 2 * pad, "h": _text_height(str(obj.get("title", "")), pw - 2 * pad, 15),
                            "style": "card_title", "size": 15, "bold": True, "color": "ink", "text": str(obj.get("title", "")), "role": "objective_title"}]
    oy = pad + 18 + obj_ops[1]["h"] + 2
    if items:
        chev, ch = _chevrons(items, pw - 2 * pad, 11)
        chev.update({"x": px + pad, "y": oy, "color": "ink", "role": "objective_items"})
        chev["runs"] = [[{**r[0], "color": "ink"}, r[1]] for r in chev["runs"]]
        obj_ops.append(chev)
        oy += ch
    height = h or max(left_h, oy + pad, 120.0)
    ops.append({"op": "box", "x": px, "y": 0, "w": pw, "h": height, "shape": "ROUND_RECTANGLE", "fill": "accent", "role": "objective"})
    ops.extend(obj_ops)
    return ops, height


register(Component(
    name="media_plan",
    description="Rappel du dispositif : leviers déployés (pastille, nom en capitales, logos régies, ordre d'insertion, dates) et carte menthe arrondie « Objectif » avec ses points, dans le style content_card.",
    props=[
        Prop("levers", "list", "Leviers : {name, logos?: [asset], budget?, dates?}.", required=True),
        Prop("objective", "dict", "Panneau de droite (carte menthe) : {title, items}."),
        Prop("objective_eyebrow", "str", "Sur-titre tracké du panneau.", default="Objectif"),
        Prop("heading", "str", "Titre de la liste.", default="Leviers déployés"),
        Prop("budget_label", "str", "Libellé du budget.", default="Ordre d'insertion : "),
        Prop("dates_label", "str", "Libellé des dates.", default="Date : "),
        Prop("split", "number", "Part de la largeur prise par le panneau objectif.", default=0.45),
        Prop("tint", "color", "Teinte des logos du dossier d'assets (pictos blancs) ; vide = couleurs d'origine."),
    ],
    render=_media_plan,
    example={"levers": [{"name": "Search + Demand Gen", "logos": ["google", "search"], "budget": "16 000 € HT", "dates": "du 09/02/2026 au 08/03/2026"},
                        {"name": "Social", "logos": ["share"], "budget": "18 000 € HT", "dates": "du 09/02/2026 au 08/03/2026"}],
             "objective": {"title": "Générer des demandes de brochures qualifiées", "items": ["Développer le nombre de demandes de brochures", "Accroître la notoriété sur le legs"]},
             "tint": "ink"},
    tags=["cartes"],
))


# --- timeline_arrow ------------------------------------------------------------------------

_EVENT_STYLE = {
    "filled": {"fill": "accent", "line": None},
    "outline": {"fill": None, "line": {"color": "ink", "weight": 1}},
    "dashed": {"fill": None, "line": {"color": "ink", "weight": 1, "dash": "DASH"}},
}


def _timeline_arrow(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    events = list(p["events"])
    n = max(1, len(events))
    bw, bh = float(p["box_w"]), float(p["box_h"])
    conn = float(p["connector"])
    arrow_y = bh + conn
    span = w - 24  # room for the arrowhead
    ops: list[dict] = [{"op": "line", "x1": 0, "y1": arrow_y, "x2": w, "y2": arrow_y, "color": "accent", "weight": 8,
                        "end_arrow": "arrow", "role": "arrow"}]
    for i, ev in enumerate(events):
        above = ev.get("above") if ev.get("above") is not None else (i % 2 == 1 if p["alternate"] else True)
        style = _EVENT_STYLE.get(str(ev.get("style") or "dashed"), _EVENT_STYLE["dashed"])
        cx = span * (i + 0.5) / n
        x = min(max(0.0, cx - bw / 2), w - bw)
        y = 0.0 if above else arrow_y + conn
        ops.append({"op": "line", "x1": cx, "y1": bh if above else arrow_y, "x2": cx, "y2": arrow_y if above else y, "color": "ink",
                    "weight": 1, "role": "connector"})
        ops.append({"op": "box", "x": x, "y": y, "w": bw, "h": bh, "fill": style["fill"], "line": style["line"],
                    "runs": [[{"text": str(ev.get("date", "")), "bold": True}], [{"text": str(ev.get("text", ""))}]],
                    "style": "caption", "size": 10, "color": "ink", "align": "CENTER", "valign": "MIDDLE", "role": "event"})
    return ops, h or (2 * (bh + conn))


register(Component(
    name="timeline_arrow",
    description="Frise des temps forts : grosse flèche accent, boîtes datées alternées au-dessus et au-dessous reliées par un trait ; styles plein (accent), contour, pointillé.",
    props=[
        Prop("events", "list", "Événements : {date, text, style?: filled | outline | dashed, above?}.", required=True),
        Prop("box_w", "number", "Largeur d'une boîte.", default=120),
        Prop("box_h", "number", "Hauteur d'une boîte.", default=46),
        Prop("connector", "number", "Longueur du trait entre boîte et flèche.", default=28),
        Prop("alternate", "bool", "Alterner dessous / dessus (le premier en dessous).", default=True),
    ],
    render=_timeline_arrow,
    example={"events": [{"date": "11/04", "text": "Début de la campagne", "style": "filled"},
                        {"date": "07/05", "text": "Basculer MDD IR « don cancer »"},
                        {"date": "07/05", "text": "Ajout du widget « montant favoris »"},
                        {"date": "15/05", "text": "Bascule Meta sur MDD IR", "style": "outline"},
                        {"date": "27/05", "text": "Augmentation de l'OI si pic de recherche"}]},
    tags=["schémas"],
))
