"""Rewrite the texts of an already-designed deck in place, keeping their look.

``refill_text`` is for decks that are laid out already (a client template to
fill, last month's bilan to update): each shape or table cell gets new text
and keeps the style it had (font, weight, size, colour, highlight,
alignment). Variation cells (« +8 % », « -3,2 pts ») take the colour of
their sign, learnt from the deck itself before falling back to the theme.

The text model here (one string per text container, a style per character,
UTF-16 indexes for the API) is shared with ``replace_text(elements=…)``.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter

from .. import themes
from ..app import IDEMPOTENT, mcp
from ..auth import slide_service
from ..components.builtin import _is_delta_col
from ..util import find_element, parse_pres_id

DEFAULT_THEME = os.environ.get("GSLIDES_MCP_THEME", "periscope")

# TextStyle fields carried over to the new text (links are not: new text, new target)
_STYLE_FIELDS = ("bold", "italic", "underline", "strikethrough", "smallCaps", "baselineOffset",
                 "fontSize", "foregroundColor", "backgroundColor", "weightedFontFamily", "fontFamily")
_PARA_FIELDS = ("alignment", "lineSpacing", "spaceAbove", "spaceBelow")
_UP = re.compile(r"^\s*(?:\+\s*\d|[▲↑↗])")
_DOWN = re.compile(r"^\s*(?:[-−–]\s*\d|[▼↓↘])")


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def sign_of(text: str) -> str | None:
    """'up' for « +8 % » / « ▲ 3 », 'down' for « -3 % » / « −2 pts », None otherwise."""
    if _UP.match(text):
        return "up"
    if _DOWN.match(text):
        return "down"
    return None


# --- text containers -----------------------------------------------------------------------

def containers(el: dict) -> list[tuple[tuple[int, int] | None, dict]]:
    """``(cell, text)`` for every text container of a page element: one for a shape, one per table cell."""
    if "shape" in el:
        return [(None, el["shape"].get("text") or {})]
    if "table" in el:
        out = []
        for i, row in enumerate(el["table"].get("tableRows", [])):
            for j, cell in enumerate(row.get("tableCells", [])):
                loc = cell.get("location") or {}
                out.append(((loc.get("rowIndex", i), loc.get("columnIndex", j)), cell.get("text") or {}))
        return out
    return []


def walk(elements: list):
    """Every page element, groups opened."""
    for el in elements:
        yield el
        children = el.get("elementGroup", {}).get("children", [])
        if children:
            yield from walk(children)


def text_of(text: dict) -> tuple[list[str], list[dict]]:
    """The container's characters and, for each, the TextStyle of its run."""
    chars: list[str] = []
    styles: list[dict] = []
    for te in text.get("textElements", []):
        run = te.get("textRun") or te.get("autoText")
        if not run:
            continue
        content = run.get("content", "")
        style = run.get("style") or {}
        chars.extend(content)
        styles.extend([style] * len(content))
    return chars, styles


def has_text(text: dict) -> bool:
    return any(te.get("textRun", {}).get("content", "") not in ("", "\n") for te in text.get("textElements", []))


def first_style(text: dict) -> dict | None:
    """TextStyle of the first run that holds visible text, or None."""
    for te in text.get("textElements", []):
        run = te.get("textRun")
        if run and run.get("content", "").strip():
            return run.get("style") or {}
    return None


def para_style(text: dict) -> dict:
    for te in text.get("textElements", []):
        marker = te.get("paragraphMarker")
        if marker is not None:
            st = marker.get("style") or {}
            return {k: st[k] for k in _PARA_FIELDS if k in st}
    return {}


def runs(text: dict) -> list[dict]:
    """The container's runs: ``[{text, start, end, style}]``, UTF-16 indexes.

    A run is a stretch of one style within a line, without its outer spaces
    (they stay where they are). Line breaks, slide numbers (autoText) and
    blank stretches are not runs and are never rewritten.
    """
    stretches: list[dict] = []
    cur: dict | None = None
    pos = 0
    for te in text.get("textElements", []):
        run, editable = te.get("textRun"), True
        if run is None:
            run, editable = te.get("autoText"), False
        if not run:
            continue
        style = run.get("style") or {}
        for ch in run.get("content", ""):
            n = utf16_len(ch)
            if ch in "\n\u000b" or not editable:
                cur = None
            elif cur is not None and cur["style"] == style:
                cur["chars"] += ch
            else:
                cur = {"chars": ch, "start": pos, "style": style}
                stretches.append(cur)
            pos += n
    out = []
    for s in stretches:
        core = s["chars"].strip()
        if core:
            start = s["start"] + utf16_len(s["chars"][:len(s["chars"]) - len(s["chars"].lstrip())])
            out.append({"text": core, "start": start, "end": start + utf16_len(core), "style": s["style"]})
    return out


