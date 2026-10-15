"""Explanatory schemes from the SEO / GEO training decks: funnel_stages (a
qualitative TOFU / MOFU / BOFU funnel with a reading column) and fan_out
(one question fanned out into sub-queries, then the pages that answer them).

Slides cannot set a shape's adjustments: a TRAPEZOID's slope is fixed at a
quarter of its height (verified live), far from the mock-up's. A stage is a
rectangle and two mirrored right triangles, which take any slope.
"""

from __future__ import annotations

import math
import re

from ..themes import Theme
from . import Component, Prop, register, render, shift
from .brand import _tracked
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, _text_height, _wrapped_lines
from .diagrams import _word_fits, warning

_STAGE_FILLS = ("accent_alt", "surface", "accent", "surface_dark", "surface_dark_2")
_DARK = {"surface_dark", "surface_dark_2", "ink", "text"}


def _fg(fill: str) -> str:
    return "on_dark" if fill in _DARK else ("on_accent" if fill == "accent" else "ink")


HEADER_SIZE = 10.0  # column titles: tracked capitals, at the caption floor
HEADER_H = HEADER_SIZE * LEADING + INSETS


def _header(text: str, x: float, y: float, w: float, align: str = "START", role: str = "column_header") -> dict:
    return {"op": "text", "x": x, "y": y, "w": w, "h": HEADER_H, "text": _tracked(text), "style": "caption", "size": HEADER_SIZE,
            "bold": True, "color": "muted", "align": align, "role": role}


def _md_h(text: str, width: float, size: float) -> float:
    """Box height of a short markdown text: a line with ``**bold**`` wraps with the wider bold glyphs."""
    lines = 0
    for line in str(text).split("\n"):
        bold = "**" in line or "__" in line
        lines += _wrapped_lines(re.sub(r"\*\*|__|==|\*|`", "", line), width, size * (BOLD_WRAP if bold else 1.0))
    return max(1, lines) * size * LEADING + INSETS


# --- funnel_stages ---------------------------------------------------------------------------

# a stage: its title at the body size (bold), then the sub-title and the strong line as 10.5 pt small lines
_STAGE_RUNS = (("title", None, True, False), ("sub", 10.5, False, True), ("text", 10.5, True, False))


def _stage_paras(st: dict, color: str, title_size: float) -> list[list[dict]]:
    return [[{"text": str(st[key]), "size": size or title_size, "bold": bold, "italic": italic, "color": color}]
            for key, size, bold, italic in _STAGE_RUNS if st.get(key)]


def _note_paras(st: dict) -> list[list[dict]]:
    """The reading column: the value (14 pt bold) and its precision (10.5 pt grey)."""
    note = []
    if st.get("note"):
        note.append([{"text": str(st["note"]), "size": 14, "bold": True, "color": "ink"}])
    if st.get("note_sub"):
        note.append([{"text": str(st["note_sub"]), "size": 10.5, "bold": False, "color": "muted"}])
    return note


def _paras_h(paras: list[list[dict]], width: float) -> float:
    total = 0.0
    for (run,) in paras:
        size = run["size"]
        total += _wrapped_lines(run["text"], width, size * (BOLD_WRAP if run["bold"] else 1)) * size * LEADING
    return total + INSETS


def _text_w(top_w: float, bottom_w: float) -> float:
    """Width of a stage's text box: between its bottom and its middle width (the text is centred vertically)."""
    return bottom_w + (top_w - bottom_w) / 4 - 8


