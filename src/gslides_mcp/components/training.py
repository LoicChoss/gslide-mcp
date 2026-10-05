"""Teaching and audit diagrams: semantic cocoon, persona card and sheet, cycle, formula.

Charter grounds only: light discs and boxes, colour on the hub, the numbers and the
arrows; navy is reserved for « action » nodes and the result header.
"""

from __future__ import annotations

import math

from ..themes import Theme
from . import Component, Prop, register
from .builtin import INSET_X, INSETS, LEADING, PAD, _text_height, _wrapped_lines, fit_text_size

# --- cocon ------------------------------------------------------------------------------


def _as_nodes(items) -> list[dict]:
    return [it if isinstance(it, dict) else {"label": str(it)} for it in (items or [])]


def _disc(cx: float, cy: float, d: float, fill: str, color: str, label: str, size: float, role: str) -> dict:
    return {"op": "box", "x": cx - d / 2, "y": cy - d / 2, "w": d, "h": d, "shape": "ELLIPSE", "fill": fill, "role": role,
            "text": label, "style": "caption", "size": size, "bold": True, "color": color, "align": "CENTER", "valign": "MIDDLE",
            "small_ok": size < 10}


def _disc_size(label: str, d: float, base: float = 10.0) -> float:
    """Text size for a label inside an ellipse of diameter d: Google writes in the inscribed
    rectangle (0.707 d) minus its 7.2 pt side insets, and breaks a word wider than that."""
    usable = 0.707 * d - 14.4
    size = fit_text_size(label, usable, base, max_lines=5, floor=7)
    longest = max((len(word) for word in label.split()), default=1)
    return max(7.0, min(size, usable / (longest * 0.58)))  # bold Barlow runs wider than the 0.485 wrap estimate