def describe_run(run: dict) -> dict:
    """``{text, size?, bold?, color?}``: what tells one run from another."""
    st = run["style"]
    out: dict = {"text": run["text"]}
    size = (st.get("fontSize") or {}).get("magnitude")
    if size:
        out["size"] = size
    if st.get("bold"):
        out["bold"] = True
    color = _describe(st.get("foregroundColor"))
    if color:
        out["color"] = color
    return out


def _run_label(run: dict) -> str:
    d = describe_run(run)
    size = f" {d['size']:g} pt" if "size" in d else ""
    return f"«{d['text']}»{size}{' bold' if d.get('bold') else ''}{' ' + d['color'] if 'color' in d else ''}"


def style_request(oid: str, style: dict, loc: dict, text_range: dict) -> dict | None:
    """updateTextStyle that re-applies ``style`` field by field (never fields "*")."""
    keep = {k: style[k] for k in _STYLE_FIELDS if k in style}
    if "weightedFontFamily" in keep:
        keep.pop("fontFamily", None)  # the weighted family carries the family; setting both resets the weight
    if not keep:
        return None
    return {"updateTextStyle": {"objectId": oid, **loc, "textRange": text_range, "style": keep,
                                "fields": ",".join(keep)}}


def _loc(cell) -> dict:
    return {"cellLocation": {"rowIndex": cell[0], "columnIndex": cell[1]}} if cell else {}


def covered_cells(table: dict) -> dict[tuple[int, int], tuple[int, int]]:
    """Cells hidden by a merge → the head cell that holds their text."""
    out: dict[tuple[int, int], tuple[int, int]] = {}
    for i, row in enumerate(table.get("tableRows", [])):
        for j, cell in enumerate(row.get("tableCells", [])):
            loc = cell.get("location") or {}
            r, c = loc.get("rowIndex", i), loc.get("columnIndex", j)
            for a in range(r, r + cell.get("rowSpan", 1)):
                for b in range(c, c + cell.get("columnSpan", 1)):
                    if (a, b) != (r, c):
                        out[(a, b)] = (r, c)
    return out


def _cell_text(table: dict, r: int, c: int) -> dict | None:
    try:
        return table["tableRows"][r]["tableCells"][c].get("text") or {}
    except (KeyError, IndexError):
        return None


def _plain(text: dict | None) -> str:
    return "".join(text_of(text or {})[0]).strip()


def _borrowed_style(table: dict, r: int, c: int) -> tuple[dict | None, str]:
    """Style for an empty cell: a filled cell of the same column (same kind of row), else of the same row."""
    n_rows = len(table.get("tableRows", []))
    order = [i for i in range(r + 1, n_rows)] + [i for i in range(r - 1, -1, -1)]
    for i in order:
        if (i == 0) != (r == 0):  # header takes the header's look, body rows a body row's
            continue
        st = first_style(_cell_text(table, i, c) or {})
        if st is not None:
            return st, "column"
    row = table["tableRows"][r].get("tableCells", [])
    for j in sorted(range(len(row)), key=lambda j: abs(j - c)):
        st = first_style(_cell_text(table, r, j) or {})
        if st is not None:
            return st, "row"
    return None, "none"


# --- sign colours ---------------------------------------------------------------------------

def _key(color) -> str:
    return json.dumps(color, sort_keys=True)


def _learn(texts: list[dict]) -> dict[str, dict]:
    """Majority text colour of signed values, by sign, when the deck tells them apart.

    A signed value is a whole cell or shape (« +8 % »), or the run of a KPI
    block that its colour sets apart from the rest of the block.
    """
    seen: dict[str, Counter] = {"up": Counter(), "down": Counter()}
    colors: dict[str, dict] = {}

    def vote(sign: str, color: dict) -> None:
        k = _key(color)
        seen[sign][k] += 1
        colors[k] = color

    for text in texts:
        sign = sign_of(_plain(text))
        st = first_style(text)
        if sign and st and st.get("foregroundColor"):
            vote(sign, st["foregroundColor"])
            continue
        rs = runs(text)
        for r in rs:
            color, sign = r["style"].get("foregroundColor"), sign_of(r["text"])
            if sign and color and any(_key(o["style"].get("foregroundColor")) != _key(color) for o in rs if o is not r):
                vote(sign, color)
    out = {s: colors[c.most_common(1)[0][0]] for s, c in seen.items() if c}
    if "up" in out and "down" in out and _key(out["up"]) == _key(out["down"]):
        return {"same": out["up"]}  # one colour for both signs: the deck does not colour by sign
    return out


