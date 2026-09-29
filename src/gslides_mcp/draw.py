"""Primitive drawing ops (points) → Slides ``batchUpdate`` requests.

This is the canvas every component renders onto. An op is a dict with an
``op`` key; coordinates are in points on the slide; colors are theme roles,
palette tokens or ``#RRGGBB``; text sizes/fonts default to the theme's named
text styles. Nothing here knows about Periscope — see ``themes``.

Ops:
    box       x y w h [fill] [line{color,weight,dash}] [shape] [+ text keys]
    text      x y w h  text | markdown | runs=[[{text,bold,italic,color,size,font,highlight}],…]
              [style] [size] [color] [bold] [italic] [font] [align] [valign] [spacing] [small_ok]
              (markdown: ==texte== surligne avec le rôle ``highlight`` ; small_ok: la taille
              demandée passe sous le plancher du thème quand le bloc ne peut pas grandir)
    line      x1 y1 x2 y2 [color] [weight] [dash] [end_arrow] [start_arrow]
    polyline  points=[[x,y],…] [color] [weight] [dash] [end_arrow]   (arrow on the last segment)
    arc       cx cy r a0 a1 weight [color]        (degrees, 0 = east, clockwise)
    ring      cx cy r thickness segments=[{value,color}] [start=-90] [span=360] [render=arcs|spokes]
    table     x y w rows=[[…],…] [col_w] [row_h] [row_heights=[…]] [header] [banding] [first_col_bold]
              [align=[…]] [borders{color,weight}|None] [size] [style]
              [row_fills{i:color}] [bold_rows] [cell_fills{(i,j):color}] [cell_text_colors] [cell_runs{(i,j):runs}]
    image     x y w h  drive_file_id | url | asset [tint] [cover] [contain] [slot] [fit]   (asset = name in the
              Drive assets folder; cover crops the source to the box like object-fit: cover,
              contain shrinks and centres the box to the source's aspect; slot keeps the box as
              the element's frame — an empty-slot placeholder, the picture swapped in with fit
              inside | crop — so replace_images can change it later)

What the Slides API cannot do, and how ops cope: no freeform geometry, so
polylines are straight segments, arcs are 1° thick-line chords, rings / pies
are quarter-turn ARC shapes stroked as thick as the ring (a few per ring, see
``arc_plan``) or, failing an exact plan, 1° radial spokes; text insets are
fixed (~7 pt left/right, ~4 pt top/bottom, ``INSET_X`` / ``INSET_Y`` below —
budget for them); predefined shapes only (no adjust handles).
"""

from __future__ import annotations

import math
import re

from .themes import Theme
from .util import md_requests