def _cocon(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    pages = _as_nodes(p["pages"])
    actions = _as_nodes(p["actions"])
    pd, cd, ad = float(p["page_d"]), float(p["center_d"]), float(p["action_d"])
    big = max(pd, cd, ad)
    radius = float(p["radius"]) if p["radius"] else max(80.0, ((h - big) / 2) if h else min(120.0, (w - pd) / 2.4))
    n, m = len(pages), len(actions)
    if p["layout"] == "ring":
        total = n + m
        angles = [90 + 360 * i / total for i in range(total)]  # math degrees, 90 = top, counter-clockwise
        page_angles, action_angles = angles[:n], angles[n:]
    else:  # pages on the left arc, actions on the right
        page_angles = [180.0] if n == 1 else [105 + 150 * i / (n - 1) for i in range(n)]
        action_angles = [-35.0] if m == 1 else [40 - 80 * i / (m - 1) for i in range(m)] if m else []
    if p["page_angles"]:  # explicit angles (degrees, 0 = right, 90 = top, 180 = left, -35 = lower right)
        page_angles = [float(a) for a in p["page_angles"]][:n] + page_angles[len(p["page_angles"]):]
    if p["action_angles"]:
        action_angles = [float(a) for a in p["action_angles"]][:m] + action_angles[len(p["action_angles"]):]
    text_color, link = p["text_color"], p["link_color"]

    def pos(angle: float, r: float) -> tuple[float, float]:
        a = math.radians(angle)
        return r * math.cos(a), -r * math.sin(a)

    # scale the radius down when the diagram is wider than the box
    for _ in range(3):
        pts = [(0.0, 0.0, cd)] + [(*pos(a, radius), pd) for a in page_angles] + [(*pos(a, radius), ad) for a in action_angles]
        x0 = min(x - d / 2 for x, _, d in pts)
        x1 = max(x + d / 2 for x, _, d in pts)
        if x1 - x0 <= w or radius <= 70:
            break
        radius = max(70.0, radius * w / (x1 - x0))
    y0 = min(y - d / 2 for _, y, d in pts)
    y1 = max(y + d / 2 for _, y, d in pts)
    ox = -x0 + (w - (x1 - x0)) / 2
    oy = -y0
    cx, cy = ox, oy
    lines: list[dict] = []
    discs: list[dict] = []
    for node, a in zip(pages, page_angles):
        x, y = pos(a, radius)
        lines.append({"op": "line", "x1": cx, "y1": cy, "x2": x + ox, "y2": y + oy, "color": link, "weight": 1, "role": "link"})
        label = str(node.get("label", ""))
        size = _disc_size(label, pd)
        discs.append(_disc(x + ox, y + oy, pd, node.get("fill") or "accent", node.get("color") or text_color, label, size, "page"))
    for node, a in zip(actions, action_angles):
        x, y = pos(a, radius)
        lines.append({"op": "line", "x1": cx, "y1": cy, "x2": x + ox, "y2": y + oy, "color": link, "weight": 1, "role": "link"})
        label = str(node.get("label", ""))
        size = _disc_size(label, ad)
        discs.append(_disc(x + ox, y + oy, ad, node.get("fill") or "ink", "on_dark", label, size, "action"))
    center = str(p["center"])
    hub = _disc(cx, cy, cd, p["center_fill"], text_color, center, _disc_size(center, cd), "center")
    return lines + discs + [hub], h or (y1 - y0)


register(Component(
    name="cocon",
    description="Cocon sémantique sur une demi-page : page cible au centre (disque cyan), pages filles en disques menthe reliées par des filets, nœuds « actions » en navy à droite ; en arc (pages à gauche, angles réglables) ou en anneau ; texte navy ou blanc.",
    props=[
        Prop("center", "str", "Page cible (texte du disque central).", required=True),
        Prop("pages", "list", "Pages filles : texte ou {label, fill?}.", required=True),
        Prop("actions", "list", "Nœuds d'action ou de conversion (navy, texte clair) : texte ou {label, fill?}.", default=[]),
        Prop("layout", "choice", "arc : pages sur l'arc gauche, actions à droite ; ring : tout autour du centre.", default="arc", choices=["arc", "ring"]),
        Prop("radius", "number", "Distance centre → disques (défaut : d'après la hauteur ou la largeur, 120 au plus ; réduite si trop large)."),
        Prop("page_angles", "list", "Angles des pages en degrés (0 = droite, 90 = haut, 180 = gauche, 270 ou -90 = bas), un par page ; défaut : répartis sur l'arc gauche.", default=[]),
        Prop("action_angles", "list", "Angles des nœuds d'action ; défaut : à droite.", default=[]),
        Prop("text_color", "color", "Couleur du texte des pages et du centre (ink, ou background pour du blanc).", default="ink"),
        Prop("link_color", "color", "Couleur des filets.", default="muted"),
        Prop("page_d", "number", "Diamètre des pages.", default=104),
        Prop("center_d", "number", "Diamètre du centre.", default=84),
        Prop("action_d", "number", "Diamètre des nœuds d'action (un mot de 9 lettres et plus demande 70 pt et plus, le texte ne descend pas sous 7 pt).", default=80),
        Prop("center_fill", "color", "Couleur du centre.", default="cyan"),
    ],
    render=_cocon,
    example={"center": "Aide alimentaire", "pages": ["Comment organiser une collecte alimentaire ?", "Réglementation autour du don d'invendus alimentaires",
                                                     "Bénéficiaires du don d'invendus alimentaires"], "actions": ["Nos actions"]},
    tags=["schémas"],
))


# --- cycle ------------------------------------------------------------------------------


def _clip(x1: float, y1: float, x2: float, y2: float, bw: float, bh: float) -> tuple[float, float, float, float]:
    """Shorten the segment between two box centres to the boxes' edges."""
    dx, dy = x2 - x1, y2 - y1
    tx = (bw / 2) / abs(dx) if dx else math.inf
    ty = (bh / 2) / abs(dy) if dy else math.inf
    t = min(tx, ty)
    return x1 + dx * t, y1 + dy * t, x2 - dx * t, y2 - dy * t


def _cycle(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    steps = _as_nodes(p["steps"])
    n = max(2, len(steps))
    gap = float(p["gap"])
    bw = min(float(p["box_w"]), (w - gap) / 2)
    texts = []
    bh = 0.0
    for s in steps:
        title = str(s.get("title", ""))
        text = str(s.get("text") or "")
        th = _text_height(title, bw - 2 * PAD, 11)
        xh = _text_height(text, bw - 2 * PAD, 10) if text else 0
        texts.append((title, text, th, xh))
        bh = max(bh, th + xh + 2 * PAD - 4)
    if n == 4:  # 2 × 2, read clockwise from the top left
        cols = [0, 1, 1, 0]
        rows = [0, 0, 1, 1]
        x_left = (w - (2 * bw + gap)) / 2
        centers = [(x_left + c * (bw + gap) + bw / 2, r * (bh + gap) + bh / 2) for c, r in zip(cols, rows)]
        height = 2 * bh + gap
    else:
        height = h or max(2 * bh + 2 * gap + 40, 240.0)
        rx = min((w - bw) / 2, 0.45 * w)
        ry = (height - bh) / 2
        centers = [(w / 2 + rx * math.cos(math.radians(-90 + 360 * i / n)), height / 2 + ry * math.sin(math.radians(-90 + 360 * i / n)))
                   for i in range(n)]
    ops: list[dict] = []
    for i, ((cx, cy), (title, text, th, xh)) in enumerate(zip(centers, texts)):
        x, y = cx - bw / 2, cy - bh / 2
        ops.append({"op": "box", "x": x, "y": y, "w": bw, "h": bh, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "step"})
        ops.append({"op": "box", "x": x, "y": y + 10, "w": 4, "h": bh - 20, "fill": "accent", "role": "step_bar"})
        ops.append({"op": "text", "x": x + PAD - 4, "y": y + PAD - 6, "w": bw - 2 * PAD + 4, "h": th, "text": title, "style": "card_title",
                    "size": 11, "bold": True, "color": "ink", "role": "step_title"})
        if text:
            ops.append({"op": "text", "x": x + PAD - 4, "y": y + PAD - 8 + th, "w": bw - 2 * PAD + 4, "h": xh, "markdown": text, "style": "caption",
                        "size": 10, "color": "text", "role": "step_text"})
    arrows: list[dict] = []
    for i in range(n):
        (x1, y1), (x2, y2) = centers[i], centers[(i + 1) % n]
        ax1, ay1, ax2, ay2 = _clip(x1, y1, x2, y2, bw + 6, bh + 6)
        arrows.append({"op": "line", "x1": ax1, "y1": ay1, "x2": ax2, "y2": ay2, "color": "accent", "weight": 2.5, "end_arrow": "arrow", "role": "arrow"})
    return ops + arrows, h or height


register(Component(
    name="cycle",
    description="Boucle d'étapes : boîtes claires à barre menthe reliées par des flèches, en carré (4 étapes, sens horaire depuis le haut à gauche) ou en anneau (3, 5, 6 étapes).",
    props=[
        Prop("steps", "list", "Étapes dans l'ordre de la boucle : {title, text?} ou texte.", required=True),
        Prop("box_w", "number", "Largeur max d'une boîte.", default=240),
        Prop("gap", "number", "Espace entre boîtes (et longueur des flèches).", default=60),
    ],
    render=_cycle,
    example={"steps": [{"title": "Off market", "text": "Univers de requêtes à pouvoir de reconnaissance marque fort : « comment choisir son casque de moto ? »"},
                       {"title": "Pre purchase", "text": "Requêtes transactionnelles : « casque jet », « casque modulable »"},
                       {"title": "Purchase", "text": "Requêtes à pouvoir transactionnel très fort : « achat casque de moto », « casque shoei pas cher »"},
                       {"title": "Usage", "text": "Requêtes de recommandation : « avis casque shoei », « avis casque intégral shark »"}]},
    tags=["schémas"],
))


# --- formula ----------------------------------------------------------------------------


def _formula(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = _as_nodes(p["items"])
    n = max(2, len(items))
    op_w = 30.0
    bw = (w - (n - 1) * op_w) / n
    head_h = 34.0
    ops: list[dict] = []
    texts = []
    body_h = 0.0
    for it in items:
        text = str(it.get("text") or "")
        th = _text_height(text, bw - 2 * PAD + 4, 10) if text else 0
        texts.append((it, text, th))
        body_h = max(body_h, th + 10 if text else 0)
    for i, (it, text, th) in enumerate(texts):
        x = i * (bw + op_w)
        num = str(it.get("num") or i + 1)
        ops.append({"op": "box", "x": x, "y": 0, "w": bw, "h": head_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "head"})
        ops.append({"op": "box", "x": x, "y": 0, "w": head_h, "h": head_h, "shape": "ROUND_RECTANGLE", "fill": "accent", "role": "num",
                    "text": num, "style": "badge", "size": 12, "bold": True, "color": "ink", "align": "CENTER", "valign": "MIDDLE"})
        title = str(it.get("title", ""))
        ops.append({"op": "text", "x": x + head_h + 2, "y": 0, "w": bw - head_h - 4, "h": head_h, "text": title, "style": "card_title",
                    "size": fit_text_size(title, bw - head_h - 20, 11, max_lines=2, floor=8.5), "bold": True, "color": "ink", "valign": "MIDDLE",
                    "small_ok": True, "role": "title"})
        if text:
            ops.append({"op": "box", "x": x, "y": head_h + 4, "w": bw, "h": body_h, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "body"})
            ops.append({"op": "text", "x": x + 6, "y": head_h + 8, "w": bw - 12, "h": th, "markdown": text, "style": "caption", "size": 10,
                        "color": "text", "align": "CENTER", "role": "text"})
        if i < n - 1:
            ops.append({"op": "text", "x": x + bw, "y": 0, "w": op_w, "h": head_h, "text": str(p["operator"]), "style": "kpi_value", "size": 20,
                        "bold": True, "color": "accent_dark", "align": "CENTER", "valign": "MIDDLE", "role": "operator"})
    y = head_h + (body_h + 4 if body_h else 0) + 6
    ops.append({"op": "text", "x": 0, "y": y, "w": w, "h": 26, "text": "=", "style": "kpi_value", "size": 22, "bold": True, "color": "accent_dark",
                "align": "CENTER", "valign": "MIDDLE", "role": "equals"})
    y += 30
    res = p["result"] if isinstance(p["result"], dict) else {"title": str(p["result"])}
    rw = min(float(p["result_w"]), w)
    rx = (w - rw) / 2
    ops.append({"op": "box", "x": rx, "y": y, "w": rw, "h": head_h, "shape": "ROUND_RECTANGLE", "fill": "ink", "role": "result_head",
                "text": str(res.get("title", "")), "style": "card_title", "size": 11, "bold": True, "color": "on_dark", "align": "CENTER", "valign": "MIDDLE"})
    y += head_h
    rtext = str(res.get("text") or "")
    if rtext:
        rh = _text_height(rtext, rw - 12, 10) + 10
        ops.append({"op": "box", "x": rx, "y": y + 4, "w": rw, "h": rh, "shape": "ROUND_RECTANGLE", "fill": "surface", "role": "result_body"})
        ops.append({"op": "text", "x": rx + 6, "y": y + 8, "w": rw - 12, "h": rh - 8, "markdown": rtext, "style": "caption", "size": 10,
                    "color": "text", "align": "CENTER", "role": "result_text"})
        y += rh + 4
    return ops, h or y


register(Component(
    name="formula",
    description="Formule de concepts : 2 à 5 boîtes numérotées (titre + explication) reliées par un opérateur, puis « = » et la boîte résultat (en-tête navy).",
    props=[
        Prop("items", "list", "Opérandes : {num?, title, text?} (2 à 5).", required=True),
        Prop("result", "dict", "Résultat : {title, text?} ou texte.", required=True),
        Prop("operator", "str", "Signe entre les opérandes (+, ×, →).", default="+"),
        Prop("result_w", "number", "Largeur de la boîte résultat.", default=300),
    ],
    render=_formula,
    example={"items": [{"title": "Résultats personnalisés", "text": "Selon l'historique des recherches"}, {"title": "Géolocalisation", "text": "Résultats adaptés selon la localité de l'IP"},
                       {"title": "Recherche universelle", "text": "Images, vidéos, actualités, IA : la SERP n'est plus dix liens bleus"}],
             "result": {"title": "Moins de fiabilité", "text": "Les positions retournées sont de moins en moins fiables : le ranking seul ne suffit plus"}},
    tags=["schémas"],
))


# --- persona_card -----------------------------------------------------------------------


def _persona_card(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ops: list[dict] = []
    pad = PAD + 2
    left_w = w * 0.55 - pad
    rx = pad + left_w + pad  # right column x
    right_w = w - rx - pad
    y = pad
    # identity
    photo_d = 56.0
    if p["photo"]:
        ops.append({"op": "image", "x": pad, "y": y, "w": photo_d, "h": photo_d, "asset": str(p["photo"]), "cover": True, "role": "photo"})
    else:
        ops.append({"op": "box", "x": pad, "y": y, "w": photo_d, "h": photo_d, "shape": "ELLIPSE", "fill": "surface", "role": "photo",
                    "text": "".join(part[0] for part in str(p["name"]).split()[:2]).upper(), "style": "card_title", "size": 16, "bold": True,
                    "color": "ink", "align": "CENTER", "valign": "MIDDLE"})
    tx = pad + photo_d + 12
    name = str(p["name"]) + (f" – {p['age']}" if p["age"] else "")
    ops.append({"op": "text", "x": tx, "y": y, "w": left_w - photo_d - 12, "h": 22 + INSETS, "text": name, "style": "card_title", "size": 15,
                "bold": True, "color": "ink", "role": "name"})
    if p["location"]:
        ops.append({"op": "text", "x": tx, "y": y + 26, "w": left_w - photo_d - 12, "h": 14 + INSETS, "text": "◎ " + str(p["location"]),
                    "style": "caption", "size": 10, "color": "muted", "italic": True, "role": "location"})
    y += photo_d + 12
    # context
    if p["context"]:
        ops.append({"op": "text", "x": pad, "y": y, "w": left_w, "h": 12 + INSETS, "text": str(p["context_label"]), "style": "card_label", "size": 10,
                    "bold": True, "color": "ink", "role": "context_label"})
        ch = _text_height(str(p["context"]), left_w, 10)
        ops.append({"op": "text", "x": pad, "y": y + 16, "w": left_w, "h": ch, "markdown": str(p["context"]), "style": "caption", "size": 10,
                    "color": "text", "role": "context"})
        y += 16 + ch + 8
    # brands
    brands = list(p["brands"] or [])
    if brands:
        ops.append({"op": "text", "x": pad, "y": y, "w": left_w, "h": 12 + INSETS, "text": str(p["brands_label"]), "style": "card_label", "size": 10,
                    "bold": True, "color": "ink", "role": "brands_label"})
        bx = pad
        for b in brands:
            ops.append({"op": "image", "x": bx, "y": y + 18, "w": 56, "h": 28, "asset": str(b), "contain": True, "role": "brand"})
            bx += 64
        y += 18 + 28 + 8
    left_bottom = y
    # right column: gauges and devices
    ry = pad
    for g in p["gauges"] or []:
        g = g if isinstance(g, dict) else {"label": str(g), "value": 0.5}
        v = max(0.0, min(1.0, float(g.get("value", 0.5))))
        ops.append({"op": "text", "x": rx, "y": ry, "w": right_w, "h": 12 + INSETS, "text": str(g.get("label", "")), "style": "card_label", "size": 10,
                    "bold": True, "color": "ink", "role": "gauge_label"})
        ops.append({"op": "box", "x": rx, "y": ry + 18, "w": right_w, "h": 7, "fill": "surface", "role": "gauge_track"})
        ops.append({"op": "box", "x": rx, "y": ry + 18, "w": max(4.0, right_w * v), "h": 7, "fill": "accent", "role": "gauge"})
        ry += 32
    devices = p["devices"] or []
    if devices:
        ops.append({"op": "text", "x": rx, "y": ry, "w": right_w, "h": 12 + INSETS, "text": str(p["devices_label"]), "style": "card_label", "size": 10,
                    "bold": True, "color": "ink", "role": "devices_label"})
        dx = rx
        for d in devices:
            d = d if isinstance(d, dict) else {"label": str(d), "on": True}
            on = bool(d.get("on", True))
            label = str(d.get("label", ""))
            dw = max(52.0, 18 + len(label) * 5.8)  # Google's 14.4 pt of side insets plus the label
            ops.append({"op": "box", "x": dx, "y": ry + 18, "w": dw, "h": 22, "shape": "ROUND_RECTANGLE", "fill": "cyan" if on else "surface",
                        "role": "device", "text": label, "style": "badge", "size": 8.5, "small_ok": True, "bold": True,
                        "color": "ink" if on else "muted", "align": "CENTER", "valign": "MIDDLE"})
            dx += dw + 6
        ry += 18 + 24 + 8
    y = max(left_bottom, ry)
    # expectations / brakes
    exp, brk = list(p["expectations"] or []), list(p["brakes"] or [])
    if exp or brk:
        ops.append({"op": "line", "x1": pad, "y1": y, "x2": w - pad, "y2": y, "color": "accent", "weight": 2, "role": "rule"})
        y += 8
        col_w = (w - 2 * pad - 12) / 2
        bottom = y
        for k, (label, items) in enumerate(((p["expectations_label"], exp), (p["brakes_label"], brk))):
            if not items:
                continue
            x = pad + k * (col_w + 12)
            md = "\n".join(f"- {it}" for it in items)
            th = _text_height(md, col_w, 10)
            ops.append({"op": "text", "x": x, "y": y, "w": col_w, "h": 12 + INSETS, "text": str(label), "style": "card_label", "size": 10, "bold": True,
                        "color": "ink", "role": "list_label"})
            ops.append({"op": "text", "x": x, "y": y + 16, "w": col_w, "h": th, "markdown": md, "style": "caption", "size": 10, "color": "text", "role": "list"})
            bottom = max(bottom, y + 16 + th)
        y = bottom
    if p["tag"]:
        y += 40  # its own band under the lists, so it never covers them
    height = h or (y + pad)
    if p["tag"]:  # inside the card's rounded corner, rounded itself
        tw = min(150.0, w * 0.3)
        ops.append({"op": "box", "x": w - tw - 12, "y": height - 32 - 12, "w": tw, "h": 32, "shape": "ROUND_RECTANGLE", "fill": "cyan", "role": "tag",
                    "text": str(p["tag"]), "style": "card_title", "size": 11, "bold": True, "color": "ink", "align": "CENTER", "valign": "MIDDLE"})
    frame = {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": "background", "line": {"color": "rule", "weight": 1},
             "role": "card"}
    return [frame] + ops, height


register(Component(
    name="persona_card",
    description="Fiche persona : photo ronde (ou initiales), prénom et âge, lieu, contexte, marques préférées, jauges (priorité, compétences…), appareils, attentes et freins en pied, étiquette cyan en bas à droite ; carte blanche arrondie.",
    props=[
        Prop("name", "str", "Prénom (ou nom du persona).", required=True),
        Prop("age", "str", "Âge ou tranche d'âge."),
        Prop("location", "str", "Lieu de résidence."),
        Prop("photo", "image", "Photo (asset) ; sans photo, un disque avec les initiales."),
        Prop("context", "markdown", "Contexte : la démarche qui pousse le persona à chercher."),
        Prop("context_label", "str", "Libellé du contexte.", default="Contexte"),
        Prop("brands", "list", "Marques préférées (assets de logos).", default=[]),
        Prop("brands_label", "str", "Libellé des marques.", default="Marques préférées"),
        Prop("gauges", "list", "Jauges : {label, value 0-1} (priorité, compétences informatiques, réseaux sociaux…).", default=[]),
        Prop("devices", "list", "Appareils : {label, on} ou texte (Mobile, Desktop, Tablette).", default=[]),
        Prop("devices_label", "str", "Libellé des appareils.", default="Appareil(s) privilégié(s)"),
        Prop("expectations", "list", "Attentes (puces).", default=[]),
        Prop("expectations_label", "str", "Libellé des attentes.", default="Attentes"),
        Prop("brakes", "list", "Freins (puces).", default=[]),
        Prop("brakes_label", "str", "Libellé des freins.", default="Freins"),
        Prop("tag", "str", "Étiquette en bas à droite (« Et le Search ? »)."),
    ],
    render=_persona_card,
    example={"name": "Camille", "age": "34 ans", "location": "Lyon", "context": "Cherche à organiser une collecte alimentaire pour son association de quartier, sans savoir par où commencer.",
             "gauges": [{"label": "Priorité", "value": 0.8}, {"label": "Compétences informatiques", "value": 0.55}, {"label": "Utilise les réseaux sociaux", "value": 0.7}],
             "devices": [{"label": "Mobile", "on": True}, {"label": "Desktop", "on": True}, {"label": "Tablette", "on": False}],
             "expectations": ["Un guide pas à pas", "Des modèles de documents"], "brakes": ["Manque de temps", "Réglementation floue"], "tag": "Et le Search ?"},
    tags=["personnes"],
))


# --- persona_sheet ----------------------------------------------------------------------

_SHEET_HEAD = 50.0     # avatar, name, subtitle, badge
_SHEET_UNDER = 10.0    # between the header and the cards
_SHEET_GAP = 12.0      # between the columns
_SHEET_VGAP = 8.0      # between stacked blocks
_SHEET_CTX = 92.0      # design heights: a card grows when its text needs more, with a warning
_SHEET_LISTS = 108.0
_SHEET_TAG = 28.0
_SHEET_IN = 3.0        # text box inside its card (Google adds its own insets)
_SHEET_SPACING = 2.0   # between the paragraphs of a card
_SHEET_MAX = {"expectations": 3, "brakes": 3, "side_items": 5}
_CAPS_BOLD = 1.3       # bold capitals run this much wider than the wrap estimate
_CAPS = 1.15           # regular capitals


def _sheet_card(x: float, y: float, w: float, h: float, fill: str, role: str) -> dict:
    box = {"op": "box", "x": x, "y": y, "w": w, "h": h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": role}
    if fill == "background":
        box["line"] = {"color": "rule", "weight": 1}
    return box


def _sheet_text(x: float, y: float, w: float, label: str, paras: list[list[dict]], role: str) -> tuple[dict, float]:
    """A card's text, its label in capitals then ``paras`` (runs), as one box: (op, card height it needs)."""
    runs = [[{"text": str(label).upper(), "bold": True, "size": 10, "color": "ink"}]] + paras
    tw = w - 2 * _SHEET_IN
    lines = sum(_wrapped_lines("".join(r["text"] for r in para), tw, para[0]["size"]) * para[0]["size"] * LEADING for para in runs)
    th = lines + _SHEET_SPACING * (len(runs) - 1) + INSETS
    return ({"op": "text", "x": x + _SHEET_IN, "y": y + _SHEET_IN, "w": tw, "h": th, "runs": runs, "style": "caption", "size": 11,
             "spacing": _SHEET_SPACING, "role": role}, th + 2 * _SHEET_IN)


def _sheet_bullets(items: list, marker: str) -> list[list[dict]]:
    return [[{"text": "›  ", "bold": True, "size": 11, "color": marker}, {"text": str(it), "size": 11, "color": "ink"}] for it in items]


def _sheet_header(p: dict, w: float, warnings: list[str]) -> list[dict]:
    ops: list[dict] = []
    d = 46.0
    if p["photo"]:
        ops.append({"op": "image", "x": 0, "y": 2, "w": d, "h": d, "asset": str(p["photo"]), "cover": True, "role": "avatar"})
    else:
        ops.append({"op": "box", "x": 0, "y": 2, "w": d, "h": d, "shape": "ELLIPSE", "fill": "surface", "role": "avatar",
                    "text": (str(p["name"]).strip()[:1] or "?").upper(), "style": "card_title", "size": 18, "bold": True,
                    "color": "ink", "align": "CENTER", "valign": "MIDDLE"})
    right = w
    badge = {"text": p["badge"]} if isinstance(p["badge"], str) else (p["badge"] or {})
    if badge.get("text"):
        text = str(badge["text"]).upper()
        bw = len(text) * 10 * 0.62 + 2 * INSET_X + 8
        ops.append({"op": "box", "x": w - bw, "y": 6, "w": bw, "h": 22, "shape": "ROUND_RECTANGLE", "fill": badge.get("color") or "accent_alt",
                    "role": "badge", "text": text, "style": "badge", "size": 10, "bold": True, "color": "ink", "align": "CENTER",
                    "valign": "MIDDLE"})
        right = w - bw - 12
    tx = d + 12
    tw = right - tx
    name = (str(p["name"]) + (f" – {p['age']}" if p["age"] else "")).upper()
    size = fit_text_size(name + ".", tw / _CAPS_BOLD, 20, max_lines=1, floor=14)
    if _wrapped_lines(name + ".", tw / _CAPS_BOLD, size) > 1:
        warnings.append(f"name and age do not fit on one line at {size:g} pt in {tw:.0f} pt: shorten them")
    ops.append({"op": "text", "x": tx, "y": 0, "w": tw, "h": size * LEADING + INSETS, "style": "card_title", "size": size, "role": "name",
                "runs": [[{"text": name, "bold": True, "size": size, "color": "ink"},
                          {"text": ".", "bold": True, "size": size, "color": "accent"}]]})
    sub = " · ".join(str(s) for s in (p["segment"], p["role"]) if s) + (f" ({p['origin']})" if p["origin"] else "")
    if sub.strip():
        sub = sub.strip().upper()
        sw = w - tx  # under the name and the badge, which sits on the name line
        ssize = fit_text_size(sub, sw / _CAPS, 12, max_lines=1, floor=10)
        if _wrapped_lines(sub, sw / _CAPS, ssize) > 1:
            warnings.append(f"segment, role and origin do not fit on one line at {ssize:g} pt: shorten them")
        ops.append({"op": "text", "x": tx, "y": 30, "w": sw, "h": ssize * LEADING + INSETS, "text": sub, "style": "body", "size": ssize,
                    "color": "ink", "role": "subtitle", "small_ok": ssize < 11})
    return ops


def _persona_sheet(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    for key, cap in _SHEET_MAX.items():
        if len(p[key] or []) > cap:
            raise ValueError(f"persona_sheet: {key} takes {cap} items at most, got {len(p[key])}")
    warnings: list[str] = []
    if w < 480:
        warnings.append(f"made for the full content width (564 pt on a 720 x 405 deck): at {w:g} pt the columns are cramped")
    side = list(p["side_items"] or [])
    lw = round(w * 0.585, 1) if side else w
    rx, rw = lw + _SHEET_GAP, w - lw - _SHEET_GAP
    head = _sheet_header(p, w, warnings) if p["header"] else []
    y0 = _SHEET_HEAD + _SHEET_UNDER if p["header"] else 0.0

    # measure every block, then settle the heights
    ctx_paras = ([[{"text": str(p["context"]), "size": 11, "color": "text"}]] if p["context"] else []) + \
                ([[{"text": "Objectif : " + str(p["goal"]), "bold": True, "size": 11, "color": "ink"}]] if p["goal"] else [])
    ctx_text, ctx_need = _sheet_text(0, y0, lw, p["context_label"], ctx_paras, "context")
    ctx_h = max(_SHEET_CTX, ctx_need)
    if ctx_need > _SHEET_CTX:
        fields = "context and goal" if p["goal"] and p["context"] else ("goal" if p["goal"] else "context")
        warnings.append(f"{fields}: {ctx_need:.0f} pt of text, the context card grows from {_SHEET_CTX:g} pt; shorten {fields}")
    exp, brk = list(p["expectations"] or []), list(p["brakes"] or [])
    has_lists = bool(exp or brk)
    cw = (lw - _SHEET_VGAP) / 2
    lists = [(key, label, items, k * (cw + _SHEET_VGAP)) for k, (key, label, items)
             in enumerate((("expectations", p["expectations_label"], exp), ("brakes", p["brakes_label"], brk)))] if has_lists else []
    needs = {key: _sheet_text(x, 0, cw, label, _sheet_bullets(items, "accent"), key)[1] for key, label, items, x in lists}
    lists_h = max([_SHEET_LISTS, *needs.values()]) if has_lists else 0.0
    for key, need in needs.items():
        if need > _SHEET_LISTS:
            warnings.append(f"{key}: {need:.0f} pt of text, the list cards grow from {_SHEET_LISTS:g} pt; shorten the items")
    column = ctx_h + (_SHEET_VGAP + lists_h if has_lists else 0.0)
    if side:
        side_need = _sheet_text(rx, y0, rw, p["side_label"], _sheet_bullets(side, "ink"), "side")[1]
        if side_need > column:
            warnings.append(f"side_items: {side_need:.0f} pt of text, more than the {column:.0f} pt of the left column; shorten them")
            if has_lists:
                lists_h += side_need - column
            else:
                ctx_h += side_need - column
            column = side_need

    # bottom row: the tag under the left column, the note under the right one (or under the tag)
    nw = rw if side else w
    note_h = _text_height(str(p["note"]), nw, 10) if p["note"] else 0.0
    tag_h = _SHEET_TAG if p["tag"] else 0.0
    if p["tag"] and _wrapped_lines(str(p["tag"]), lw / _CAPS_BOLD, 11) > 1:
        warnings.append("tag does not fit on one line: shorten it")
    row = max(tag_h, note_h) if side else tag_h + note_h + (_SHEET_VGAP if tag_h and note_h else 0.0)
    natural = y0 + column + (_SHEET_VGAP + row if row else 0.0)
    height = natural
    if h is not None and h < natural - 0.01:
        warnings.append(f"height_pt {h:g} is less than the {natural:.0f} pt the sheet needs: it keeps {natural:.0f} pt "
                        "rather than overlap; shorten the texts or give it more room")
    elif h is not None:
        grow = h - natural
        if has_lists:
            lists_h += grow
        else:
            ctx_h += grow
        column += grow
        height = h

    ops = list(head)
    ops.append(_sheet_card(0, y0, lw, ctx_h, "background", "context_card"))
    ops.append(ctx_text)
    ly = y0 + ctx_h + _SHEET_VGAP
    for key, label, items, x in lists:
        ops.append(_sheet_card(x, ly, cw, lists_h, "background", f"{key}_card"))
        ops.append(_sheet_text(x, ly, cw, label, _sheet_bullets(items, "accent"), key)[0])
    if side:
        ops.append(_sheet_card(rx, y0, rw, column, "accent", "side_card"))
        ops.append(_sheet_text(rx, y0, rw, p["side_label"], _sheet_bullets(side, "ink"), "side")[0])
    by = y0 + column + _SHEET_VGAP
    if p["tag"]:
        ops.append({"op": "box", "x": 0, "y": by, "w": lw, "h": _SHEET_TAG, "shape": "ROUND_RECTANGLE", "fill": "cyan", "role": "tag",
                    "text": str(p["tag"]), "style": "card_title", "size": 11, "bold": True, "color": "ink", "align": "CENTER",
                    "valign": "MIDDLE"})
    if p["note"]:
        nx, ny = (rx, by) if side else (0.0, by + (tag_h + _SHEET_VGAP if tag_h else 0.0))
        ops.append({"op": "text", "x": nx, "y": ny, "w": nw, "h": note_h, "text": str(p["note"]), "style": "caption", "size": 10,
                    "color": "muted", "role": "note"})
    ops += [{"op": "warning", "text": f"persona_sheet: {msg}"} for msg in warnings]
    return ops, height


register(Component(
    name="persona_sheet",
    description="Fiche persona pleine largeur avec son propre en-tête : pastille (initiale ou photo), nom et âge en capitales suivis d'un point menthe, sous-titre public · libellé (origine), badge de statut ; à gauche contexte + objectif puis attentes et freins côte à côte, à droite une carte menthe (requêtes, verbatims) ; pastille cyan et note de source en pied. Hauteurs calculées bloc par bloc, jamais de chevauchement.",
    props=[
        Prop("name", "str", "Prénom du persona.", required=True),
        Prop("age", "str", "Âge (« 48 ans »)."),
        Prop("segment", "str", "Public visé (« Porteurs de projets »)."),
        Prop("role", "str", "Libellé du persona : fonction, besoin."),
        Prop("origin", "str", "Origine du persona (« Persona 2017 revu »), entre parenthèses."),
        Prop("photo", "image", "Photo (asset) à la place de la pastille à initiale."),
        Prop("badge", "dict", "Badge de statut calé à droite : {text, color} (couleur par défaut acide) ou un texte."),
        Prop("context", "str", "Contexte : qui est le persona, comment il cherche."),
        Prop("context_label", "str", "Libellé de la carte contexte.", default="Contexte"),
        Prop("goal", "str", "Objectif, en gras sous le contexte (« Objectif : … »)."),
        Prop("expectations", "list", "Attentes : 3 puces au plus.", default=[]),
        Prop("expectations_label", "str", "Libellé des attentes.", default="Attentes"),
        Prop("brakes", "list", "Freins : 3 puces au plus.", default=[]),
        Prop("brakes_label", "str", "Libellé des freins.", default="Freins"),
        Prop("side_label", "str", "Libellé de la carte menthe de droite.", default="Requêtes Google types"),
        Prop("side_items", "list", "Carte menthe : requêtes, verbatims… 5 puces au plus ; vide, la colonne gauche prend toute la largeur.", default=[]),
        Prop("tag", "str", "Pastille cyan sous les cartes (« 2 PROMPTS : N° 24, 27 »)."),
        Prop("note", "str", "Note de source sous la carte de droite, 10 pt gris."),
        Prop("header", "bool", "Dessiner l'en-tête ; false garde le titre du layout et la fiche commence aux cartes.", default=True),
    ],
    render=_persona_sheet,
    example={"name": "Manon", "age": "48 ans", "segment": "Porteurs de projets", "role": "Financements et partenariats", "origin": "Persona 2017 revu",
             "badge": {"text": "NOUVEAU 2026", "color": "acid"},
             "context": "Responsable développement ou chargée de projets, utilise l'IA générative.",
             "goal": "Identifier rapidement les financements pertinents.",
             "expectations": ["Recherche et filtres", "Alertes personnalisées", "FAQ détaillée"],
             "brakes": ["Trop de dossiers", "Lourdeur administrative", "Infos dispersées"],
             "side_items": ["« appel à projet » : 1 242 impr., pos. 18,5 (GSC)", "« appel à projet fondation » : 839 impr. (GSC)", "« collecte de fonds » (S)"],
             "tag": "2 PROMPTS : N° 24, 27", "note": "(GSC) Search Console www, 29/06 au 28/09/2026. (S) expression Synomia 2016."},
    tags=["personnes"],
))