def _describe(color: dict | None) -> str | None:
    if not color:
        return None
    oc = color.get("opaqueColor", {})
    if "rgbColor" in oc:
        rgb = oc["rgbColor"]
        return "#{:02X}{:02X}{:02X}".format(*(round(rgb.get(k, 0) * 255) for k in ("red", "green", "blue")))
    if "themeColor" in oc:
        return f"theme:{oc['themeColor']}"
    return None


def _as_color(theme: themes.Theme, value: str) -> dict:
    return {"opaqueColor": {"rgbColor": theme.color(value)}}


# --- the tool --------------------------------------------------------------------------------

@mcp.tool(annotations=IDEMPOTENT)
def refill_text(presentation: str, edits: list[dict], up_color: str | None = None,
                down_color: str | None = None) -> dict:
    """Rewrite shapes and table cells of an already-designed deck, keeping each one's style.

    For a deck that is laid out already — a client template whose slides are
    kept and filled, last month's bilan updated with this month's figures —
    where ``set_table_cell`` / ``write_text_markdown`` would reset the look.
    Each target keeps the font, weight, size, colour, highlight and alignment
    of its current first run; an empty cell borrows the style of a filled
    cell in the same column (header from header, body from body), then of
    the same row. All edits go in one batchUpdate.

    A block whose parts have their own look (a KPI: figure 30 pt, label
    11 pt, variation in green) is refilled run by run: ``runs`` instead of
    ``text``, one entry per run of the current text, in reading order —
    a string rewrites that run in its own style, ``null`` leaves it. A run
    is a stretch of one style within a line, outer spaces left out; line
    breaks stay. ``inspect_slide`` lists the runs of a shape that mixes
    styles; a wrong count is refused with the runs listed.

    Variation colours: a value that starts with a sign (``+8 %``, ``-3,2 pts``,
    ``−12``, ``▲ 4``) is recoloured by its sign when the target is a
    variation — a cell of a « vs N-1 » / « Évol. » / « Var. » / « Δ »
    column or of a column of signed values, or any cell or shape whose
    current text is already signed. The colours come from ``up_color`` /
    ``down_color`` when given, else from the deck itself (the colours its
    signed values already use: same table first, then the whole deck), else
    from the theme (``positive`` / ``negative``). A deck that shows both
    signs in one colour is left in that colour. With ``runs``, each run is
    judged on its own: the variation run of a KPI is recoloured, the figure
    and the label keep theirs.

    Args:
        edits: ``{element, text}`` for a shape (text box, placeholder, card),
            ``{element, row, column, text}`` for a table cell (0-based; a
            cell hidden by a merge is refused, write its head cell; ``""``
            leaves a styled space so the row keeps its height).
            Plain text, ``\\n`` for a new line; no markdown (use
            ``write_text_markdown`` for bold parts). ``runs`` in place of
            ``text`` (see above). Optional ``delta``:
            ``"auto"`` (default, as above), ``true`` (colour by sign
            whatever the column), ``false`` (keep the colour), ``"inverse"``
            (lower is better — CPC, CPA, taux de rebond: a « - » is good news
            and takes the up colour).
        up_color, down_color: hex (``#1A9E5C``) or theme role (``positive``)
            to force the colours of good and bad variations.

    Returns: ``{edited, edits: [{element, row?, column?, style_from, delta?,
    runs?: [{index, text, delta?}]}], colors: {up, down, source}}`` —
    ``style_from`` is ``self``, ``column``, ``row`` or ``none`` (nothing to
    copy: the placeholder's own style applies); ``runs`` lists the runs
    rewritten (an unchanged one is not sent).

    Example::

        refill_text(deck, [
            {"element": "g3a1_kpi_value", "text": "12 400"},
            {"element": "g3a1_kpi_delta", "text": "-4 %"},
            {"element": "g3a1_kpi_block", "runs": ["13 100", None, "-2 %", None]},
            {"element": "tbl_regies", "row": 1, "column": 2, "text": "46 811 €"},
            {"element": "tbl_regies", "row": 1, "column": 3, "text": "+52,18 %"},
            {"element": "tbl_regies", "row": 2, "column": 5, "text": "-0,12 €", "delta": "inverse"},
        ])
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    reqs, out = plan_refill(pres, edits, up_color, down_color)
    if reqs:
        svc.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute()
    return out


def _check_runs(n: int, given, where: str, current: list[dict]) -> None:
    """Refuse a ``runs`` list that does not match the target's runs, listing them."""
    if not isinstance(given, list):
        raise ValueError(f"edit #{n + 1}: runs must be a list, one entry per run (null keeps a run), got {given!r}")
    if not current:
        raise ValueError(f"edit #{n + 1}: {where} has no run to rewrite: give 'text'")
    if len(given) != len(current):
        listed = " · ".join(_run_label(r) for r in current)
        raise ValueError(f"edit #{n + 1}: {where} has {len(current)} runs, got {len(given)}: {listed}"
                         " — one entry per run, null keeps a run")
    bad = [r for r in given if r is not None and not isinstance(r, (str, int, float))]
    if bad:
        raise ValueError(f"edit #{n + 1}: each run is a string or null, got {bad[0]!r}")