def _funnel_stages(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    stages = [s if isinstance(s, dict) else {"title": str(s)} for s in p["stages"]]
    if not stages:
        raise ValueError("funnel_stages: at least one stage")
    n = len(stages)
    notes = any(s.get("note") or s.get("note_sub") for s in stages)
    axis_w = 30.0 if p["axis"] else 0.0
    note_w = w * float(p["note_ratio"]) if notes else 0.0
    fx = axis_w
    fw = w - axis_w - (note_w + 20 if notes else 0)
    top_w, bot_w = fw * float(p["top_ratio"]), fw * float(p["bottom_ratio"])
    cx = fx + fw / 2
    gap, min_h = float(p["gap"]), float(p["min_h"])
    ops: list[dict] = []
    top = 0.0
    if p["stage_header"] or p["note_header"]:
        if p["stage_header"]:
            ops.append(_header(str(p["stage_header"]), 0, 0, w / 2 if notes else w))
        if p["note_header"] and notes:
            ops.append(_header(str(p["note_header"]), w / 2, 0, w / 2, "END"))
        top = HEADER_H + 10.5

    fills = [s.get("fill") or _STAGE_FILLS[i % len(_STAGE_FILLS)] for i, s in enumerate(stages)]
    title_size = max(12.5, theme.size("label"))
    paras = [_stage_paras(s, s.get("color") or _fg(f), title_size) for s, f in zip(stages, fills)]
    notes_h = [_paras_h(_note_paras(s), note_w) if (s.get("note") or s.get("note_sub")) else 0.0 for s in stages]
    # heights follow the text (and the note beside it), measured at each stage's bottom width,
    # which depends on the heights: settle twice
    heights = [min_h] * n
    for _ in range(3):
        total = sum(heights) + gap * (n - 1)
        ys = [sum(heights[:i]) + gap * i for i in range(n)]
        width_at = (lambda yy, total=total: top_w - (top_w - bot_w) * yy / total)
        heights = [max(min_h, _paras_h(pa, _text_w(width_at(y), width_at(y + hh))) + 12, nh + 4)
                   for pa, y, hh, nh in zip(paras, ys, heights, notes_h)]
    total = sum(heights) + gap * (n - 1)
    k = (top_w - bot_w) / total  # width lost per point of height
    y = top
    for i, (st, fill, pa, hh) in enumerate(zip(stages, fills, paras, heights)):
        wt = top_w - k * (y - top)
        wb = wt - k * hh
        inset = (wt - wb) / 2
        # body, then the two sides: right triangles mirrored so the hypotenuses make the funnel's edges
        ops.append({"op": "box", "x": cx - wb / 2 - 0.4, "y": y, "w": wb + 0.8, "h": hh, "fill": fill, "role": "stage"})
        ops.append({"op": "box", "x": cx - wt / 2, "y": y, "w": inset, "h": hh, "shape": "RIGHT_TRIANGLE", "flip": "xy", "fill": fill, "role": "stage_side"})
        ops.append({"op": "box", "x": cx + wb / 2, "y": y, "w": inset, "h": hh, "shape": "RIGHT_TRIANGLE", "flip": "y", "fill": fill, "role": "stage_side"})
        if pa:
            tw = _text_w(wt, wb)
            ops.append({"op": "text", "x": cx - tw / 2, "y": y, "w": tw, "h": hh, "runs": pa, "style": "caption", "size": 10.5,
                        "align": "CENTER", "valign": "MIDDLE", "role": "stage_text"})
            ops += [warning("funnel_stages", "étage", run["text"]) for (run,) in pa if not _word_fits(run["text"], tw, run["size"], run["bold"])]
        if st.get("note") or st.get("note_sub"):
            ops.append({"op": "text", "x": w - note_w, "y": y, "w": note_w, "h": hh, "runs": _note_paras(st), "style": "caption",
                        "size": 10.5, "align": "END", "valign": "MIDDLE", "role": "note"})
        y += hh + gap
    bottom = top + total
    if p["axis"]:
        ops.append({"op": "line", "x1": axis_w - 8, "y1": top, "x2": axis_w - 8, "y2": bottom, "color": "divider", "weight": 1,
                    "end_arrow": "open", "role": "axis"})
        ops.append({"op": "text", "x": (axis_w - 16) / 2 - total / 2, "y": top + total / 2 - 10, "w": total, "h": 20,
                    "text": _tracked(str(p["axis"])), "style": "axis", "size": 9.5, "small_ok": True, "bold": True, "color": "muted",
                    "align": "CENTER", "valign": "MIDDLE", "rotate": -90, "role": "axis_label"})
    height = bottom
    if p["conclusion"]:
        c = p["conclusion"] if isinstance(p["conclusion"], dict) else {"title": str(p["conclusion"])}
        cw, pad = top_w, 14.0
        cy = bottom + 16
        inner = cw - 2 * pad
        bs = theme.size("body")
        title_h = _wrapped_lines(str(c.get("title", "")), inner, 15 * BOLD_WRAP) * 15 * LEADING + INSETS if c.get("title") else 0.0
        text_h = _md_h(str(c["text"]), inner, bs) if c.get("text") else 0.0
        ch = pad + title_h + (4 if title_h and text_h else 0) + text_h + pad
        x = cx - cw / 2
        ops.append({"op": "box", "x": x, "y": cy, "w": cw, "h": ch, "shape": "ROUND_RECTANGLE", "fill": "surface_dark", "role": "conclusion"})
        ty = cy + pad
        if title_h:
            ops.append({"op": "text", "x": x + pad, "y": ty, "w": inner, "h": title_h, "text": str(c["title"]), "style": "card_title",
                        "size": 15, "bold": True, "color": "accent", "align": "CENTER", "role": "conclusion_title"})
            ty += title_h + 4
        if text_h:
            ops.append({"op": "text", "x": x + pad, "y": ty, "w": inner, "h": text_h, "markdown": str(c["text"]), "style": "body",
                        "size": bs, "color": "on_dark", "align": "CENTER", "role": "conclusion_text"})
        height = cy + ch
    return ops, h or height


register(Component(
    name="funnel_stages",
    description="Entonnoir d'étages qualitatif (TOFU / MOFU / BOFU) : trapèzes jointifs de couleurs charte, titre, sous-titre et ligne forte par étage, colonne de lecture à droite (valeur + précision), titres de colonnes, axe vertical fléché et encadré de conclusion navy.",
    props=[
        Prop("stages", "list", "Étages, du haut vers le bas : {title, sub?, text?, note?, note_sub?, fill?, color?} ou texte.", required=True),
        Prop("stage_header", "str", "Titre de la colonne de l'entonnoir (capitales espacées)."),
        Prop("note_header", "str", "Titre de la colonne de lecture, à droite."),
        Prop("axis", "str", "Libellé de l'axe vertical à gauche (« Intention d'agir ↑ »), filet fléché vers le bas."),
        Prop("conclusion", "dict", "Encadré navy sous l'entonnoir : {title, text (markdown)}."),
        Prop("top_ratio", "number", "Largeur du haut de l'entonnoir (part de sa colonne).", default=1.0),
        Prop("bottom_ratio", "number", "Largeur du bas de l'entonnoir (part de sa colonne).", default=0.42),
        Prop("note_ratio", "number", "Part de la largeur prise par la colonne de lecture.", default=0.28),
        Prop("gap", "number", "Espace entre étages.", default=6),
        Prop("min_h", "number", "Hauteur minimale d'un étage.", default=44),
    ],
    render=_funnel_stages,
    example={"stages": [
        {"title": "TOFU · informationnel, froid", "sub": "« grippe a », « hantavirus france »", "note": "-20 à -50 %", "note_sub": "clic capté par l'IA"},
        {"title": "MOFU · considération", "sub": "« comment déduire un don »", "note": "partiel", "note_sub": "clic préservé si réassurance"},
        {"title": "BOFU · transactionnel", "sub": "don · pétition · collecte", "text": "l'action se fait chez vous", "note": "résiste", "note_sub": "clic à forte valeur"}],
        "stage_header": "Étage du funnel", "note_header": "Impact de l'IA sur le clic", "axis": "Intention d'agir",
        "conclusion": {"title": "Le focus SEO de Pasteur", "text": "Là où le clic survit à l'IA\n**et où il rapporte : le bas de funnel**"}},
    tags=["schémas"],
))


# --- fan_out ---------------------------------------------------------------------------------

def _accent_runs(text: str, size: float, color: str, accent: str) -> list[dict]:
    """``==x==`` spans of ``text`` as bold runs in ``accent``, the rest in ``color``."""
    runs = []
    for k, part in enumerate(re.split(r"==(.+?)==", text)):
        if part:
            runs.append({"text": part, "size": size, "bold": bool(k % 2), "color": accent if k % 2 else color})
    return runs


def _fan_out(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    branches = [str(b) for b in p["branches"]]
    if not branches:
        raise ValueError("fan_out: at least one branch")
    target = p["target"]
    if target:
        src_w, conn, br_w, arrow_w = w * 0.27, max(36.0, w * 0.07), w * 0.27, 48.0
    else:
        src_w, conn = w * 0.4, max(40.0, w * 0.1)
        br_w, arrow_w = w - src_w - conn, 0.0
    bx = src_w + conn
    tx = bx + br_w + arrow_w
    labels = [(p["source_label"], 0.0), (p["branches_label"], bx), (p["target_label"] if target else None, tx)]
    top = HEADER_H + 8.5 if any(t for t, _ in labels) else 0.0
    bs = theme.size("body")
    # branches: one per line, the box grows with a long query
    bh = [max(float(p["branch_h"]), _text_height(b, br_w, bs)) for b in branches]
    warns: list[dict] = [warning("fan_out", "sous-requête", b) for b in branches if not _word_fits(b, br_w, bs)]
    gap = float(p["gap"])
    stack_h = sum(bh) + gap * (len(bh) - 1)
    tree_ops: list[dict] = []
    tree_h = 0.0
    if target:
        tree = {"layout": "vertical", "root": target.get("root", ""), "children": target.get("children") or []}
        tree_ops, tree_h = render("tree", tree, theme, w - tx, None)
    # the question: 15 pt, down to the body size when a word is wider than its block (never under it)
    source = str(p["source"])
    widest = max([len(word) * GLYPH_WRAP * (BOLD_WRAP if k % 2 else 1.0)
                  for k, part in enumerate(re.split(r"==(.+?)==", source)) for word in part.split()] or [0.0])
    avail = src_w - 24 - 2 * INSET_X
    size = max(float(p["source_size"]), bs)
    if widest and widest * size > avail:
        size = max(bs, math.floor(avail / widest * 2) / 2)
        if widest * size > avail + 0.01:
            warns.append(warning("fan_out", "question", source))
    src_text_h = _text_height(re.sub(r"==(.+?)==", r"\1", source), src_w - 36, size * BOLD_WRAP)
    src_h = max(src_text_h + 36, stack_h * 0.8)
    body_h = max(stack_h, tree_h, src_h)
    cy = top + body_h / 2
    ops: list[dict] = []
    for text, x in labels:
        if text:
            ops.append(_header(str(text), x, 0, (br_w if x == bx else src_w if x == 0 else w - tx), role="column_label"))
    ops.append({"op": "box", "x": 0, "y": cy - src_h / 2, "w": src_w, "h": src_h, "shape": "ROUND_RECTANGLE", "fill": "surface_dark", "role": "source"})
    ops.append({"op": "text", "x": 12, "y": cy - src_h / 2, "w": src_w - 24, "h": src_h, "style": "body", "size": size, "valign": "MIDDLE",
                "runs": [_accent_runs(str(p["source"]), size, "on_dark", "accent")], "role": "source_text"})
    y = cy - stack_h / 2
    curves, boxes = [], []
    for text, hh in zip(branches, bh):
        curves.append({"op": "line", "x1": src_w, "y1": cy, "x2": bx, "y2": y + hh / 2, "curve": True, "color": "accent", "weight": 1.5, "role": "fan"})
        boxes.append({"op": "box", "x": bx, "y": y, "w": br_w, "h": hh, "shape": "ROUND_RECTANGLE", "fill": "background",
                      "line": {"color": "rule", "weight": 1}, "text": text, "style": "body", "size": bs, "color": "ink", "align": "START", "valign": "MIDDLE",
                      "role": "branch"})
        y += hh + gap
    ops.extend(curves + boxes)  # the curves end under the boxes' outlines
    ops.append({"op": "box", "x": src_w - 3.5, "y": cy - 3.5, "w": 7, "h": 7, "shape": "ELLIPSE", "fill": "accent", "role": "dot"})
    if target:
        ops.append({"op": "line", "x1": bx + br_w + 10, "y1": cy, "x2": tx - 10, "y2": cy, "color": "ink", "weight": 1.5,
                    "end_arrow": "arrow", "role": "arrow"})
        ops.extend(shift(tree_ops, tx, cy - tree_h / 2))
    return ops + warns, h or (top + body_h)


register(Component(
    name="fan_out",
    description="Query fan-out : une question (bloc navy, mots clés en menthe) éclatée par des liens courbes en sous-requêtes (cases à filet), puis flèche vers les pages qui y répondent (pilier menthe et pages filles en colonne).",
    props=[
        Prop("source", "str", "La question de départ ; ==mots== en menthe gras.", required=True),
        Prop("branches", "list", "Les sous-requêtes, une case chacune.", required=True),
        Prop("target", "dict", "Pages qui répondent, en arborescence verticale : {root: texte ou {label, sub}, children: [..]} ; vide = pas de flèche."),
        Prop("source_label", "str", "Titre de la colonne de la question (capitales espacées)."),
        Prop("branches_label", "str", "Titre de la colonne des sous-requêtes."),
        Prop("target_label", "str", "Titre de la colonne des pages."),
        Prop("source_size", "number", "Taille du texte de la question.", default=15),
        Prop("branch_h", "number", "Hauteur minimale d'une case.", default=32),
        Prop("gap", "number", "Espace entre cases.", default=10),
    ],
    render=_fan_out,
    example={"source": "« À quelle association donner pour un don ==déductible ?== »",
             "branches": ["don déductible 66 % ?", "reçu fiscal / cerfa", "plafond de déduction", "don ponctuel ou mensuel ?"],
             "target": {"root": {"label": "Pilier", "sub": "Faire un don à Pasteur"}, "children": ["Don & impôts (66 %)", "Votre reçu fiscal", "Ponctuel ou mensuel ?"]},
             "source_label": "Question posée à l'IA", "branches_label": "Query fan-out", "target_label": "Cocon « Faire un don »"},
    tags=["schémas"],
))
