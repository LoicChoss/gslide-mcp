"""Mockup components: serp (Google result), browser frame, laptop frame.

Same contract as ``builtin``. The SERP deliberately uses Google's own colours
(hex constants below) rather than theme roles: it mimics a real search
result, whatever the brand. Browser and laptop frames are themed
(``device_frame``, ``device_base``, ``rule``, ``surface``…). Screenshots
come from the Drive assets folder (``image`` = asset name or local path).
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import INSETS, _text_height

# Google SERP mimicry — intentionally not theme roles.
GOOGLE = {
    "blue": "#1A0DAB", "grey": "#4D5156", "dark": "#202124", "light": "#70757A",
    "star": "#FBBC04", "empty": "#DADCE0", "chip": "#F1F3F4", "white": "#FFFFFF",
}
_SERP_FONT = "Arial"


# --- serp -------------------------------------------------------------------------

def _serp(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    ix, iy = 16.0, 13.0
    body: list[dict] = []
    initial = (str(p["site"] or p["url"] or "?").strip()[:1] or "?").upper()
    body.append({"op": "box", "x": ix, "y": iy, "w": 24.5, "h": 24.5, "shape": "ELLIPSE", "fill": GOOGLE["chip"],
                 "line": {"color": GOOGLE["empty"], "weight": 1}, "role": "favicon", "text": initial,
                 "style": "caption", "size": 10, "bold": True, "color": GOOGLE["grey"], "font": _SERP_FONT, "align": "CENTER", "valign": "MIDDLE"})
    if p["site"]:
        body.append({"op": "text", "x": ix + 32, "y": iy - 4, "w": w - 65, "h": 14 + INSETS, "text": str(p["site"]),
                     "size": 11, "color": GOOGLE["dark"], "font": _SERP_FONT})
    if p["url"]:
        body.append({"op": "text", "x": ix + 32, "y": iy + 9, "w": w - 65, "h": 14 + INSETS, "text": str(p["url"]),
                     "style": "caption", "size": 10, "color": GOOGLE["grey"], "font": _SERP_FONT})
    ty = iy + 31.7
    body.append({"op": "text", "x": ix, "y": ty, "w": w - 32, "h": 16 + INSETS, "text": str(p["title"]),
                 "size": 13, "color": GOOGLE["blue"], "font": _SERP_FONT, "role": "title"})
    ty += 23
    if p["rating"] is not None:
        d, gap = 10.8, 1.44
        rating = max(0.0, min(5.0, float(p["rating"])))
        for k in range(5):
            sx = ix + k * (d + gap)
            body.append({"op": "box", "x": sx, "y": ty + 1.4, "w": d, "h": d, "shape": "STAR_5", "fill": GOOGLE["empty"]})
        for k in range(5):
            frac = max(0.0, min(1.0, rating - k))
            if frac <= 0:
                continue
            sx = ix + k * (d + gap)
            body.append({"op": "box", "x": sx, "y": ty + 1.4, "w": d, "h": d, "shape": "STAR_5", "fill": GOOGLE["star"]})
            if frac < 1:
                # no partial fill in Slides: mask the unfilled part with the card's white
                body.append({"op": "box", "x": sx + d * frac, "y": ty + 0.4, "w": d * (1 - frac), "h": d + 2,
                             "fill": GOOGLE["white"], "role": "star_mask"})
        rtxt = f"{rating:g}".replace(".", ",") + "/5" + (f" · {p['reviews']}" if p["reviews"] else "")
        body.append({"op": "text", "x": ix + 5 * (d + gap) + 6, "y": ty - 4, "w": w - 110, "h": 14 + INSETS, "text": rtxt,
                     "style": "caption", "size": 10, "color": GOOGLE["light"], "font": _SERP_FONT})
        ty += 20
    if p["desc"]:
        dh = _text_height(str(p["desc"]), w - 32, 11)
        body.append({"op": "text", "x": ix, "y": ty, "w": w - 32, "h": dh, "text": str(p["desc"]),
                     "size": 11, "color": GOOGLE["grey"], "font": _SERP_FONT})
        ty += dh
    height = h or (ty + 10)
    ops: list[dict] = []
    if p["frame"]:
        ops.append({"op": "box", "x": 0, "y": 0, "w": w, "h": height, "shape": "ROUND_RECTANGLE", "fill": GOOGLE["white"],
                    "line": {"color": GOOGLE["empty"], "weight": 1.25}, "role": "frame"})
    return ops + body, height


register(Component(
    name="serp", description="Mockup de résultat Google : favicon (initiale), site, URL, titre bleu, étoiles optionnelles, description. Couleurs Google volontairement hors charte.",
    props=[
        Prop("title", "str", "Titre bleu du résultat.", required=True),
        Prop("site", "str", "Nom du site (première ligne)."),
        Prop("url", "str", "URL affichée, ex. 'labelleadresse.com › astuces'."),
        Prop("desc", "str", "Description sous le titre."),
        Prop("rating", "number", "Note sur 5 (étoiles), ex. 4.6."),
        Prop("reviews", "str", "Nombre d'avis, ex. '1 024 avis'."),
        Prop("frame", "bool", "Carte blanche bordée autour du résultat.", default=True),
    ],
    render=_serp,
    example={"site": "La Belle Adresse", "url": "labelleadresse.com › astuces", "title": "Comment détacher un vêtement blanc ?",
             "rating": 4.6, "reviews": "1 024 avis", "desc": "Nos astuces de grand-mère pour raviver le blanc sans abîmer les fibres."},
    tags=["mockups"],
))


# --- browser / laptop -----------------------------------------------------------------

def _browser(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    pad, bar_h = 2.2, 24.5
    inner = w - 2 * pad
    cy = pad + bar_h
    content: list[dict] = []
    if p["image"]:
        ih = inner / float(p["image_aspect"])
        content.append({"op": "image", "x": pad, "y": cy, "w": inner, "h": ih, "asset": str(p["image"])})
        height = cy + ih + pad
    else:
        height = h or (cy + inner / float(p["image_aspect"]) + pad)
        ch = height - cy - pad
        content.append({"op": "box", "x": pad, "y": cy, "w": inner, "h": ch, "fill": p["screen"] or "background", "role": "screen"})
        if p["screen_text"]:
            content.append({"op": "text", "x": pad, "y": cy, "w": inner, "h": ch, "text": str(p["screen_text"]),
                            "style": "label", "size": 12, "bold": True, "color": "accent", "align": "CENTER", "valign": "MIDDLE"})
    ops: list[dict] = [
        # square frame, no outline: the grey bar and the content draw the browser, nothing rounded around it
        {"op": "box", "x": 0, "y": 0, "w": w, "h": height, "fill": "background", "role": "frame"},
        {"op": "box", "x": pad, "y": pad, "w": inner, "h": bar_h, "fill": "surface"},
    ]
    for k, col in enumerate(("ink", "accent", "accent_alt")):
        ops.append({"op": "box", "x": 11.5 + k * 12.2, "y": 9, "w": 7.9, "h": 7.9, "shape": "ELLIPSE", "fill": col})
    if p["url"]:
        ops.append({"op": "box", "x": 52, "y": 6.1, "w": w - 68, "h": 14.4, "shape": "ROUND_RECTANGLE", "fill": "background",
                    "text": str(p["url"]), "style": "caption", "size": 10, "color": "muted", "valign": "MIDDLE"})
    return ops + content, height


register(Component(
    name="browser", description="Cadre navigateur plat (pastilles charte, champ URL) autour d'une capture d'écran ou d'un fond de démo.",
    props=[
        Prop("url", "str", "URL affichée dans la barre."),
        Prop("image", "image", "Capture : nom d'un PNG du dossier d'assets Drive ou chemin local."),
        Prop("image_aspect", "number", "Ratio largeur/hauteur de la capture (défaut : celui du fichier).", default=1.6),
        Prop("screen", "color", "Fond de l'écran quand il n'y a pas d'image."),
        Prop("screen_text", "str", "Texte centré sur l'écran quand il n'y a pas d'image."),
    ],
    render=_browser, example={"url": "periscope.digital", "image": "screen-demo"}, tags=["mockups"],
))


def _laptop(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    inset = 8.64
    sw = w - 2 * inset
    sh = sw / float(p["image_aspect"])
    fh = sh + 2 * inset
    ops: list[dict] = [{"op": "box", "x": 0, "y": 0, "w": w, "h": fh, "shape": "ROUND_RECTANGLE", "fill": "device_frame", "role": "frame"}]
    if p["image"]:
        ops.append({"op": "image", "x": inset, "y": inset, "w": sw, "h": sh, "asset": str(p["image"]), "cover": True})
    else:
        ops.append({"op": "box", "x": inset, "y": inset, "w": sw, "h": sh, "fill": p["screen"] or "device_frame", "role": "screen"})
        if p["screen_text"]:
            ops.append({"op": "text", "x": inset, "y": inset, "w": sw, "h": sh, "text": str(p["screen_text"]),
                        "style": "label", "size": 12, "bold": True, "color": "accent", "align": "CENTER", "valign": "MIDDLE"})
    ops.append({"op": "box", "x": -18, "y": fh, "w": w + 36, "h": 12.2, "shape": "ROUND_RECTANGLE", "fill": "device_base", "role": "base"})
    return ops, fh + 12.2


def _phone(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    inset = max(4.0, w * 0.05)
    sw = w - 2 * inset
    sh = sw / float(p["image_aspect"])
    fh = sh + 2 * inset
    ops: list[dict] = [{"op": "box", "x": 0, "y": 0, "w": w, "h": fh, "shape": "ROUND_RECTANGLE", "fill": "device_frame", "role": "frame"}]
    if p["image"]:
        ops.append({"op": "image", "x": inset, "y": inset, "w": sw, "h": sh, "asset": str(p["image"]), "cover": True})
    else:
        ops.append({"op": "box", "x": inset, "y": inset, "w": sw, "h": sh, "fill": p["screen"] or "background", "role": "screen"})
        if p["screen_text"]:
            ops.append({"op": "text", "x": inset, "y": inset, "w": sw, "h": sh, "text": str(p["screen_text"]),
                        "style": "label", "size": 11, "bold": True, "color": "accent", "align": "CENTER", "valign": "MIDDLE"})
    if p["notch"]:
        nw = w * 0.32
        ops.append({"op": "box", "x": (w - nw) / 2, "y": inset + 3, "w": nw, "h": max(4.0, w * 0.05), "shape": "ROUND_RECTANGLE",
                    "fill": "device_frame", "role": "notch"})
    return ops, fh


register(Component(
    name="phone", description="Cadre smartphone (écran arrondi sombre, encoche) autour d'une capture d'écran recadrée au format de l'écran.",
    props=[
        Prop("image", "image", "Capture : nom d'un PNG du dossier d'assets Drive ou chemin local."),
        Prop("image_aspect", "number", "Ratio largeur/hauteur de l'écran (9:19.5 par défaut).", default=0.4615),
        Prop("screen", "color", "Fond de l'écran sans image."),
        Prop("screen_text", "str", "Texte centré sur l'écran sans image."),
        Prop("notch", "bool", "Encoche en haut de l'écran.", default=True),
    ],
    render=_phone, example={"screen": "surface_dark_2", "screen_text": "Capture mobile"}, tags=["mockups"],
))


register(Component(
    name="laptop", description="Cadre laptop (écran sombre arrondi + socle) autour d'une capture d'écran.",
    props=[
        Prop("image", "image", "Capture : nom d'un PNG du dossier d'assets Drive ou chemin local (recadrée au format de l'écran)."),
        Prop("image_aspect", "number", "Ratio largeur/hauteur de l'écran (16:10 par défaut, comme PLaptop).", default=1.6),
        Prop("screen", "color", "Fond de l'écran sans image."),
        Prop("screen_text", "str", "Texte centré sur l'écran sans image."),
    ],
    render=_laptop, example={"image": "screen-demo"}, tags=["mockups"],
))