def plan_refill(pres: dict, edits: list[dict], up_color: str | None = None,
                down_color: str | None = None) -> tuple[list[dict], dict]:
    """``refill_text``'s requests and result for ``edits`` on a presentation already read; nothing is sent.

    Everything is checked before any request is built, so a wrong edit
    raises and nothing is written. ``sync_table`` and ``sync_deck`` plan
    their text changes through here.
    """
    if not edits:
        raise ValueError("edits is empty: give {element, text} or {element, row, column, text} items")
    theme = themes.load(DEFAULT_THEME)

    # resolve targets first: nothing is written when one edit is wrong
    resolved = []
    seen: set[tuple] = set()
    for n, e in enumerate(edits):
        if "element" not in e or ("text" not in e and "runs" not in e):
            raise ValueError(f"edit #{n + 1} needs 'element' and 'text' or 'runs' (and row / column for a table cell): {e!r}")
        if "text" in e and "runs" in e:
            raise ValueError(f"edit #{n + 1}: give either 'text' or 'runs', not both")
        oid = str(e["element"])
        el, _slide = find_element(pres, oid)
        if el is None:
            raise ValueError(f"edit #{n + 1}: element not found: {oid!r}")
        delta = e.get("delta", "auto")
        if delta not in ("auto", True, False, "inverse"):
            raise ValueError(f"edit #{n + 1}: delta must be 'auto', true, false or 'inverse', got {delta!r}")
        if "table" in el:
            if e.get("row") is None or e.get("column") is None:
                raise ValueError(f"edit #{n + 1}: {oid!r} is a table: give row and column (0-based)")
            r, c = int(e["row"]), int(e["column"])
            n_r, n_c = el["table"].get("rows", 0), el["table"].get("columns", 0)
            if not (0 <= r < n_r and 0 <= c < n_c):
                raise ValueError(f"edit #{n + 1}: cell ({r}, {c}) is outside table {oid} ({n_r}x{n_c}, 0-based)")
            head = covered_cells(el["table"]).get((r, c))
            if head:
                raise ValueError(f"edit #{n + 1}: cell ({r}, {c}) of {oid} is merged into {head}: write that cell instead")
            text = _cell_text(el["table"], r, c)
            if text is None:
                raise ValueError(f"edit #{n + 1}: cell ({r}, {c}) of {oid} is merged into another cell")
            cell = (r, c)
        elif "shape" in el:
            if e.get("row") is not None or e.get("column") is not None:
                raise ValueError(f"edit #{n + 1}: {oid!r} is a shape, not a table: drop row / column")
            text, cell = el["shape"].get("text") or {}, None
        else:
            raise ValueError(f"edit #{n + 1}: {oid!r} holds no text (image, line, chart or group)")
        key = (oid, cell)
        if key in seen:
            raise ValueError(f"edit #{n + 1}: {oid!r} {cell or ''} is edited twice")
        seen.add(key)
        if "runs" in e:
            _check_runs(n, e["runs"], f"{oid}{f' cell {cell}' if cell else ''}", runs(text))
        resolved.append((e, oid, el, cell, text, delta))

    # sign colours: arguments, then this table, then the deck, then the theme
    all_texts = [t for s in pres.get("slides", []) for el in walk(s.get("pageElements", [])) for _c, t in containers(el)]
    deck_learnt = _learn(all_texts)
    fallback = {"up": _as_color(theme, "positive"), "down": _as_color(theme, "negative")}

    def colors_for(el: dict) -> tuple[dict, dict] | None:
        """(up, down) colours for a target, or None when the deck deliberately does not colour by sign."""
        local = _learn([t for _c, t in containers(el)]) if "table" in el else {}
        picked, sources = {}, {}
        for sign, arg in (("up", up_color), ("down", down_color)):
            if arg:
                picked[sign], sources[sign] = _as_color(theme, arg), "args"
            elif sign in local:
                picked[sign], sources[sign] = local[sign], "table"
            elif "same" in local:
                return None
            elif sign in deck_learnt:
                picked[sign], sources[sign] = deck_learnt[sign], "deck"
            elif "same" in deck_learnt:
                return None
            else:
                picked[sign], sources[sign] = fallback[sign], "theme"
        used_sources.update(sources.values())
        return picked["up"], picked["down"]

    def in_delta_col(el: dict, cell: tuple[int, int], new: str) -> bool:
        table = el["table"]
        rows = [[_plain(_cell_text(table, i, j)) for j in range(table.get("columns", 0))]
                for i in range(table.get("rows", 0))]
        rows[cell[0]][cell[1]] = new
        return cell[0] > 0 and _is_delta_col(rows, cell[1], 1, len(rows), rows[0])

    def recolour(style: dict, new: str, was_signed: bool, delta_col: bool, delta, el: dict) -> str | None:
        """Give ``style`` the colour of ``new``'s sign when it is a variation; the entry's ``delta``, or None."""
        sign = sign_of(new)
        if not sign or not (delta in (True, "inverse") or (delta == "auto" and (was_signed or delta_col))):
            return None
        pair = colors_for(el)
        if pair is None:
            return "kept"  # the deck shows both signs in one colour
        good = sign if delta != "inverse" else ("down" if sign == "up" else "up")
        style["foregroundColor"] = pair[0] if good == "up" else pair[1]
        reported_colors.update(up=_describe(pair[0]), down=_describe(pair[1]))
        return good

    used_sources: set[str] = set()
    reported_colors: dict = {}
    reqs: list[dict] = []
    report = []
    for e, oid, el, cell, text, delta in resolved:
        loc = _loc(cell)
        entry: dict = {"element": oid, "style_from": "self"}
        if cell:
            entry.update(row=cell[0], column=cell[1])

        if "runs" in e:
            current = runs(text)
            news = [None if r is None else str(r) for r in e["runs"]]
            new_plain = " ".join(c["text"] if r is None else r for c, r in zip(current, news))
            delta_col = bool(cell) and delta == "auto" and in_delta_col(el, cell, new_plain)
            done = []
            for i in reversed(range(len(current))):  # last run first: the indexes before it stay valid
                run, new = current[i], news[i]
                if new is None:
                    continue
                style = dict(run["style"])
                d = recolour(style, new, sign_of(run["text"]) is not None, delta_col, delta, el)
                if new == run["text"] and style == run["style"]:
                    continue
                if new != run["text"]:
                    reqs.append({"deleteText": {"objectId": oid, **loc, "textRange": {
                        "type": "FIXED_RANGE", "startIndex": run["start"], "endIndex": run["end"]}}})
                    if new:
                        reqs.append({"insertText": {"objectId": oid, **loc, "text": new, "insertionIndex": run["start"]}})
                st = style_request(oid, style, loc, {
                    "type": "FIXED_RANGE", "startIndex": run["start"], "endIndex": run["start"] + utf16_len(new)}) if new else None
                if st:
                    reqs.append(st)
                done.append({"index": i, "text": new, **({"delta": d} if d else {})})
            entry["runs"] = done[::-1]
            report.append(entry)
            continue

        new = str(e["text"])
        if cell and not new:
            new = " "  # an empty cell falls back to Slides' 18 pt default paragraph and its row grows
        style = first_style(text)
        if style is None:
            style, entry["style_from"] = _borrowed_style(el["table"], *cell) if cell else (None, "none")
        style = dict(style or {})
        delta_col = bool(cell) and delta == "auto" and in_delta_col(el, cell, new)
        d = recolour(style, new, sign_of(_plain(text)) is not None, delta_col, delta, el)
        if d:
            entry["delta"] = d

        if has_text(text):
            reqs.append({"deleteText": {"objectId": oid, **loc, "textRange": {"type": "ALL"}}})
        if new:
            reqs.append({"insertText": {"objectId": oid, **loc, "text": new, "insertionIndex": 0}})
            st = style_request(oid, style, loc, {"type": "ALL"})
            if st:
                reqs.append(st)
            ps = para_style(text)
            if ps:
                reqs.append({"updateParagraphStyle": {"objectId": oid, **loc, "textRange": {"type": "ALL"},
                                                      "style": ps, "fields": ",".join(ps)}})
        report.append(entry)

    out: dict = {"edited": len(report), "edits": report}
    if reported_colors:
        out["colors"] = {**reported_colors, "source": "+".join(sorted(used_sources))}
    return reqs, out