PT = 12700
INSET_X = 7.2  # Google's fixed text-box insets, in pt
INSET_Y = 3.6
HL_OPEN, HL_CLOSE = "\ue000", "\ue001"  # private-use sentinels carrying ==highlight== through the markdown writer
SMALL_BOX_W, SMALL_BOX_H = 48.0, 30.0  # below this, a box's text is drawn in a centred overlay (see box())
_ARROWS = {"none": "NONE", "arrow": "FILL_ARROW", "open": "OPEN_ARROW", "dot": "FILL_CIRCLE", "stealth": "STEALTH_ARROW"}
_ALIGN = {"START": "START", "LEFT": "START", "CENTER": "CENTER", "END": "END", "RIGHT": "END", "JUSTIFIED": "JUSTIFIED"}
_VALIGN = {"TOP": "TOP", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM"}
_ARC_STEP_DEG = 1.0


_QUARTER = 90.0  # Google's ARC preset spans a quarter turn; the API cannot move its adjust handles
_ARC_OVERLAP = 2.0  # consecutive arcs of one share overlap, so no hairline shows between them
_ARC_SEAM = 0.6  # a share runs this far under the share painted after it
_PLAN_BIN = 0.25  # degrees: the grid arc_plan checks its result on


def arc_plan(shares: list[tuple], span: float = 360.0) -> list[tuple] | None:
    """Painting order of quarter-turn arcs that shows every share of a ring exactly, or None.

    ``shares``: ``[(color, a0, a1)]`` in angular order (degrees, clockwise,
    0 = east). Returns ``[("arc", color, a0, a0 + 90) | ("spokes", color, a0, a1)]``
    in painting order. Every share but the last painted is laid with arcs
    from its start onwards; its last arc may overshoot onto the shares
    painted after it, which cover the overshoot. The last painted share
    must not overshoot: on a full turn it is the largest share (moved to
    the end), laid from both of its ends — or, when it is under a quarter
    turn, drawn in spokes. A partial ring (gauge) keeps its order and lays
    a piece back from the ring's end rather than past it. The plan is
    checked on a 0.25° grid; None means no exact plan (fall back to spokes).
    """
    if not shares:
        return []
    full = span >= 359.999
    order = list(shares)
    if full:
        k = max(range(len(order)), key=lambda i: order[i][2] - order[i][1])
        order = order[k + 1:] + order[:k + 1]
    end = shares[-1][2]
    step = _QUARTER - _ARC_OVERLAP
    plan: list[tuple] = []
    for n, (color, a0, a1) in enumerate(order):
        last = n == len(order) - 1
        lo = a0 - (_ARC_SEAM if full and n == 0 else 0.0)  # the first share runs under the last one
        hi = a1 if last else a1 + _ARC_SEAM  # and every share under the next one
        if not full:
            hi = min(hi, end)
        if hi - lo >= _QUARTER:
            # from the start, then one piece laid back from the end: nothing spills out of the share
            p = lo
            while p + _QUARTER < hi:
                plan.append(("arc", color, p, p + _QUARTER))
                p += step
            plan.append(("arc", color, hi - _QUARTER, hi))
        elif last:
            plan.append(("spokes", color, a0, a1))  # on top of everything: it must not overshoot
        else:
            # under a quarter turn: overshoot forwards, onto shares painted later; a partial
            # ring lays it back from its end rather than past it (the check refuses a bad fit)
            p = lo if full else min(lo, end - _QUARTER)
            plan.append(("arc", color, p, p + _QUARTER))
    return plan if _plan_shows(shares, plan) else None


def _plan_shows(shares: list[tuple], plan: list[tuple]) -> bool:
    """True when painting ``plan`` in order leaves every share's colour on top, and nothing outside them."""
    n = int(round(360 / _PLAN_BIN))

    def cover(grid: list, a0: float, a1: float, value) -> None:
        for k in range(math.floor(a0 / _PLAN_BIN), math.ceil(a1 / _PLAN_BIN)):
            c = (k + 0.5) * _PLAN_BIN
            if a0 <= c <= a1:
                grid[k % n] = value

    want: list = [None] * n
    got: list = [None] * n
    for color, a0, a1 in shares:
        cover(want, a0, a1, repr(color))
    for _kind, color, a0, a1 in plan:
        cover(got, a0, a1, repr(color))
    edges = [a % 360 for _c, a0, a1 in shares for a in (a0, a1)]
    for k in range(n):
        c = (k + 0.5) * _PLAN_BIN
        if any(min(abs(c - e), 360 - abs(c - e)) < 1.0 for e in edges):
            continue  # boundaries: the seam overlaps and the spokes' width live here
        if want[k] != got[k]:
            return False
    return True


SLOT_FRAME_PREFIX = "slot:"


def slot_frame_text(x: float, y: float, w: float, h: float) -> str:
    """Alt-text description recording an image slot's frame, in page points."""
    return f"{SLOT_FRAME_PREFIX}{x:.1f},{y:.1f},{w:.1f},{h:.1f}"


def parse_slot_frame(text: str | None) -> tuple[float, float, float, float] | None:
    """The frame recorded by ``slot_frame_text``, or None."""
    if not text or not text.startswith(SLOT_FRAME_PREFIX):
        return None
    try:
        x, y, w, h = (float(v) for v in text[len(SLOT_FRAME_PREFIX):].split(","))
    except ValueError:
        return None
    return (x, y, w, h) if w > 0 and h > 0 else None


def _emu(pt: float) -> int:
    return int(round(pt * PT))


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def _elem_props(page_id: str, x: float, y: float, w: float, h: float,
                sx: int = 1, sy: int = 1) -> dict:
    return {
        "pageObjectId": page_id,
        "size": {
            "width": {"magnitude": max(1, _emu(abs(w))), "unit": "EMU"},
            "height": {"magnitude": max(1, _emu(abs(h))), "unit": "EMU"},
        },
        "transform": {"scaleX": sx, "scaleY": sy, "translateX": _emu(x), "translateY": _emu(y), "unit": "EMU"},
    }


class _Canvas:
    def __init__(self, page_id: str, theme: Theme, prefix: str, offset: tuple[float, float],
                 resolve_asset=None, named: bool = False):
        self.page = page_id
        self.theme = theme
        self.prefix = prefix
        self.resolve_asset = resolve_asset
        self.named = named
        self.ox, self.oy = offset
        self.reqs: list[dict] = []
        self.ids: list[str] = []
        self.roles: dict[str, list[str]] = {}  # role (or op kind) → element ids, in drawing order
        self.role = "el"  # set by ops_to_requests before each op
        self._n = 0

    # -- helpers ---------------------------------------------------------------

    def new_id(self) -> str:
        """``<prefix>_<n>`` — or, named, ``<prefix>_<role>_<n>`` counted per role (``yt_top_slot_2``)."""
        key = self.role
        if self.named:
            oid = f"{self.prefix}_{key}_{len(self.roles.get(key, [])) + 1}"
        else:
            self._n += 1
            oid = f"{self.prefix}_{self._n:03d}"
        self.roles.setdefault(key, []).append(oid)
        return oid

    def rgb(self, value) -> dict:
        return {"rgbColor": self.theme.color(value)}

    def _slides_style(self, style: dict) -> tuple[dict, list[str]]:
        """Theme-style dict → (Slides TextStyle, fields)."""
        out: dict = {}
        fields: list[str] = []
        if style.get("font"):
            out["fontFamily"] = style["font"]
            fields.append("fontFamily")
        if style.get("size") is not None:
            out["fontSize"] = {"magnitude": style["size"], "unit": "PT"}
            fields.append("fontSize")
        for key in ("bold", "italic"):
            if style.get(key) is not None:
                out[key] = bool(style[key])
                fields.append(key)
        if style.get("color") is not None:
            out["foregroundColor"] = {"opaqueColor": self.rgb(style["color"])}
            fields.append("foregroundColor")
        if style.get("highlight"):
            out["backgroundColor"] = {"opaqueColor": self.rgb(style["highlight"])}
            fields.append("backgroundColor")
        return out, fields

    def _md_requests(self, oid: str, markdown: str, cell) -> tuple[list[dict], list[tuple[int, int]]]:
        """Writer requests for ``markdown`` with ``==x==`` spans extracted.

        The spans are carried through the writer as private-use sentinel
        characters, then stripped: every insertion index and range the writer
        computed is shifted back by the sentinels that preceded it.
        """
        import re

        md = re.sub(r"==(.+?)==", lambda m: HL_OPEN + m.group(1) + HL_CLOSE, markdown)
        reqs = md_requests(oid, md, cell=cell)
        if HL_OPEN not in md:
            return reqs, []
        # positions of the sentinels in the text as the writer inserts it
        marks: list[tuple[int, str]] = []
        for r in reqs:
            ins = r.get("insertText")
            if not ins:
                continue
            base = ins["insertionIndex"]
            pos = 0
            for ch in ins["text"]:
                if ch in (HL_OPEN, HL_CLOSE):
                    marks.append((base + pos, ch))
                pos += _utf16_len(ch)
        marks.sort()
        positions = [m[0] for m in marks]

        def shifted(i: int) -> int:
            return i - sum(1 for p in positions if p < i)

        spans: list[tuple[int, int]] = []
        open_at = None
        for p, ch in marks:
            if ch == HL_OPEN:
                open_at = p
            elif open_at is not None:
                spans.append((shifted(open_at), shifted(p)))
                open_at = None
        for r in reqs:
            if "insertText" in r:
                ins = r["insertText"]
                ins["insertionIndex"] = shifted(ins["insertionIndex"])
                ins["text"] = ins["text"].replace(HL_OPEN, "").replace(HL_CLOSE, "")
            for key in ("updateTextStyle", "createParagraphBullets", "updateParagraphStyle"):
                rng = r.get(key, {}).get("textRange")
                if rng and rng.get("type") == "FIXED_RANGE":
                    rng["startIndex"] = shifted(rng["startIndex"])
                    rng["endIndex"] = shifted(rng["endIndex"])
        return [r for r in reqs if not ("insertText" in r and r["insertText"]["text"] == "")], spans

    def _text_into(self, oid: str, op: dict, cell: tuple[int, int] | None = None) -> None:
        """insertText + styles for a shape or a table cell (empty target only)."""
        loc = {"cellLocation": {"rowIndex": cell[0], "columnIndex": cell[1]}} if cell else {}
        overrides = {k: op.get(k) for k in ("size", "bold", "italic", "color", "font")}
        base = self.theme.text_style(op.get("style"), **overrides)
        if base.get("color") is None and "text" in self.theme.roles:
            base["color"] = "text"
        floor = self.theme.size_floor(op.get("style"))
        if op.get("small_ok"):
            # the charter floor is a recommendation: a value that cannot get a wider box
            # (KPI in a narrow column, value over a thin bar) may go under it
            floor = None
            if op.get("size") is not None:
                base["size"] = op["size"]

        runs_ranges: list[tuple[int, int, dict]] = []
        md_styles: list[dict] = []
        if "markdown" in op:
            # text + bullets now; the writer's style requests go AFTER the base
            # style, because updating fontFamily resets the weight (bold) to 400
            md_reqs, spans = self._md_requests(oid, str(op["markdown"]), cell)
            hl = op.get("highlight") or "highlight"
            runs_ranges.extend((a, b, {"highlight": hl}) for a, b in spans)
            for r in md_reqs:
                if "updateTextStyle" not in r:
                    self.reqs.append(r)
                    continue
                # the writer sends fields "*", which would wipe font/size/color:
                # keep only what it actually sets (bold, italic, links…)
                st = r["updateTextStyle"].get("style") or {}
                if st:
                    r["updateTextStyle"]["fields"] = ",".join(st)
                    md_styles.append(r)
        else:
            if "runs" in op:
                paragraphs = [[dict(r) for r in para] for para in op["runs"]]
            else:
                paragraphs = [[{"text": str(op.get("text", ""))}]]
            pos = 0
            chunks: list[str] = []
            for p_i, para in enumerate(paragraphs):
                if p_i:
                    chunks.append("\n")
                    pos += 1
                for run in para:
                    t = str(run.get("text", ""))
                    n = _utf16_len(t)
                    extra = {k: run[k] for k in ("bold", "italic", "color", "size", "font", "highlight") if k in run}
                    if floor is not None and extra.get("size") is not None and extra["size"] < floor:
                        extra["size"] = floor
                    if extra and n:
                        runs_ranges.append((pos, pos + n, extra))
                    chunks.append(t)
                    pos += n
            full = "".join(chunks)
            if full:
                self.reqs.append({"insertText": {"objectId": oid, **loc, "text": full, "insertionIndex": 0}})

        style, fields = self._slides_style(base)
        if fields:
            self.reqs.append({"updateTextStyle": {
                "objectId": oid, **loc, "textRange": {"type": "ALL"}, "style": style, "fields": ",".join(fields),
            }})
        self.reqs.extend(md_styles)
        for start, end, extra in runs_ranges:
            style, fields = self._slides_style(extra)
            self.reqs.append({"updateTextStyle": {
                "objectId": oid, **loc,
                "textRange": {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end},
                "style": style, "fields": ",".join(fields),
            }})
        para_style: dict = {}
        para_fields: list[str] = []
        if op.get("align"):
            para_style["alignment"] = _ALIGN[str(op["align"]).upper()]
            para_fields.append("alignment")
        if op.get("spacing") is not None:
            para_style["spaceBelow"] = {"magnitude": op["spacing"], "unit": "PT"}
            para_fields.append("spaceBelow")
        if para_fields:
            self.reqs.append({"updateParagraphStyle": {
                "objectId": oid, **loc, "textRange": {"type": "ALL"}, "style": para_style, "fields": ",".join(para_fields),
            }})
        if op.get("valign") and cell is None:
            self.reqs.append({"updateShapeProperties": {
                "objectId": oid,
                "shapeProperties": {"contentAlignment": _VALIGN[str(op["valign"]).upper()]},
                "fields": "contentAlignment",
            }})

    # -- ops ---------------------------------------------------------------

    def box(self, op: dict) -> None:
        oid = self.new_id()
        self.reqs.append({"createShape": {
            "objectId": oid, "shapeType": op.get("shape", "RECTANGLE"),
            "elementProperties": _elem_props(self.page, op["x"] + self.ox, op["y"] + self.oy, op["w"], op["h"]),
        }})
        fill = op.get("fill")
        props: dict = {
            "shapeBackgroundFill": {"solidFill": {"color": self.rgb(fill)}} if fill else {"propertyState": "NOT_RENDERED"},
        }
        line = op.get("line")
        if line:
            props["outline"] = {
                "outlineFill": {"solidFill": {"color": self.rgb(line.get("color", "ink"))}},
                "weight": {"magnitude": line.get("weight", 1), "unit": "PT"},
            }
            if line.get("dash"):
                props["outline"]["dashStyle"] = str(line["dash"]).upper()
        else:
            props["outline"] = {"propertyState": "NOT_RENDERED"}
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": props, "fields": "shapeBackgroundFill,outline"}})
        self.ids.append(oid)
        if any(k in op for k in ("text", "runs", "markdown")):
            if op["w"] < SMALL_BOX_W or op["h"] < SMALL_BOX_H:
                # Google keeps 7.2 pt side insets and 3.6 pt top / bottom insets inside every shape: in a
                # numbered disc or a tiny tile that pushes the text off centre. The text goes into a
                # larger transparent box centred on the shape instead, so the insets cancel out.
                tw, th = max(op["w"], SMALL_BOX_W), max(op["h"], SMALL_BOX_H)
                self.text({**op, "x": op["x"] + (op["w"] - tw) / 2, "y": op["y"] + (op["h"] - th) / 2, "w": tw, "h": th,
                           "align": op.get("align", "CENTER"), "valign": op.get("valign", "MIDDLE")})
            else:
                self._text_into(oid, op)

    def text(self, op: dict) -> None:
        oid = self.new_id()
        self.reqs.append({"createShape": {
            "objectId": oid, "shapeType": "TEXT_BOX",
            "elementProperties": _elem_props(self.page, op["x"] + self.ox, op["y"] + self.oy, op["w"], op["h"]),
        }})
        self.ids.append(oid)
        self._text_into(oid, op)

    def line(self, op: dict) -> None:
        self._segment(op["x1"], op["y1"], op["x2"], op["y2"],
                      op.get("color", "ink"), op.get("weight", 1), op.get("dash"),
                      end_arrow=op.get("end_arrow"), start_arrow=op.get("start_arrow"))

    def _segment(self, x1, y1, x2, y2, color, weight, dash=None, end_arrow=None, start_arrow=None) -> None:
        oid = self.new_id()
        w, h = x2 - x1, y2 - y1
        self.reqs.append({"createLine": {
            "objectId": oid, "lineCategory": "STRAIGHT",
            "elementProperties": _elem_props(self.page, x1 + self.ox, y1 + self.oy, w, h,
                                             sx=-1 if w < 0 else 1, sy=-1 if h < 0 else 1),
        }})
        props = {"weight": {"magnitude": weight, "unit": "PT"}, "lineFill": {"solidFill": {"color": self.rgb(color)}}}
        fields = "weight,lineFill"
        if dash:
            props["dashStyle"] = dash
            fields += ",dashStyle"
        for key, value in (("endArrow", end_arrow), ("startArrow", start_arrow)):
            if value:
                props[key] = _ARROWS.get(str(value), str(value).upper())
                fields += "," + key
        self.reqs.append({"updateLineProperties": {"objectId": oid, "lineProperties": props, "fields": fields}})
        self.ids.append(oid)

    def polyline(self, op: dict) -> None:
        pts = op["points"]
        last = len(pts) - 2
        for i, ((x1, y1), (x2, y2)) in enumerate(zip(pts, pts[1:])):
            self._segment(x1, y1, x2, y2, op.get("color", "ink"), op.get("weight", 2), op.get("dash"),
                          end_arrow=op.get("end_arrow") if i == last else None)

    def arc(self, op: dict) -> None:
        self._arc(op["cx"], op["cy"], op["r"], op["a0"], op["a1"], op["weight"], op.get("color", "accent"))

    def _arc(self, cx, cy, r, a0, a1, weight, color, step: float = _ARC_STEP_DEG) -> None:
        """Thick-line arc: 1° chords, each stretched a hair so inner edges meet."""
        n = max(2, int(round(abs(a1 - a0) / step)))
        # Consecutive chords are rectangles rotated by ``step`` and leave a
        # wedge on their outer side; Google's rendering needs roughly six
        # times the naive (weight/2)*tan(step) to close it (calibrated on
        # rendered thumbnails). Interior joints get that overlap on both
        # sides; the arc's own ends stay sharp so colour boundaries don't
        # bleed, except a small lead-in that overwrites the previous arc.
        extend_pt = (weight / 2) * math.tan(math.radians(step)) * 6 + 0.5
        over = math.degrees(extend_pt / max(r, 1.0))
        lead = min(over, 0.6)
        sign = 1 if a1 >= a0 else -1
        for i in range(n):
            s0 = a0 + (a1 - a0) * i / n - sign * (over if i else lead)
            s1 = a0 + (a1 - a0) * (i + 1) / n + sign * (over if i < n - 1 else 0)
            t0, t1 = math.radians(s0), math.radians(s1)
            self._segment(cx + r * math.cos(t0), cy + r * math.sin(t0),
                          cx + r * math.cos(t1), cy + r * math.sin(t1), color, weight)

    def ring(self, op: dict) -> None:
        """Ring, or full pie when thickness == r: a few quarter-turn arcs, or radial spokes.

        ``render: "arcs"`` (default) paints each share with Google's ARC
        shape — a quarter turn with flat radial ends — outlined as thick as
        the ring, so a donut is a handful of elements instead of 360 (see
        ``arc_plan``). When no plan is exact (a partial ring whose last share
        is under a quarter turn and would spill past the end), or with
        ``render: "spokes"``, every share is one thin line per degree from
        the inner to the outer radius: radial edges, clean colour boundaries,
        but ~360 elements for a full turn.
        """
        segments = op["segments"]
        total = sum(float(s["value"]) for s in segments) or 1.0
        r_out = float(op["r"])
        r_in = max(0.0, r_out - min(float(op["thickness"]), r_out))
        full = float(op.get("span", 360))  # < 360 for gauges: the segments share that arc only
        shares, a = [], float(op.get("start", -90))
        for s in segments:
            span = full * float(s["value"]) / total
            if span > 0:
                shares.append((s.get("color", "accent"), a, a + span))
            a += span
        plan = arc_plan(shares, full) if op.get("render", "arcs") == "arcs" else None
        if plan is None:
            plan = [("spokes", color, a0, a1) for color, a0, a1 in shares]
        for kind, color, a0, a1 in plan:
            if kind == "arc":
                self._quarter_arc(op["cx"], op["cy"], (r_in + r_out) / 2, r_out - r_in, a0, color)
            else:
                self._spokes(op["cx"], op["cy"], r_in, r_out, a0, a1, color)

    def _spokes(self, cx, cy, r_in, r_out, a0, a1, color) -> None:
        """One line per degree across the ring; weight just enough for neighbours to overlap."""
        step = _ARC_STEP_DEG
        weight = max(2.5, 1.3 * r_out * math.tan(math.radians(step)))
        span = a1 - a0
        n = max(1, int(round(span / step)))
        for i in range(n):
            t = math.radians(a0 + span * (i + 0.5) / n)
            self._segment(cx + r_in * math.cos(t), cy + r_in * math.sin(t),
                          cx + r_out * math.cos(t), cy + r_out * math.sin(t), color, weight)

    def _quarter_arc(self, cx, cy, r_mid, thickness, a0, color) -> None:
        """Google's ARC preset (top → right, clockwise) turned to start at ``a0``, stroked ``thickness`` wide.

        The stroke is centred on the circle of radius ``r_mid`` and its ends
        are cut radially, so it covers exactly [a0, a0 + 90°] between
        r_mid ± thickness / 2. Rotation is an affine transform about the
        box centre (degrees clockwise, 0 = east, as everywhere here).
        """
        oid = self.new_id()
        phi = math.radians(a0 - 270.0)
        c, s = math.cos(phi), math.sin(phi)
        half = r_mid  # the box is the circle's square, 2 × r_mid
        self.reqs.append({"createShape": {
            "objectId": oid, "shapeType": "ARC",
            "elementProperties": {
                "pageObjectId": self.page,
                "size": {"width": {"magnitude": max(1, _emu(2 * r_mid)), "unit": "EMU"},
                         "height": {"magnitude": max(1, _emu(2 * r_mid)), "unit": "EMU"}},
                "transform": {"scaleX": c, "shearX": -s, "shearY": s, "scaleY": c,
                              "translateX": _emu(cx + self.ox - (c * half - s * half)),
                              "translateY": _emu(cy + self.oy - (s * half + c * half)), "unit": "EMU"},
            },
        }})
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": {
            "shapeBackgroundFill": {"propertyState": "NOT_RENDERED"},
            "outline": {"outlineFill": {"solidFill": {"color": self.rgb(color)}},
                        "weight": {"magnitude": round(thickness, 2), "unit": "PT"}, "dashStyle": "SOLID"},
        }, "fields": "shapeBackgroundFill,outline"}})
        self.ids.append(oid)

    def table(self, op: dict) -> None:
        rows = op["rows"]
        n_r, n_c = len(rows), max(len(r) for r in rows)
        row_h = op.get("row_h", 20)
        row_heights = list(op.get("row_heights") or [])
        row_heights = [float(row_heights[i]) if i < len(row_heights) and row_heights[i] else float(row_h) for i in range(n_r)]
        col_w = op.get("col_w") or [op["w"] / n_c] * n_c
        oid = self.new_id()
        self.reqs.append({"createTable": {
            "objectId": oid, "rows": n_r, "columns": n_c,
            "elementProperties": _elem_props(self.page, op["x"] + self.ox, op["y"] + self.oy, op["w"], sum(row_heights)),
        }})
        self.ids.append(oid)
        header = op.get("header")
        banding = op.get("banding")
        aligns = op.get("align") or []
        size = op.get("size")
        first_col_bold = op.get("first_col_bold", False)

        def fill_row(i: int, color) -> None:
            self.reqs.append({"updateTableCellProperties": {
                "objectId": oid,
                "tableRange": {"location": {"rowIndex": i, "columnIndex": 0}, "rowSpan": 1, "columnSpan": n_c},
                "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": self.rgb(color)}}},
                "fields": "tableCellBackgroundFill.solidFill.color",
            }})

        if header and header.get("fill"):
            fill_row(0, header["fill"])
        if banding:
            for i in range(1 if header else 0, n_r):
                fill_row(i, banding[(i - (1 if header else 0)) % len(banding)])
        for i, color in (op.get("row_fills") or {}).items():
            fill_row(int(i), color)
        for (ci, cj), color in (op.get("cell_fills") or {}).items():
            self.reqs.append({"updateTableCellProperties": {
                "objectId": oid,
                "tableRange": {"location": {"rowIndex": int(ci), "columnIndex": int(cj)}, "rowSpan": 1, "columnSpan": 1},
                "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": self.rgb(color)}}},
                "fields": "tableCellBackgroundFill.solidFill.color",
            }})
        cell_text_colors = {(int(a), int(b)): c for (a, b), c in (op.get("cell_text_colors") or {}).items()}
        cell_runs = {(int(a), int(b)): r for (a, b), r in (op.get("cell_runs") or {}).items()}
        bold_rows = {int(i) for i in op.get("bold_rows") or []}

        for i, row in enumerate(rows):
            for j in range(n_c):
                value = row[j] if j < len(row) else ""
                is_header = bool(header) and i == 0
                style_name = op.get("header_style", "table_header") if is_header else op.get("style", "table_cell")
                cell_op: dict = {
                    "text": str(value),
                    # default style names are a convenience: themes without them still work
                    "style": style_name if style_name in self.theme.text_styles else None,
                    "size": size,
                }
                if is_header:
                    cell_op["color"] = header.get("color")
                    cell_op["bold"] = header.get("bold", True)
                elif (first_col_bold and j == 0) or i in bold_rows:
                    cell_op["bold"] = True
                if j < len(aligns) and aligns[j]:
                    cell_op["align"] = aligns[j]
                if (i, j) in cell_text_colors:
                    cell_op["color"] = cell_text_colors[(i, j)]
                if (i, j) in cell_runs:  # styled runs (name + muted sub-line) instead of plain text
                    cell_op.pop("text", None)
                    cell_op["runs"] = cell_runs[(i, j)]
                    cell_op["bold"] = None
                elif str(value) == "":
                    # an empty cell keeps Google's 18 pt default paragraph and stretches its row:
                    # a styled space keeps the row at the table's text size
                    cell_op["text"] = " "
                self._text_into(oid, cell_op, cell=(i, j))

        for j, w in enumerate(col_w):
            self.reqs.append({"updateTableColumnProperties": {
                "objectId": oid, "columnIndices": [j],
                "tableColumnProperties": {"columnWidth": {"magnitude": _emu(w), "unit": "EMU"}},
                "fields": "columnWidth",
            }})
        for height in sorted(set(row_heights), key=row_heights.index):
            self.reqs.append({"updateTableRowProperties": {
                "objectId": oid, "rowIndices": [i for i, rh in enumerate(row_heights) if rh == height],
                "tableRowProperties": {"minRowHeight": {"magnitude": _emu(height), "unit": "EMU"}},
                "fields": "minRowHeight",
            }})
        borders = op.get("borders", {"color": "rule", "weight": 1})
        if borders is None:  # no "none" in the API: paint them in the background color
            borders = {"color": "background", "weight": 0.5}
        specs = [borders]
        if borders.get("position", "ALL") != "ALL":
            # hide the borders the spec doesn't cover (Google draws them black by default)
            specs.insert(0, {"color": "background", "weight": 0.5, "position": "ALL"})
        for spec in specs:
            self.reqs.append({"updateTableBorderProperties": {
                "objectId": oid, "borderPosition": spec.get("position", "ALL"),
                "tableBorderProperties": {
                    "tableBorderFill": {"solidFill": {"color": self.rgb(spec.get("color", "rule"))}},
                    "weight": {"magnitude": spec.get("weight", 1), "unit": "PT"},
                    "dashStyle": "SOLID",
                },
                "fields": "tableBorderFill,weight,dashStyle",
            }})

    def _hex6(self, value) -> str:
        c = self.theme.color(value)
        return "{:02x}{:02x}{:02x}".format(*(round(c[k] * 255) for k in ("red", "green", "blue")))

    def _drive_url(self, ref: str, tint=None) -> str:
        if self.resolve_asset is None:
            raise ValueError("image op with 'asset' or 'slot' needs an asset resolver (insert_component / draw provide one)")
        resolved = self.resolve_asset(ref, tint)
        file_id = resolved[0] if isinstance(resolved, tuple) else resolved
        return f"https://drive.google.com/uc?export=view&id={file_id}"

    def _slot(self, op: dict) -> None:
        """An image created from an empty-slot placeholder with the box's exact aspect.

        ``createImage`` fits a picture into the given size keeping *its* aspect, so a
        picture placed directly would shrink the element to its own shape. The
        placeholder has the box's aspect: the element's frame is the box, and the
        real picture (``asset`` / ``url``) goes in with ``replaceImage``, which
        keeps the frame — now and on every later replacement.
        """
        from .assets import slot_ref

        oid = self.new_id()
        x, y, w, h = op["x"], op["y"], op["w"], op["h"]
        ref = slot_ref(w, h, self._hex6(op.get("slot_fill", "surface")), self._hex6(op.get("slot_line", "divider")))
        self.reqs.append({"createImage": {
            "objectId": oid, "url": self._drive_url(ref),
            "elementProperties": _elem_props(self.page, x + self.ox, y + self.oy, w, h),
        }})
        self.ids.append(oid)
        source = self._drive_url(str(op["asset"]), op.get("tint")) if op.get("asset") else op.get("url")
        if source:
            self.reqs.append({"replaceImage": {
                "imageObjectId": oid, "url": source,
                "imageReplaceMethod": "CENTER_CROP" if op.get("fit") == "crop" else "CENTER_INSIDE",
            }})
        # CENTER_INSIDE shrinks the element to the picture: the frame is kept in the alt text, and
        # every replace_images puts it back before a swap. replaceImage clears the alt text, so it
        # is written after it (both verified live).
        self.reqs.append({"updatePageElementAltText": {
            "objectId": oid, "description": slot_frame_text(x + self.ox, y + self.oy, w, h),
        }})

    def image(self, op: dict) -> None:
        if op.get("slot"):
            self._slot(op)
            return
        oid = self.new_id()
        natural = None  # (w, h) of the source when the resolver knows it
        if op.get("asset"):
            if self.resolve_asset is None:
                raise ValueError("image op with 'asset' needs an asset resolver (insert_component / draw provide one)")
            resolved = self.resolve_asset(op["asset"], op.get("tint"))
            file_id, natural = resolved if isinstance(resolved, tuple) else (resolved, None)
            url = f"https://drive.google.com/uc?export=view&id={file_id}"
        else:
            url = op.get("url") or f"https://drive.google.com/uc?export=view&id={op['drive_file_id']}"
        x, y, w, h = op["x"], op["y"], op["w"], op["h"]
        if op.get("contain") and natural and natural[0] and natural[1]:
            # object-fit: contain — shrink the box to the source's aspect, centred
            src = natural[0] / natural[1]
            if src > w / h:
                nh = w / src
                y += (h - nh) / 2
                h = nh
            else:
                nw = h * src
                x += (w - nw) / 2
                w = nw
        self.reqs.append({"createImage": {
            "objectId": oid, "url": url,
            "elementProperties": _elem_props(self.page, x + self.ox, y + self.oy, w, h),
        }})
        self.ids.append(oid)
        if op.get("cover") and natural and natural[0] and natural[1]:
            # object-fit: cover — crop the source so it fills the box without distortion
            src, box = natural[0] / natural[1], op["w"] / op["h"]
            crop = {"leftOffset": 0.0, "rightOffset": 0.0, "topOffset": 0.0, "bottomOffset": 0.0}
            if src > box:
                crop["leftOffset"] = crop["rightOffset"] = (1 - box / src) / 2
            elif src < box:
                crop["topOffset"] = crop["bottomOffset"] = (1 - src / box) / 2
            if any(crop.values()):
                # Google wants all four offsets in one go ("cannot be updated individually")
                self.reqs.append({"updateImageProperties": {
                    "objectId": oid, "imageProperties": {"cropProperties": crop}, "fields": "cropProperties",
                }})


