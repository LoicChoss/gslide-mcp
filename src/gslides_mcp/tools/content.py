"""Content-level tools: write_text_markdown, set_text, style_text, replace_text.

write_text_markdown is the killer tool — uses gslides-api's markdown writer
which handles bold/italic/bullets in ONE call and roundtrips cleanly. Replaces
the old set_text + style_text + bullet_text + unbold-then-rebold-lead dance.
"""

from __future__ import annotations

from gslides_api import Presentation
from gslides_api.element.shape import ShapeElement

from ..app import ADDITIVE, IDEMPOTENT, mcp
from ..auth import client, slide_service
from ..util import find_element, parse_pres_id, parse_range, rgb_color, resolve_slide_ids
from . import refill


@mcp.tool(annotations=IDEMPOTENT)
def write_text_markdown(presentation: str, element: str, markdown: str) -> dict:
    """Write markdown content to a text-bearing element.

    Replaces the element's text and applies bold/italic/bullets/etc from the
    markdown. **Use this instead of set_text + style_text whenever possible.**
    Eliminates the unbold-everything-then-rebold-lead dance after replaceAllText.

    Markdown supports:
        - **bold**, *italic*
        - bullet lists (`- item`)
        - inline mix (e.g. `**Lead phrase.** rest of sentence`)

    Args:
        element: text-bearing element objectId (must already exist on a slide).
        markdown: e.g. `**Lead phrase.** rest of sentence.`

    For 2+ edits on the same deck, prefer ``batch_write_markdown`` — it
    folds all edits into ONE batchUpdate, ~N× faster.
    """
    pid = parse_pres_id(presentation)
    c = client()
    pres = Presentation.from_id(pid, api_client=c)
    target_el = None
    for slide in pres.slides:
        for el in (slide.pageElements or []):
            if el.objectId == element and isinstance(el, ShapeElement):
                target_el = el
                break
        if target_el:
            break
    if target_el is None:
        raise ValueError(f"text-bearing element not found: {element!r}")
    target_el.write_text(markdown, as_markdown=True, api_client=c)
    c.flush_batch_update()
    return {"element": element, "content_length": len(markdown)}


