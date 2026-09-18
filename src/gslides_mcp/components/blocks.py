"""Text-block components: bigstat, stats, pill, checklist, chevrons, arrows.

Same contract as ``builtin``: ``render(props, theme, w, h) -> (ops, height)``
at origin, theme roles and named text styles only.
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import INSETS, LEADING, _text_height

_DARK_FILLS = {"surface_dark", "surface_dark_2", "ink", "text"}


# --- bigstat / stats ---------------------------------------------------------------------

def _bigstat(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    color = p["color"]
    ops: list[dict] = [
        {"op": "text", "x": 0, "y": 0, "w": w, "h": 64 + INSETS, "text": str(p["value"]), "style": "stat_value",
         "color": color, "align": "CENTER"},
        {"op": "text", "x": 0, "y": 72, "w": w, "h": 18 + INSETS, "text": str(p["label"]), "style": "stat_label",
         "color": color, "align": "CENTER"},
    ]
    height = 98.0
    if p["sub"]:
        ops.append({"op": "text", "x": 0, "y": 98, "w": w, "h": 14 + INSETS, "text": str(p["sub"]), "style": "caption",
                    "size": 11, "align": "CENTER"})
        height = 120.0
    return ops, h or height


register(Component(
    name="bigstat", description="Un chiffre spectaculaire centré (54 pt) avec son libellé et un sous-texte optionnel.",
    props=[
        Prop("value", "str", "Le chiffre, formaté.", required=True),
        Prop("label", "str", "Libellé sous le chiffre.", required=True),
        Prop("sub", "str", "Précision en petit."),
        Prop("color", "color", "Couleur du chiffre et du libellé (rôle du thème)."),
    ],
    render=_bigstat, example={"value": "+42 %", "label": "de trafic organique", "sub": "vs 2025, à périmètre constant"},
    tags=["chiffres"],
))


def _stats(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    items = list(p["items"])
    n = max(1, len(items))
    per_w = w / n
    color = p["color"]
    ops: list[dict] = []
    height = 82.0
    for i, it in enumerate(items):
        value, label, sub = (it.get("value"), it.get("label"), it.get("sub")) if isinstance(it, dict) else (it[0], it[1], None)
        x = i * per_w
        ops.append({"op": "text", "x": x, "y": 0, "w": per_w, "h": 46 + INSETS, "text": str(value), "style": "stat_value",
                    "size": 38, "color": color, "align": "CENTER"})
        ops.append({"op": "text", "x": x, "y": 56, "w": per_w, "h": 18 + INSETS, "text": str(label), "style": "stat_label",
                    "size": 12.5, "color": color, "align": "CENTER"})
        if sub:
            sh = _text_height(str(sub), per_w, 10)
            ops.append({"op": "text", "x": x, "y": 80, "w": per_w, "h": sh, "text": str(sub), "style": "caption", "align": "CENTER", "role": "sub"})
            height = max(height, 80 + sh)
    return ops, h or height


register(Component(
    name="stats", description="Rangée de chiffres clés centrés (valeur 38 pt + libellé), répartis sur la largeur.",
    props=[
        Prop("items", "list", "Chiffres : {value, label, sub?} (ou paires [value, label]).", required=True),
        Prop("color", "color", "Couleur des chiffres (rôle du thème)."),
    ],
    render=_stats, example={"items": [{"value": "12", "label": "pays couverts"}, {"value": "3", "label": "langues"}, {"value": "98 %", "label": "de satisfaction"}]},
    tags=["chiffres"],
))


# --- pill ------------------------------------------------------------------------------------

def _pill(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    color = p["color"]
    outline = bool(p["outline"])
    text = str(p["text"]).upper() if outline else str(p["text"])
    pw = min(w, len(text) * 6.8 + 36)
    ph = h or 29
    box: dict = {"op": "box", "x": 0, "y": 0, "w": pw, "h": ph, "shape": "ROUND_RECTANGLE", "text": text,
                 "style": "pill", "size": p["size"], "align": "CENTER", "valign": "MIDDLE"}
    if outline:
        box.update({"fill": "background", "line": {"color": color, "weight": 2}, "color": color})
    else:
        box.update({"fill": color, "color": "on_dark" if color in _DARK_FILLS else "on_accent"})
    return [box], ph


register(Component(
    name="pill", description="Capsule (rectangle arrondi) pleine ou en contour, largeur ajustée au texte.",
    props=[
        Prop("text", "str", "Texte de la capsule.", required=True),
        Prop("color", "color", "Couleur de fond (ou du contour).", default="accent"),
        Prop("outline", "bool", "Contour seul, texte en capitales.", default=False),
        Prop("size", "number", "Taille de police.", default=11),
    ],
    render=_pill, example={"text": "Google Ads", "outline": True}, tags=["texte"],
))


# --- checklist / chevrons / arrows ------------------------------------------------------------

def _checklist(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    gap = float(p["gap"])
    color = p["color"]
    ops: list[dict] = []
    y = 0.0
    bottom = 0.0
    for it in p["items"]:
        text, done = (it.get("text", ""), bool(it.get("done"))) if isinstance(it, dict) else (str(it), False)
        ops.append({"op": "box", "x": 0, "y": y + 2, "w": 15, "h": 15, "fill": color if done else None,
                    "line": {"color": "ink", "weight": 2}, "role": "check"})
        if done:
            ops.append({"op": "polyline", "points": [[3.2, y + 11], [6.1, y + 14.6], [11.9, y + 6.3]], "color": "ink", "weight": 2.25})
        th = max(gap - 6, _text_height(text, w - 26, 12))
        ops.append({"op": "text", "x": 26, "y": y - 2, "w": w - 26, "h": th, "markdown": str(text), "style": "list", "size": 12})
        bottom = max(bottom, y + 17, y - 2 + th)
        y += max(gap, th + 2)
    return ops, h or bottom


register(Component(
    name="checklist", description="Liste à cases carrées ; les cases cochées sont pleines (accent) avec une coche.",
    props=[
        Prop("items", "list", "Éléments : texte, ou {text, done}.", required=True),
        Prop("gap", "number", "Pas vertical.", default=32),
        Prop("color", "color", "Couleur des cases cochées.", default="accent"),
    ],
    render=_checklist, example={"items": [{"text": "Sitemap XML soumis", "done": True}, "Balises canoniques", {"text": "Core Web Vitals", "done": False}]},
    tags=["texte"],
))


def _marker_list(marker: str, marker_color: str | None):
    def render(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
        size = float(p["size"])
        spacing = float(p["spacing"])
        runs = []
        for it in p["items"]:
            prefix: dict = {"text": f"{marker}  ", "bold": True}
            if marker_color:
                prefix["color"] = marker_color
            runs.append([prefix, {"text": str(it)}])
        n = max(1, len(runs))
        wrapped = sum(max(1, -(-len(str(it)) // max(1, int((w - 20) / (size * 0.46))))) for it in p["items"])
        height = h or (wrapped * size * LEADING + (n - 1) * spacing + INSETS)
        return [{"op": "text", "x": 0, "y": 0, "w": w, "h": height, "runs": runs, "style": "list", "size": size, "spacing": spacing}], height
    return render


register(Component(
    name="chevrons", description="Liste à puces › (chevron accent), un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police.", default=12.5),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("›", "positive"), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))

register(Component(
    name="arrows", description="Liste à flèches →, un paragraphe par élément.",
    props=[
        Prop("items", "list", "Éléments (texte).", required=True),
        Prop("size", "number", "Taille de police.", default=12.5),
        Prop("spacing", "number", "Espace après chaque paragraphe.", default=9),
    ],
    render=_marker_list("→", None), example={"items": ["Un premier point", "Un second point"]}, tags=["texte"],
))
