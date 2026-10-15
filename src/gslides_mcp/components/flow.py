"""Lot 4 diagrams: tree (sitemap / org chart) and flowchart (nodes on a grid,
elbow connectors with arrowheads).
"""

from __future__ import annotations

from ..themes import Theme
from . import Component, Prop, register
from .builtin import BOLD_WRAP, GLYPH_WRAP, INSET_X, INSETS, LEADING, _text_height
from .diagrams import _box_h, _half_up, _lines_h, _word_fits, warning

_DARK = {"surface_dark", "surface_dark_2", "ink", "text", "device_frame"}


def _fg(fill: str | None) -> str:
    return "on_dark" if fill in _DARK else "ink"


# --- tree -------------------------------------------------------------------------------

def _tree_vertical(root: dict, children: list[dict], theme: Theme, w: float, node_h: float, h: float | None) -> tuple[list[dict], float]:
    """Root on top, children stacked under it in a column, hung on a rail (a file tree, a cocon's pilier and its pages)."""
    indent, gap, rail_x = 22.0, 8.0, 10.0
    ts, bs = theme.size("card_title"), theme.size("body")
    root_fill = root.get("fill") or "accent"
    # the root's name stays above its sub-line: body + 2 when there is one
    label_size = bs + 2 if root.get("sub") else ts
    paras = [[{"text": str(root.get("label", "")), "bold": True, "size": label_size}]]
    if root.get("sub"):
        paras.append([{"text": str(root["sub"]), "bold": False, "size": bs}])
    root_h = max(node_h, _half_up(sum(_lines_h(r[0]["text"], w, r[0]["size"], r[0]["bold"]) for r in paras) + INSETS + 10))
    ops: list[dict] = [{"op": "box", "x": 0, "y": 0, "w": w, "h": root_h, "shape": "ROUND_RECTANGLE", "fill": root_fill, "role": "root",
                        "runs": paras, "style": "card_title", "size": ts, "color": _fg(root_fill), "align": "CENTER", "valign": "MIDDLE"}]
    ops += [warning("tree", "racine", r[0]["text"]) for r in paras if not _word_fits(r[0]["text"], w, r[0]["size"], r[0]["bold"])]
    lines: list[dict] = []
    y = root_h + 12
    cw = w - indent
    for c in children:
        text = str(c.get("label", ""))
        ch = max(node_h, _half_up(_box_h(text, cw, ts, True)))
        fill = c.get("fill") or "surface"
        if not _word_fits(text, cw, ts, True):
            ops.append(warning("tree", "enfant", text))
        ops.append({"op": "box", "x": indent, "y": y, "w": cw, "h": ch, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "child",
                    "line": {"color": "accent", "weight": 1.5} if c.get("hl") else None,
                    "text": text, "style": "card_title", "size": ts, "color": _fg(fill), "align": "START", "valign": "MIDDLE"})
        lines.append({"op": "line", "x1": rail_x, "y1": y + ch / 2, "x2": indent, "y2": y + ch / 2, "color": "accent", "weight": 1.5, "role": "stub"})
        y += ch + gap
    if children:
        last = [o for o in ops if o.get("role") == "child"][-1]
        lines.insert(0, {"op": "line", "x1": rail_x, "y1": root_h, "x2": rail_x, "y2": last["y"] + last["h"] / 2, "color": "accent",
                         "weight": 1.5, "role": "rail"})
        y -= gap
    return lines + ops, h or (y if children else root_h)