@mcp.tool(annotations=IDEMPOTENT)
def batch_write_markdown(presentation: str, edits: list[dict]) -> dict:
    """Apply markdown to MULTIPLE elements in a single batchUpdate. ~N× faster.

    The killer tool for slide rewrites. Where ``write_text_markdown`` is one
    HTTP round trip per element (~1-2s each), this tool buffers every edit
    via gslides-api's deferred-flush mode, then sends all generated requests
    (deleteText / insertText / updateTextStyle / createParagraphBullets / …)
    in a single ``batchUpdate`` at the end. A 9-edit slide goes from ~15-20s
    sequential to ~2-3s.

    Args:
        edits: list of ``{"element": <objectId>, "markdown": <md>}``. Each
            element must already exist on a slide. Order is preserved.

    Returns: ``{edits: [{element, ok, content_length, error?}], total, succeeded}``.

    **Atomicity:** the underlying batchUpdate is atomic — if any one element's
    request set fails, the whole batch is rejected. Per-element errors before
    flush (element not found, not text-bearing) are reported in ``edits``
    with ``ok: False`` and the rest still flush together.

    **Use this whenever** rewriting 2+ text elements on the same deck —
    cards, columns, multiple slides, doesn't matter. Always prefer this
    over a loop of ``write_text_markdown`` calls.
    """
    if not edits:
        return {"edits": [], "total": 0, "succeeded": 0}

    pid = parse_pres_id(presentation)
    c = client()
    pres = Presentation.from_id(pid, api_client=c)

    by_id: dict[str, ShapeElement] = {}
    for slide in pres.slides:
        for el in (slide.pageElements or []):
            if isinstance(el, ShapeElement):
                by_id[el.objectId] = el

    prior_auto_flush = c.auto_flush
    c.auto_flush = False
    results: list[dict] = []
    try:
        for edit in edits:
            element_id = edit.get("element")
            md = edit.get("markdown")
            if element_id is None or md is None:
                results.append({
                    "element": element_id, "ok": False,
                    "error": "each edit needs 'element' and 'markdown' keys",
                })
                continue
            target = by_id.get(element_id)
            if target is None:
                results.append({
                    "element": element_id, "ok": False,
                    "error": "element not found or not text-bearing",
                })
                continue
            try:
                target.write_text(md, as_markdown=True, api_client=c)
                results.append({
                    "element": element_id, "ok": True,
                    "content_length": len(md),
                })
            except Exception as exc:
                results.append({
                    "element": element_id, "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                })
        c.flush_batch_update()
    finally:
        c.auto_flush = prior_auto_flush

    succeeded = sum(1 for r in results if r.get("ok"))
    return {"edits": results, "total": len(results), "succeeded": succeeded}


@mcp.tool(annotations=IDEMPOTENT)
def set_text(presentation: str, element: str, text: str) -> dict:
    """Replace plain text on an element. Use write_text_markdown for any styling.

    Use this when you genuinely just want plain text and don't want markdown
    parsing. For styled content, prefer write_text_markdown. To refill the
    shapes and cells of a designed deck and keep each one's style,
    ``refill_text`` (many edits, one call).
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()
    pres = svc.presentations().get(presentationId=pid).execute()

    target = None
    for slide in pres.get("slides", []):
        for el in slide.get("pageElements", []):
            if el.get("objectId") == element:
                target = el
                break
        if target:
            break
    if target is None:
        raise ValueError(f"element not found: {element!r}")

    has_text = bool(target.get("shape", {}).get("text", {}).get("textElements"))
    reqs = []
    if has_text:
        reqs.append({"deleteText": {"objectId": element, "textRange": {"type": "ALL"}}})
    reqs.append({"insertText": {"objectId": element, "text": text}})
    svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": reqs}
    ).execute()
    return {"element": element, "length": len(text)}


@mcp.tool(annotations=IDEMPOTENT)
def style_text(
    presentation: str,
    element: str,
    text_range: str = "ALL",
    bold: bool | None = None,
    italic: bool | None = None,
    font: str | None = None,
    weight: int | None = None,
    size_pt: float | None = None,
    color_hex: str | None = None,
) -> dict:
    """Apply text style to a range. Use write_text_markdown for new content;
    use this for fine-tuning (e.g. font, color) after the fact.

    Args:
        text_range: 'ALL' or 'START:END' (character indexes).
        weight: numeric font weight (e.g. 500 for medium, 600 for semibold).
            Combine with `font` — sets weightedFontFamily under the hood.
    """
    pid = parse_pres_id(presentation)
    style: dict = {}
    fields: list[str] = []
    if bold is not None:
        style["bold"] = bold
        fields.append("bold")
    if italic is not None:
        style["italic"] = italic
        fields.append("italic")
    if font:
        style["fontFamily"] = font
        fields.append("fontFamily")
        if weight:
            style["weightedFontFamily"] = {"fontFamily": font, "weight": weight}
            fields.append("weightedFontFamily")
    if size_pt is not None:
        style["fontSize"] = {"magnitude": size_pt, "unit": "PT"}
        fields.append("fontSize")
    if color_hex:
        style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb_color(color_hex)}}
        fields.append("foregroundColor")
    if not fields:
        raise ValueError("provide at least one styling argument")

    slide_service().presentations().batchUpdate(
        presentationId=pid,
        body={"requests": [{"updateTextStyle": {
            "objectId": element,
            "textRange": parse_range(text_range),
            "style": style,
            "fields": ",".join(fields),
        }}]},
    ).execute()
    return {"element": element, "applied": fields, "range": text_range}


@mcp.tool(annotations=ADDITIVE)
def replace_text(
    presentation: str,
    find: str | None = None,
    replace: str | None = None,
    pairs: list[dict] | None = None,
    slides: list[str] | None = None,
    match_case: bool = False,
    elements: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Find-and-replace text across the deck, with optional scope and batching.

    Call shapes:
        - Single pair, whole deck: ``replace_text(p, find='X', replace='Y')``
        - Single pair, slide-scoped: ``replace_text(p, find='X', replace='Y', slides=[1,3])``
        - Element-scoped: ``replace_text(p, find='X', replace='Y', elements=['g1_title', 'tbl_1'])``
        - Batch pairs: ``replace_text(p, pairs=[{'find':'X','replace':'Y'}, ...])``
          (each pair may set its own ``match_case``; can be combined with
          ``slides=`` or ``elements=``)

    Scope trap: ``slides=`` replaces EVERY occurrence on those slides — a
    label « nouveau levier » also changes inside the analysis paragraph that
    quotes it. When a phrase may appear in more than one place, run
    ``dry_run=True`` first: it lists each match (slide, element, cell, the
    words around it) and writes nothing; then pass ``elements=`` with only
    the shapes / tables to change.

    Style: the new text keeps the style of the text it replaces (Slides does
    it for the deck and slide scopes; the element scope re-applies the
    style of the first replaced character). For bold parts, follow up with
    write_text_markdown; to rewrite a whole shape or cell, ``refill_text``.

    When occurrences = 0 for a pair, returns ``near_misses`` candidates from
    the deck text (top 3 strings within edit distance ≤2 or matching after
    HTML-entity / smart-quote / case normalization). Catches the silent
    mismatch traps (``&amp;`` vs ``&``, smart vs straight quotes, etc.).

    Args:
        slides: optional list of slide refs (1-based ints, str-ints, or
            objectIds) to scope replacements. None = whole deck.
        elements: objectIds of the shapes and tables (every cell) to
            replace in, and nowhere else. Not with ``slides``.
        pairs: list of ``{'find': str, 'replace': str, 'match_case': bool?}``
            for batch operations, applied in order in one ``batchUpdate``.
        dry_run: list the matches (``where``) and write nothing.

    Returns: ``{results: [{find, replace, occurrences, where?, near_misses?}],
    total[, dry_run]}`` — ``where`` (dry run and element scope) is
    ``[{slide, element, row?, column?, count, context}]``.
    """
    pid = parse_pres_id(presentation)
    svc = slide_service()

    work: list[dict] = []
    if pairs:
        if find is not None or replace is not None:
            raise ValueError("pass either pairs= OR find=/replace=, not both")
        for p in pairs:
            if "find" not in p or "replace" not in p:
                raise ValueError(f"each pair needs 'find' and 'replace' keys, got {p!r}")
            work.append({
                "find": p["find"],
                "replace": p["replace"],
                "match_case": bool(p.get("match_case", match_case)),
            })
    else:
        if find is None or replace is None:
            raise ValueError("provide find= and replace=, or pairs=")
        work.append({"find": find, "replace": replace, "match_case": match_case})
    if any(not w["find"] for w in work):
        raise ValueError("find must not be empty")
    if elements and slides:
        raise ValueError("pass slides= or elements=, not both: elements already names where to replace")

    if elements or dry_run:
        return _replace_scanned(svc, pid, work, slides, elements, dry_run)

    page_object_ids: list[str] | None = None
    if slides:
        page_object_ids = resolve_slide_ids(svc, pid, slides)

    requests = []
    for w in work:
        req = {
            "replaceAllText": {
                "containsText": {"text": w["find"], "matchCase": w["match_case"]},
                "replaceText": w["replace"],
            }
        }
        if page_object_ids:
            req["replaceAllText"]["pageObjectIds"] = page_object_ids
        requests.append(req)

    resp = svc.presentations().batchUpdate(
        presentationId=pid, body={"requests": requests}
    ).execute()

    results = []
    needs_near_miss = False
    for w, reply in zip(work, resp.get("replies", [])):
        occ = reply.get("replaceAllText", {}).get("occurrencesChanged", 0)
        entry = {"find": w["find"], "replace": w["replace"], "occurrences": occ}
        if occ == 0:
            needs_near_miss = True
        results.append(entry)

    if needs_near_miss:
        all_text = _gather_deck_text(svc, pid, page_object_ids)
        for entry in results:
            if entry["occurrences"] == 0:
                cands = _near_miss_candidates(entry["find"], all_text)
                if cands:
                    entry["near_misses"] = cands

    return {"results": results, "total": sum(r["occurrences"] for r in results)}


def _replace_scanned(svc, pid: str, work: list[dict], slides, elements, dry_run: bool) -> dict:
    """Element-scoped replace and dry runs: the matches are found here, not by replaceAllText.

    Each text container (a shape, a table cell) is held as characters plus
    the style of each; pairs apply in order, matches from the last to the
    first so earlier indexes stay valid, and the batch replays the same
    edits on the deck (indexes in UTF-16 units, as the API counts).
    """
    import re

    pres = svc.presentations().get(presentationId=pid).execute()
    slide_index = {s["objectId"]: i for i, s in enumerate(pres.get("slides", []), 1)}
    targets: list[tuple[str, dict, tuple | None, dict]] = []  # (slide id, element, cell, text)
    if elements:
        for oid in elements:
            el, slide = find_element(pres, oid)
            if el is None:
                raise ValueError(f"element not found: {oid!r}")
            conts = refill.containers(el)
            if not conts:
                raise ValueError(f"{oid!r} holds no text (image, line, chart or group)")
            targets += [(slide["objectId"], el, cell, text) for cell, text in conts]
    else:
        wanted = set(resolve_slide_ids(svc, pid, slides)) if slides else None
        for s in pres.get("slides", []):
            if wanted is not None and s["objectId"] not in wanted:
                continue
            for el in refill.walk(s.get("pageElements", [])):
                targets += [(s["objectId"], el, cell, text) for cell, text in refill.containers(el)]

    state = [refill.text_of(text) for _s, _el, _c, text in targets]
    results = [{"find": w["find"], "replace": w["replace"], "occurrences": 0, "where": []} for w in work]
    requests: list[dict] = []
    for k, (sid, el, cell, _text) in enumerate(targets):
        chars, styles = state[k]
        loc = {"cellLocation": {"rowIndex": cell[0], "columnIndex": cell[1]}} if cell else {}
        for w, res in zip(work, results):
            flags = 0 if w["match_case"] else re.IGNORECASE
            s = "".join(chars)
            spans = [(m.start(), m.end()) for m in re.finditer(re.escape(w["find"]), s, flags)]
            if not spans:
                continue
            a = spans[0][0]
            ctx = s[max(0, a - 30):spans[0][1] + 30].replace("\n", " ⏎ ").strip()
            spot = {"slide": slide_index.get(sid), "element": el["objectId"], "count": len(spans), "context": ctx}
            if cell:
                spot.update(row=cell[0], column=cell[1])
            res["where"].append(spot)
            res["occurrences"] += len(spans)
            for start, end in reversed(spans):
                u0 = refill.utf16_len("".join(chars[:start]))
                u1 = u0 + refill.utf16_len("".join(chars[start:end]))
                style = styles[start] if start < len(styles) else {}
                requests.append({"deleteText": {"objectId": el["objectId"], **loc,
                                                "textRange": {"type": "FIXED_RANGE", "startIndex": u0, "endIndex": u1}}})
                if w["replace"]:
                    requests.append({"insertText": {"objectId": el["objectId"], **loc, "text": w["replace"],
                                                    "insertionIndex": u0}})
                    st = refill.style_request(el["objectId"], style, loc, {
                        "type": "FIXED_RANGE", "startIndex": u0, "endIndex": u0 + refill.utf16_len(w["replace"])})
                    if st:
                        requests.append(st)
                chars[start:end] = list(w["replace"])
                styles[start:end] = [style] * len(w["replace"])

    if requests and not dry_run:
        svc.presentations().batchUpdate(presentationId=pid, body={"requests": requests}).execute()
    haystack = ["".join(c) for c, _st in (refill.text_of(t) for _s, _e, _c, t in targets)]
    for res in results:
        if res["occurrences"] == 0:
            res.pop("where")
            cands = _near_miss_candidates(res["find"], haystack)
            if cands:
                res["near_misses"] = cands
    out = {"results": results, "total": sum(r["occurrences"] for r in results)}
    if dry_run:
        out["dry_run"] = True
    return out


def _gather_deck_text(svc, pid: str, page_object_ids: list[str] | None) -> list[str]:
    """Flatten all text-run strings on the deck (or in a slide subset)."""
    pres = svc.presentations().get(presentationId=pid).execute()
    out: list[str] = []
    for slide in pres.get("slides", []):
        if page_object_ids and slide.get("objectId") not in page_object_ids:
            continue
        _walk_text(slide.get("pageElements", []), out)
    return out


def _walk_text(elements: list, sink: list[str]) -> None:
    for el in elements:
        for te in el.get("shape", {}).get("text", {}).get("textElements", []):
            run = te.get("textRun", {}).get("content", "")
            if run.strip():
                sink.append(run)
        children = el.get("elementGroup", {}).get("children", [])
        if children:
            _walk_text(children, sink)


def _near_miss_candidates(needle: str, haystack: list[str], top: int = 3) -> list[str]:
    """Surface up to ``top`` deck strings that probably matched what the caller meant.

    Catches: HTML entity escaping (``&amp;`` vs ``&``), smart vs straight
    quotes, case-only differences, and small typos. Cheap O(N) scan — fine for
    decks up to a few hundred text runs.
    """
    import html
    from difflib import SequenceMatcher

    norm_needle = _normalize(needle)
    needle_decoded = html.unescape(needle)

    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for chunk in haystack:
        for s in (chunk, chunk.strip(), *chunk.split("\n")):
            s = s.strip()
            if not s or s in seen:
                continue
            seen.add(s)
            if _normalize(s) == norm_needle:
                scored.append((1.0, s))
                continue
            if needle_decoded != needle and needle_decoded in s:
                scored.append((0.95, s))
                continue
            ratio = SequenceMatcher(None, needle.lower(), s.lower()).ratio()
            if ratio >= 0.85 and len(s) <= len(needle) * 2:
                scored.append((ratio, s))
    scored.sort(key=lambda t: -t[0])
    return [s for _, s in scored[:top]]


def _normalize(s: str) -> str:
    """Normalize for near-miss matching: html-decode, fold quotes, lowercase, trim."""
    import html

    s = html.unescape(s)
    s = (
        s.replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"')
         .replace("–", "-").replace("—", "-")
    )
    return s.casefold().strip()
