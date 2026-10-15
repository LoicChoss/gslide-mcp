"""Rebuild the component catalogue deck with the repo's code (not the installed bundle).

One slide per component (``cat_<name>``) and per variant (``cat_<name>__<k>``),
alphabetical: a header (name in bold, then the description or « variante k :
title — when ») and the component under it. Existing slides are wiped and
redrawn in place (their ids stay), missing ones are created at their sorted
index; slides of components that no longer exist are listed, not deleted.

Usage (from the repo root, with ``.env.local``)::

    .venv/Scripts/python.exe scripts/rebuild_catalogue.py [--deck ID] [--dry-run]
        [--thumbs DIR] [name …]

``--thumbs DIR`` saves a thumbnail of every rebuilt slide to DIR for review.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DECK = "1cPrerkVnlbxs5QtKjlILoBDO-MczFd-WViffUEUfi1E"
LAYOUT = "p12"
KEEP = {"cat_zz_pixel_icons"}  # hand-made slides the rebuild leaves alone
NARROW = {"card", "callout", "content_card", "donut", "gauge", "person_card", "quote", "serp"}  # shown at card width
X, Y, W, W_NARROW = 30.0, 60.0, 660.0, 420.0
HEADER_TOP, NAME_SIZE, DESC_SIZE = 12.0, 14, 11
INK, MUTED = {"red": 0.0, "green": 0.1686, "blue": 0.2353}, {"red": 0.4196, "green": 0.4392, "blue": 0.4588}
EMU = 12700


def _env() -> None:
    env = ROOT / ".env.local"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _expected() -> list[tuple[str, str, dict, str]]:
    """(slide id, component, props, header description) in deck order."""
    from gslides_mcp import components

    out = []
    for entry in components.catalogue():
        if entry["source"] != "builtin":
            continue
        name = entry["name"]
        out.append((f"cat_{name}", name, entry["example"]["props"], entry["description"]))
        for k, v in enumerate(entry.get("variants") or [], 1):
            when = f" — {v['when']}" if v.get("when") else ""
            out.append((f"cat_{name}__{k}", name, v["props"], f"variante {k} : {v['title']}{when}"))
    return sorted(out, key=lambda t: t[0])


def _header_requests(slide_id: str, name: str, desc: str) -> tuple[list[dict], float]:
    from gslides_mcp.components.builtin import _wrapped_lines

    text = f"{name}   {desc}"
    lines = _wrapped_lines(text, W, DESC_SIZE * 1.05)
    h = max(30.0, lines * DESC_SIZE * 1.35 + 8)
    oid = f"{slide_id[:40]}_hdr"
    reqs = [
        {"createShape": {"objectId": oid, "shapeType": "TEXT_BOX", "elementProperties": {
            "pageObjectId": slide_id,
            "size": {"width": {"magnitude": W * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": X * EMU, "translateY": HEADER_TOP * EMU, "unit": "EMU"}}}},
        {"insertText": {"objectId": oid, "text": text, "insertionIndex": 0}},
        {"updateTextStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "fields": "fontFamily,fontSize,foregroundColor,bold",
                             "style": {"fontFamily": "Barlow", "fontSize": {"magnitude": DESC_SIZE, "unit": "PT"}, "bold": False,
                                       "foregroundColor": {"opaqueColor": {"rgbColor": MUTED}}}}},
        {"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": len(name)},
                             "fields": "fontSize,foregroundColor,bold",
                             "style": {"fontSize": {"magnitude": NAME_SIZE, "unit": "PT"}, "bold": True,
                                       "foregroundColor": {"opaqueColor": {"rgbColor": INK}}}}},
    ]
    return reqs, (Y if lines <= 2 else HEADER_TOP + h + 8)


def _retry(call, what: str):
    for attempt in range(6):
        try:
            return call()
        except Exception as e:  # noqa: BLE001 — quota errors come as HttpError 429
            if "429" not in str(e) and "RATE_LIMIT" not in str(e) and "Quota" not in str(e):
                raise
            wait = 15 * (attempt + 1)
            print(f"   quota on {what}, waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"quota: gave up on {what}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="components to rebuild (default: all)")
    ap.add_argument("--deck", default=DECK)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--thumbs", help="directory for a thumbnail per rebuilt slide")
    args = ap.parse_args()
    _env()
    from gslides_mcp.auth import slide_service
    from gslides_mcp.tools.components import insert_component

    svc = slide_service()
    pres = svc.presentations().get(presentationId=args.deck, fields="slides(objectId,pageElements(objectId))").execute()
    existing = {s["objectId"]: [el["objectId"] for el in s.get("pageElements", [])] for s in pres["slides"]}
    order = [s["objectId"] for s in pres["slides"]]
    expected = _expected()
    wanted = {e[0] for e in expected}
    stale = [sid for sid in order if sid.startswith("cat_") and sid not in wanted and sid not in KEEP]
    todo = [e for e in expected if not args.names or e[1] in args.names]
    print(f"{len(expected)} catalogue slides, {len(todo)} to rebuild, {sum(1 for e in todo if e[0] not in existing)} to create")
    if stale:
        print("stale slides (not deleted):", ", ".join(stale))
    if args.dry_run:
        return
    thumbs = Path(args.thumbs) if args.thumbs else None
    if thumbs:
        thumbs.mkdir(parents=True, exist_ok=True)
    report = []
    for sid, name, props, desc in todo:
        reqs: list[dict] = []
        if sid in existing:
            reqs += [{"deleteObject": {"objectId": oid}} for oid in existing[sid]]
        else:
            # sorted position among the slides already there
            index = sum(1 for o in order if o < sid)
            reqs.append({"createSlide": {"objectId": sid, "insertionIndex": index, "slideLayoutReference": {"layoutId": LAYOUT}}})
            order.append(sid)
            order.sort()
        hdr, y = _header_requests(sid, name, desc)
        reqs += hdr
        _retry(lambda: svc.presentations().batchUpdate(presentationId=args.deck, body={"requests": reqs}).execute(), sid)
        width = W_NARROW if name in NARROW else W
        out = _retry(lambda: insert_component(args.deck, sid, name, props, x_pt=X, y_pt=y, width_pt=width), f"{sid} component")
        bottom = y + float(out.get("height_pt") or 0)
        report.append((sid, round(bottom), out.get("warnings")))
        print(f"{sid:42} bottom {bottom:5.0f}{'  OVER THE SLIDE' if bottom > 395 else ''}"
              f"{'  warnings: ' + '; '.join(map(str, out['warnings'])) if out.get('warnings') else ''}")
        if thumbs:
            thumb = _retry(lambda: svc.presentations().pages().getThumbnail(
                presentationId=args.deck, pageObjectId=sid, thumbnailProperties_thumbnailSize="LARGE").execute(), f"{sid} thumbnail")
            urllib.request.urlretrieve(thumb["contentUrl"], thumbs / f"{sid}.png")
        time.sleep(1.0)
    over = [r for r in report if r[1] > 395]
    print(f"\ndone: {len(report)} slides; {len(over)} run past the 405 pt slide; "
          f"{sum(1 for r in report if r[2])} with warnings")


if __name__ == "__main__":
    main()