_OPS = ("box", "text", "line", "polyline", "arc", "ring", "table", "image")


def ops_to_requests(
    page_id: str,
    ops: list[dict],
    theme: Theme,
    prefix: str = "drw",
    offset: tuple[float, float] = (0, 0),
    group: str | None = None,
    resolve_asset=None,
    named: bool = False,
    roles_out: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Translate ops into batchUpdate requests. Returns (requests, element ids).

    ``prefix`` seeds every objectId (≥ 3 chars so ids satisfy the 5-char
    minimum); ``offset`` shifts every op; ``group`` names a groupObjects
    request wrapping all elements (only sent when there are at least two).
    ``named`` makes ids readable, ``<prefix>_<role>_<n>`` with the op's
    ``role`` (else its kind) counted per role; ``roles_out`` receives
    ``{role: [ids]}`` either way.
    """
    canvas = _Canvas(page_id, theme, prefix, offset, resolve_asset, named=named)
    for op in ops:
        kind = op.get("op")
        if kind not in _OPS:
            raise ValueError(f"unknown draw op {kind!r}; ops: {', '.join(_OPS)}")
        canvas.role = re.sub(r"[^A-Za-z0-9_-]", "_", str(op.get("role") or kind))[:18]
        getattr(canvas, kind)(op)
    if roles_out is not None:
        roles_out.update(canvas.roles)
    if group and len(canvas.ids) >= 2:
        canvas.reqs.append({"groupObjects": {"groupObjectId": group, "childrenObjectIds": list(canvas.ids)}})
    return canvas.reqs, canvas.ids