def _tree(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    root = p["root"] if isinstance(p["root"], dict) else {"label": str(p["root"])}
    children = [c if isinstance(c, dict) else {"label": str(c)} for c in p["children"]]
    if p["layout"] == "vertical":
        return _tree_vertical(root, children, theme, w, float(p["node_h"]), h)
    n = max(1, len(children))
    node_h = float(p["node_h"])
    gap_y, gap_x = float(p["gap_y"]), float(p["gap_x"])
    ts, cs = theme.size("card_title"), theme.size("caption")
    rw = min(w * 0.4, 220.0)
    rx = (w - rw) / 2
    cw = (w - (n - 1) * gap_x) / n
    # the root and the row of children grow to hold their names (bold, wrapped); the children keep one height
    root_label = str(root.get("label", ""))
    labels = [str(c.get("label", "")) for c in children]
    root_h = max(node_h, _half_up(_box_h(root_label, rw, ts, True)))
    child_h = max([node_h] + [_half_up(_box_h(t, cw, ts, True)) for t in labels])
    ops: list[dict] = [warning("tree", "racine" if k < 0 else "enfant", t) for k, t, bw in [(-1, root_label, rw)] + [(i, t, cw) for i, t in enumerate(labels)]
                       if not _word_fits(t, bw, ts, True)]
    y1 = root_h + gap_y
    bus_y = root_h + gap_y / 2
    lines: list[dict] = [{"op": "line", "x1": w / 2, "y1": root_h, "x2": w / 2, "y2": bus_y, "color": "ink", "weight": 1.5}]
    if n > 1:
        lines.append({"op": "line", "x1": cw / 2, "y1": bus_y, "x2": w - cw / 2, "y2": bus_y, "color": "ink", "weight": 1.5, "role": "bus"})
    root_fill = root.get("fill") or "accent"
    ops.append({"op": "box", "x": rx, "y": 0, "w": rw, "h": root_h, "shape": "ROUND_RECTANGLE", "fill": root_fill, "role": "root",
                "text": root_label, "style": "card_title", "size": ts, "color": _fg(root_fill),
                "align": "CENTER", "valign": "MIDDLE"})
    bottom = y1 + child_h
    for i, (c, label) in enumerate(zip(children, labels)):
        x = i * (cw + gap_x)
        cx = x + cw / 2
        lines.append({"op": "line", "x1": cx, "y1": bus_y, "x2": cx, "y2": y1, "color": "ink", "weight": 1.5})
        fill = c.get("fill") or "surface"
        ops.append({"op": "box", "x": x, "y": y1, "w": cw, "h": child_h, "shape": "ROUND_RECTANGLE", "fill": fill, "role": "child",
                    "line": {"color": "accent", "weight": 1.5} if c.get("hl") else None,
                    "text": label, "style": "card_title", "size": ts, "color": _fg(fill),
                    "align": "CENTER", "valign": "MIDDLE"})
        items = c.get("items") or []
        leaves = c.get("children") or []
        if leaves:  # third level: stacked boxes under the child, each hung on a short line
            ly = y1 + child_h + 12
            for leaf in leaves:
                leaf = leaf if isinstance(leaf, dict) else {"label": str(leaf)}
                text = str(leaf.get("label", ""))
                # at the caption size, the box growing with its lines rather than the text shrinking under the floor
                lh = max(24.0, _half_up(_text_height(text, cw - 12, cs) + 4))
                if not _word_fits(text, cw - 12, cs):
                    ops.append(warning("tree", "sous-rubrique", text))
                lines.append({"op": "line", "x1": cx, "y1": ly - 12, "x2": cx, "y2": ly, "color": "ink", "weight": 1})
                lfill = leaf.get("fill") or "surface"
                ops.append({"op": "box", "x": x, "y": ly, "w": cw, "h": lh, "shape": "ROUND_RECTANGLE", "fill": lfill, "role": "leaf",
                            "line": {"color": "accent", "weight": 1.5} if leaf.get("hl") else None,
                            "text": text, "style": "caption", "size": cs, "color": _fg(lfill), "align": "CENTER", "valign": "MIDDLE"})
                ly += lh + 12
            bottom = max(bottom, ly - 12)
        elif items:
            md = "\n".join(f"- {it}" for it in items)
            th = _text_height(md, cw, cs)
            ops.append({"op": "text", "x": x, "y": y1 + child_h + 4, "w": cw, "h": th, "markdown": md, "style": "caption",
                        "size": cs, "color": "text", "role": "items"})
            bottom = max(bottom, y1 + child_h + 4 + th)
    return lines + ops, h or bottom


register(Component(
    name="tree", description="Arborescence / organigramme à deux ou trois niveaux : racine accent, 2 à 5 enfants en rangée reliés par un bus, puis sous-rubriques listées (items) ou petites-filles en boîtes empilées (children) sous chaque enfant ; ou en colonne (layout vertical) : racine en haut, enfants en retrait sur un rail.",
    props=[
        Prop("root", "str", "Racine (texte, ou {label, sub?, fill?} ; sub = seconde ligne, en colonne).", required=True),
        Prop("children", "list", "Enfants : {label, items?: [..], children?: [texte ou {label, fill?, hl?}], fill?, hl?} ou texte (en colonne : label, fill, hl).", required=True),
        Prop("layout", "choice", "bus : enfants en rangée sous la racine ; vertical : enfants empilés en retrait sur un rail (pilier et ses pages).", default="bus",
             choices=["bus", "vertical"]),
        Prop("node_h", "number", "Hauteur des nœuds.", default=30),
        Prop("gap_y", "number", "Espace vertical racine → enfants.", default=30),
        Prop("gap_x", "number", "Espace entre enfants.", default=10),
    ],
    render=_tree,
    example={"root": "Accueil", "children": [
        {"label": "Nos programmes", "items": ["Les quatre programmes", "Leur fonctionnement", "Les soutenir"]},
        {"label": "Fondations abritées", "items": ["Les 61 fondations", "Créer la vôtre", "Espace fondateurs"], "hl": True},
        {"label": "Agir avec nous", "items": ["Donner", "Transmettre", "Agir autrement"]},
        {"label": "Nous connaître", "items": ["La fondation", "Nos engagements", "Nous suivre"]}]},
    tags=["schémas"],
))


# --- flowchart --------------------------------------------------------------------------

def _flowchart(p: dict, theme: Theme, w: float, h: float | None) -> tuple[list[dict], float]:
    nodes = list(p["nodes"])
    if not nodes:
        raise ValueError("flowchart: at least one node")
    cols = int(p["cols"] or (max(int(nd.get("col", 0)) for nd in nodes) + 1))
    rows = max(int(nd.get("row", 0)) for nd in nodes) + 1
    gap_x, gap_y = float(p["gap_x"]), float(p["gap_y"])
    nw = float(p["node_w"]) if p["node_w"] else (w - (cols - 1) * gap_x) / cols
    ls = theme.size("label")
    if not p["node_w"] and cols > 1:
        # a word wider than its node: the nodes widen into the gaps (an arrow keeps 24 pt) before a word is reported
        want = max(len(word) * GLYPH_WRAP * ls * (BOLD_WRAP if bold else 1.0) + 2 * INSET_X
                   for nd in nodes for text, bold in ((nd.get("label", ""), True), (nd.get("sub") or "", False))
                   for word in str(text).split() or [""])
        if want > nw:
            gap_x = min(gap_x, max(24.0, (w - cols * want) / (cols - 1)))
            nw = (w - (cols - 1) * gap_x) / cols

    # the grid's rows grow to hold the tallest node: its name (bold) and its sub-line, both at the body size
    def need(nd: dict) -> float:
        width = float(nd.get("w") or nw)
        sub = _lines_h(str(nd["sub"]), width, ls) if nd.get("sub") else 0.0
        return _lines_h(str(nd.get("label", "")), width, ls, True) + sub + INSETS
    nh = max([float(p["node_h"])] + [_half_up(need(nd)) for nd in nodes])
    pos: dict[str, tuple[float, float, float]] = {}
    ops: list[dict] = []
    for nd in nodes:
        width = float(nd.get("w") or nw)
        for field, text, bold in (("nœud", nd.get("label", ""), True), ("nœud", nd.get("sub") or "", False)):
            if text and not _word_fits(str(text), width, ls, bold):
                ops.append(warning("flowchart", field, text))
    for i, nd in enumerate(nodes):
        nid = str(nd.get("id", i))
        x = int(nd.get("col", 0)) * (nw + gap_x)
        y = int(nd.get("row", 0)) * (nh + gap_y)
        width = float(nd.get("w") or nw)
        pos[nid] = (x, y, width)
        fill = nd.get("fill") or "surface"
        fg = nd.get("color") or _fg(fill)
        box: dict = {"op": "box", "x": x, "y": y, "w": width, "h": nh, "shape": nd.get("shape") or "ROUND_RECTANGLE", "fill": fill,
                     "role": "node", "line": {"color": "accent", "weight": 1.5} if nd.get("hl") else None}
        if nd.get("sub"):
            # each run carries its weight: the name bold, the sub-line regular
            box["runs"] = [[{"text": str(nd.get("label", "")), "bold": True}], [{"text": str(nd["sub"]), "size": ls, "bold": False}]]
        else:
            box["text"] = str(nd.get("label", ""))
            box["bold"] = True
        box.update({"style": "label", "size": ls, "color": fg, "align": "CENTER", "valign": "MIDDLE"})
        ops.append(box)
    edges: list[dict] = []
    for e in p["edges"] or []:
        e = {"from": e[0], "to": e[1]} if isinstance(e, (list, tuple)) else dict(e)
        a, b = str(e["from"]), str(e["to"])
        if a not in pos or b not in pos:
            raise ValueError(f"flowchart: edge {a!r} → {b!r} names an unknown node; nodes: {', '.join(pos)}")
        (ax, ay, aw), (bx, by, bw) = pos[a], pos[b]
        if bx > ax + aw - 1:  # target to the right: leave from the right side
            sx, sy, tx, ty = ax + aw, ay + nh / 2, bx, by + nh / 2
            mx = sx + (tx - sx) / 2
            pts = [[sx, sy], [tx, ty]] if abs(sy - ty) < 0.5 else [[sx, sy], [mx, sy], [mx, ty], [tx, ty]]
        elif bx + bw < ax + 1:  # backward: drop into a lane under the grid, come back up into the target
            lane = rows * (nh + gap_y) - gap_y + 12
            sx, sy, tx, ty = ax + aw / 2, ay + nh, bx + bw / 2, by + nh
            pts = [[sx, sy], [sx, lane], [tx, lane], [tx, ty]]
        elif by > ay:  # below
            sx, sy, tx, ty = ax + aw / 2, ay + nh, bx + bw / 2, by
            my = sy + (ty - sy) / 2
            pts = [[sx, sy], [tx, ty]] if abs(sx - tx) < 0.5 else [[sx, sy], [sx, my], [tx, my], [tx, ty]]
        else:  # above
            sx, sy, tx, ty = ax + aw / 2, ay, bx + bw / 2, by + nh
            my = sy + (ty - sy) / 2
            pts = [[sx, sy], [tx, ty]] if abs(sx - tx) < 0.5 else [[sx, sy], [sx, my], [tx, my], [tx, ty]]
        edge: dict = {"op": "polyline", "points": pts, "color": e.get("color") or "ink", "weight": 1.5, "end_arrow": "arrow", "role": "edge"}
        if e.get("dash"):
            edge["dash"] = "DASH"
        edges.append(edge)
        if e.get("label"):
            # on the longest segment, just above it
            (x1, y1), (x2, y2) = max(zip(pts, pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
            cs = theme.size("caption")
            lh = cs * LEADING + INSETS
            edges.append({"op": "text", "x": (x1 + x2) / 2 - 40, "y": (y1 + y2) / 2 - lh, "w": 80, "h": lh, "text": str(e["label"]),
                          "style": "caption", "size": cs, "align": "CENTER", "valign": "BOTTOM", "role": "edge_label"})
    height = rows * (nh + gap_y) - gap_y
    if any(len(e.get("points", [])) == 4 and e["points"][1][1] > height for e in edges if e["op"] == "polyline"):
        height += 12  # a backward lane runs under the grid
    return edges + ops, h or height


register(Component(
    name="flowchart", description="Schéma de flux : nœuds placés sur une grille (col, row), connecteurs coudés fléchés, libellés d'arêtes, nœud mis en avant.",
    props=[
        Prop("nodes", "list", "Nœuds : {id, label, sub?, col, row, fill?, color?, shape?, hl?, w?}.", required=True),
        Prop("edges", "list", "Arêtes : [from, to] ou {from, to, label?, dash?, color?}.", default=[]),
        Prop("cols", "number", "Colonnes de la grille (défaut : d'après les nœuds)."),
        Prop("node_w", "number", "Largeur des nœuds (défaut : répartie)."),
        Prop("node_h", "number", "Hauteur des nœuds.", default=44),
        Prop("gap_x", "number", "Espace horizontal entre colonnes.", default=40),
        Prop("gap_y", "number", "Espace vertical entre rangées.", default=24),
    ],
    render=_flowchart,
    example={"nodes": [{"id": "brief", "label": "Brief", "sub": "sujet + intention", "col": 0, "row": 0},
                       {"id": "ia", "label": "Rédaction IA", "col": 1, "row": 0, "fill": "surface_dark"},
                       {"id": "relecture", "label": "Relecture humaine", "col": 2, "row": 0},
                       {"id": "publi", "label": "Publication", "col": 3, "row": 0, "fill": "accent"},
                       {"id": "kpi", "label": "Suivi des positions", "col": 3, "row": 1}],
             "edges": [["brief", "ia"], ["ia", "relecture"], ["relecture", "publi"], {"from": "publi", "to": "kpi"}, {"from": "kpi", "to": "brief", "dash": True, "label": "itération"}]},
    tags=["schémas"],
))
