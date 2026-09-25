"""Rework an existing deck on the charter: harvest its images into Drive, suggest components.

``harvest_deck_assets`` copies every image of a source deck (and a thumbnail of each
slide) into a Drive folder, so a rebuild on another presentation can reuse them by
URL or as ``drive:<id>`` assets long after the source's temporary content URLs
have expired. ``suggest_components`` reads one source slide and ranks the charter
components that would present the same content, with the reasons.
"""

from __future__ import annotations

import os
import re
import tempfile

from ..app import ADDITIVE, READ_ONLY, mcp
from ..auth import drive_service, slide_service
from ..util import parse_pres_id
from . import deck as deck_tools
from . import qa
from .images import _sniff

_FOLDER_MIME = "application/vnd.google-apps.folder"
_FOLDER_URL = re.compile(r"/folders/([A-Za-z0-9_-]+)")
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif"}


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:40] or fallback).strip("-")


def _drive_url(fid: str) -> str:
    return f"https://drive.google.com/uc?export=view&id={fid}"


def _target_folder(drv, folder: str | None, name: str) -> tuple[str, bool]:
    """(folder id, created): the given folder, or a folder called ``name`` inside the assets folder."""
    from .. import assets as store

    if folder:
        m = _FOLDER_URL.search(folder)
        return (m.group(1) if m else folder.strip()), False
    parent = store.folder_id()
    existing = store._list_folder(drv, parent)
    if name in existing:
        return existing[name], False
    fid = drv.files().create(body={"name": name, "mimeType": _FOLDER_MIME, "parents": [parent]},
                             fields="id", supportsAllDrives=True).execute()["id"]
    return fid, True


def _images_of(slide: dict) -> list[tuple[dict, dict]]:
    """(raw image element, on-canvas summary) for every image, groups included."""
    found: list[tuple[dict, dict]] = []

    def walk(elements, tx=0.0, ty=0.0, sx=1.0, sy=1.0, parent=None):
        for el in elements:
            summary, ntx, nty, nsx, nsy = deck_tools._summarize_element(el, tx, ty, sx, sy, parent)
            if "image" in el:
                found.append((el, summary))
            children = el.get("elementGroup", {}).get("children", [])
            if children:
                walk(children, ntx, nty, nsx, nsy, el["objectId"])

    walk(slide.get("pageElements", []))
    return found


@mcp.tool(annotations=ADDITIVE)
def harvest_deck_assets(
    presentation: str,
    slides: list[str] | None = None,
    folder: str | None = None,
    thumbnails: bool = True,
    min_pt: float = 20.0,
    folder_name: str | None = None,
) -> dict:
    """Copy a deck's images (and a thumbnail per slide) into a Drive folder, for a rebuild elsewhere.

    The first step of « remettre ce deck à la charte » : the source's image URLs
    expire after ~30 minutes, so its visuals are stored once, named by slide and
    position (``s03-2-logo-client.png``), shared read-only, and returned with a
    stable ``url`` (for ``insert_image`` / ``draw`` image ops) and an ``asset``
    ref (``drive:<id>``, accepted by every ``icon`` / ``image`` / ``logo`` /
    ``photo`` prop and by ``draw``). Thumbnails (``s03-slide.png``) keep the
    original look at hand while rebuilding. Re-running is idempotent: files
    already in the folder are reused, not re-uploaded.

    Args:
        slides: 1-based indexes or objectIds to harvest (default: all).
        folder: Drive folder id or URL to store into. Ask the user first: an
            existing folder of theirs (pass its id / URL), or let the tool
            create « <deck title> · sources » inside the assets folder (default,
            reused on the next run); ``folder_name`` renames that new folder.
        folder_name: name of the folder to create when ``folder`` is not given.
        thumbnails: also store a LARGE thumbnail of each harvested slide.
        min_pt: images smaller than this on both sides (bullets, tiny icons) are
            skipped and listed under ``skipped``.

    Returns: ``{deck_title, folder_id, folder_url, folder_created, slides: [{index,
    slide_id, thumbnail: {name, file_id, url} | null, images: [{name, file_id,
    url, asset, element_id, x, y, w, h, alt}]}], image_count, skipped: [{slide,
    element_id, reason}]}``.

    Example: ``harvest_deck_assets(old_deck)["slides"][2]["images"][0]["asset"]``
    """
    from .. import assets as store

    pid = parse_pres_id(presentation)
    svc = slide_service()
    drv = drive_service()
    pres = svc.presentations().get(presentationId=pid).execute()
    title = pres.get("title", "")
    wanted = None
    if slides:
        wanted = {deck_tools._resolve_slide(pres, s)["objectId"] for s in slides}
    folder_id, created = _target_folder(drv, folder, folder_name or f"{title or 'deck'} · sources")
    existing = store._list_folder(drv, folder_id)

    def put(path: str, name: str) -> str:
        if name in existing:
            return existing[name]
        fid = store._upload(drv, folder_id, path, name)
        existing[name] = fid
        return fid

    out_slides: list[dict] = []
    skipped: list[dict] = []
    count = 0
    for idx, sl in enumerate(pres.get("slides", []), 1):
        sid = sl["objectId"]
        if wanted is not None and sid not in wanted:
            continue
        row: dict = {"index": idx, "slide_id": sid, "thumbnail": None, "images": []}
        for k, (el, summary) in enumerate(_images_of(sl), 1):
            url = el.get("image", {}).get("contentUrl")
            if not url:
                skipped.append({"slide": idx, "element_id": el["objectId"], "reason": "no content url"})
                continue
            if summary["w"] < min_pt and summary["h"] < min_pt:
                skipped.append({"slide": idx, "element_id": el["objectId"], "reason": f"smaller than {min_pt} pt"})
                continue
            fd, tmp = tempfile.mkstemp(prefix="gslides_harvest_", suffix=".bin")
            os.close(fd)
            try:
                qa._download_to(url, tmp)
                try:
                    mime = _sniff(tmp)
                except ValueError as exc:
                    skipped.append({"slide": idx, "element_id": el["objectId"], "reason": str(exc)})
                    continue
                name = f"s{idx:02d}-{k}-{_slug(summary.get('alt_title', ''), el['objectId'])}.{_EXT[mime]}"
                fid = put(tmp, name)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            count += 1
            row["images"].append({"name": name, "file_id": fid, "url": _drive_url(fid), "asset": f"drive:{fid}",
                                  "element_id": el["objectId"], "x": summary["x"], "y": summary["y"], "w": summary["w"], "h": summary["h"],
                                  "alt": summary.get("alt_title", "")})
        if thumbnails:
            name = f"s{idx:02d}-slide.png"
            if name in existing:
                fid = existing[name]
            else:
                png = qa._fetch_thumbnail_png(svc, pid, sid, "LARGE")
                try:
                    fid = put(png, name)
                finally:
                    try:
                        os.unlink(png)
                    except OSError:
                        pass
            row["thumbnail"] = {"name": name, "file_id": fid, "url": _drive_url(fid)}
        out_slides.append(row)
    return {"deck_title": title, "folder_id": folder_id, "folder_url": f"https://drive.google.com/drive/folders/{folder_id}",
            "folder_created": created, "slides": out_slides, "image_count": count, "skipped": skipped}


# --- component suggestions --------------------------------------------------------------

_NUM = re.compile(r"(?<![\w,.])[+-]?\d[\d   ]*(?:[.,]\d+)?\s*(?:%|€|k€|M€|K|M|pts?)?(?![\w])")
_STRONG_NUM = re.compile(r"[+-]?\d[\d   ]*(?:[.,]\d+)?\s*(?:%|€|k€|M€|k|M)|\d{1,3}(?:[   ]\d{3})+|\d{4,}")  # figures: unit, thousands or 4+ digits
_ARROW_SHAPES = {"RIGHT_ARROW", "LEFT_RIGHT_ARROW", "CHEVRON", "HOME_PLATE", "NOTCHED_RIGHT_ARROW", "STRIPED_RIGHT_ARROW", "BENT_ARROW", "UP_ARROW", "DOWN_ARROW"}

# (regex on the slide's text, components in order, reason)
_KEYWORDS: list[tuple[str, list[str], str]] = [
    (r"\bavant\b.*\bapr[eè]s\b|\bbefore\b.*\bafter\b", ["before_after", "stat_pair"], "le texte oppose un avant et un après"),
    (r"\bsommaire\b|\bagenda\b|ordre du jour|\bplan de (la )?pr[ée]sentation\b", ["agenda", "numbered_list"], "sommaire ou ordre du jour"),
    (r"\b[àa] retenir\b|\bconclusion|\bsynth[èe]se\b|\brecommandation|\bkey takeaways?\b|\benseignements?\b", ["takeaways", "attention_points", "next_steps"], "messages à retenir ou recommandations"),
    (r"prochaines? [ée]tapes?|\bnext steps?\b|\bsuite du projet\b|\bplan d'action", ["next_steps", "numbered_list", "session_plan"], "prochaines étapes"),
    (r"\bplanning\b|\bcalendrier\b|\bretroplanning\b|\btimeline\b|\broadmap\b|\bphases?\b|\bjalons?\b", ["timeline", "timeline_arrow", "phase_cards", "session_plan"], "planning, phases ou jalons"),
    (r"\b[ée]tapes?\b|\bprocess(us)?\b|\bm[ée]thod(e|ologie)\b|\bd[ée]marche\b|\bparcours\b", ["process", "steps", "numbered_list", "chevrons", "flowchart"], "démarche en étapes"),
    (r"\b[ée]quipe\b|\bteam\b|qui sommes[- ]nous|\binterlocuteurs?\b", ["team_grid", "person_card"], "présentation d'équipe"),
    (r"\bobjectifs?\b|\bdispositif\b|\bleviers?\b|\bbudget\b|\bplan m[ée]dia\b", ["media_plan", "table", "kpi_grid"], "objectifs, budget ou dispositif média"),
    (r"\br[ée]sultats?\b|\bbilan\b|\bperformances?\b|\bcampagne\b|\bkpi", ["kpi_grid", "chart_bars", "chart_combo", "table", "source_note"], "résultats chiffrés d'une campagne"),
    (r"\bcitation\b|\bt[ée]moignage\b|\bverbatim\b|«", ["quote"], "citation ou verbatim"),
    (r"\batelier\b|\bworkshop\b|\bvotes?\b|\bpriorisation\b|\bid[ée]es?\b|\bbrainstorm", ["ranked_bars", "chip_cloud", "quadrant_matrix", "board_columns", "score_matrix"], "restitution d'atelier"),
    (r"\bid[ée]e re[çc]ue\b|\bmythe\b|\bvrai ou faux\b|\bdo\b.*\bdon'?t\b", ["compare_cards", "do_dont"], "idées reçues ou bonnes / mauvaises pratiques"),
    (r"\bmaquette|\bwireframe|\bsite\b|\bpage d'accueil|\b[ée]cran|\bapp(li)?\b|\bmobile\b", ["browser", "laptop", "phone", "gallery"], "capture d'écran ou maquette"),
    (r"\bpiliers?\b|\bvaleurs?\b|\bconvictions?\b|\bprincipes?\b|\bexpertises?\b|\boffres?\b", ["card_grid", "big_numbers", "content_cards"], "piliers, valeurs ou offres en cartes"),
    (r"\bentonnoir\b|\bfunnel\b|\bconversion\b|\btunnel\b", ["funnel", "stat_box"], "entonnoir de conversion"),
    (r"\bclients?\b|\br[ée]f[ée]rences?\b|\bpartenaires?\b|\bils nous font confiance", ["logo_wall", "logo_grid", "client_ticker"], "références clients ou partenaires"),
    (r"\br[ée]partition\b|\bpart de\b|\bmix\b", ["donut", "donut_row", "chart_stacked"], "répartition en parts"),
    (r"\b[ée]volution\b|\btendance\b|\bmois par mois\b|\bjour par jour\b", ["chart_line", "chart_combo", "chart_bars"], "évolution dans le temps"),
]


def _bullets_of(el: dict) -> tuple[int, int]:
    """(paragraph count, bulleted paragraph count) of a shape."""
    paras = bullets = 0
    for te in el.get("shape", {}).get("text", {}).get("textElements", []):
        pm = te.get("paragraphMarker")
        if pm is not None:
            paras += 1
            if "bullet" in pm:
                bullets += 1
    return paras, bullets


def _bbox(items: list[dict]) -> dict:
    x0 = min(e["x"] for e in items)
    y0 = min(e["y"] for e in items)
    x1 = max(e["x"] + e["w"] for e in items)
    y1 = max(e["y"] + e["h"] for e in items)
    return {"x": round(x0, 1), "y": round(y0, 1), "w": round(x1 - x0, 1), "h": round(y1 - y0, 1)}


def _table_hint(raw: dict, text: str) -> tuple[list[str], str]:
    r = len(raw["table"].get("tableRows", []))
    c = raw["table"].get("columns", 0)
    cells = [cell for row in deck_tools._table_cells(raw["table"]) for cell in row]
    numeric = sum(1 for cell in cells if _NUM.fullmatch(cell.strip() or "x"))
    why = f"tableau de {r} lignes × {c} colonnes"
    low = " ".join(cells).lower() + " " + text
    if re.search(r"\bcpa\b|\bcpl\b|\broas\b|\bcpc\b", low):
        return ["table"], why + " avec une métrique à juger : variante pilules par seuil (`pill_cols`)"
    if re.search(r"vs\s*n-1|n-1|variation|[ée]volution|[+-]\d+[,.]?\d*\s*%", low):
        return ["table"], why + " avec des variations : variante « vs N-1 » (`delta_cols`)"
    if c >= 5 and r >= 4 and numeric >= (r - 1) * (c - 1) * 0.6:
        return ["heatmap", "table"], why + ", presque que des chiffres : lecture par intensité, sinon table"
    if re.search(r"google|meta|facebook|instagram|bing|linkedin|tiktok|pinterest|youtube|search|display|social", low):
        return ["table"], why + " avec une ligne par canal : variante pictos de canaux"
    return ["table"], why + " : variante simple (en-tête accent, total)"


def _text_block_candidates(e: dict, raw: dict, at_bottom: bool) -> tuple[list[str], str]:
    text = e["text"]
    words = len(text.split())
    paras, bullets = _bullets_of(raw)
    strong = len(_STRONG_NUM.findall(text))
    low = text.lower()
    if at_bottom and (low.startswith("source") or low.startswith("*") or re.search(r"\bsources?\s*:", low)):
        return ["source_note"], "note de source en bas de slide"
    if strong >= 3 and words <= 40:
        return ["kpi_grid", "stats", "big_numbers"], f"{strong} chiffres forts, peu de texte"
    if strong >= 1 and words <= 12:
        return ["bigstat", "kpi", "stat_box"], "un chiffre choc avec son libellé"
    if bullets >= 3 or paras >= 4:
        n = bullets or paras
        return ["chevrons", "takeaways", "numbered_list", "checklist"], f"{n} puces ou paragraphes : liste chartée (chevrons pour des points courts, takeaways pour titre + texte)"
    if low.startswith("«") or low.startswith('"') or re.search(r"\bt[ée]moignage\b|\bcitation\b", low):
        return ["quote"], "citation ou verbatim"
    if words > 90:
        return ["analysis_block", "content_card", "callout"], "paragraphe long : bloc d'analyse titré ou carte de contenu"
    if words <= 6:
        return ["eyebrow", "badge", "pill"], "libellé court : sur-titre ou tag"
    return ["callout", "card", "analysis_block"], "texte court : encadré ou carte"


def _blocks(slide: dict, page_w: float, page_h: float) -> tuple[dict, list[dict], list[dict]]:
    """Group the slide's elements into content blocks, each with ranked candidates."""
    els: list[dict] = []
    deck_tools._walk_elements(slide.get("pageElements", []), True, els)
    raw_by_id: dict[str, dict] = {}

    def index(elements):
        for el in elements:
            raw_by_id[el["objectId"]] = el
            index(el.get("elementGroup", {}).get("children", []))

    index(slide.get("pageElements", []))
    els = [e for e in els if e["type"] != "group"]
    texts = [e for e in els if e["type"] not in ("image", "table", "chart") and e.get("text")]
    title_el = None
    for e in texts:
        if raw_by_id[e["id"]].get("shape", {}).get("placeholder", {}).get("type") in ("TITLE", "CENTERED_TITLE"):
            title_el = e
            break
    if title_el is None and texts:
        top = [e for e in texts if e["y"] < page_h * 0.25 and len(e["text"].split()) <= 20]
        if top:
            title_el = max(top, key=lambda e: e["w"] * e["h"])
    title = title_el["text"] if title_el else ""
    body = [e for e in texts if e is not title_el]
    all_text = " ".join(e["text"] for e in texts).lower()
    blocks: list[dict] = []
    used: set[str] = set()

    def add(items: list[dict], names: list[str], why: str, kind: str) -> None:
        blocks.append({"kind": kind, "zone": _bbox(items), "elements": [e["id"] for e in items],
                       "content": " | ".join(e["text"] for e in items if e.get("text"))[:200], "candidates": [(n, why) for n in names]})
        used.update(e["id"] for e in items)

    for e in els:
        if e["type"] == "table":
            raw = raw_by_id[e["id"]]
            if len(raw["table"].get("tableRows", [])) <= 1 and raw["table"].get("columns", 1) <= 1:
                cells = deck_tools._table_cells(raw["table"])
                e["text"] = " ".join(c for row in cells for c in row)
                add([e], ["stat_box", "kpi", "card"], "tableau à une cellule : boîte chiffrée ou carte", "box")
                continue
            names, why = _table_hint(raw, all_text)
            add([e], names, why, "table")
        elif e["type"] == "chart":
            add([e], ["chart_bars", "chart_line", "chart_combo", "donut"], "graphique Sheets : composant charté, ou graphique Sheets natif relié (insert_sheets_chart)", "chart")
    images = [e for e in els if e["type"] == "image"]
    big = [e for e in images if e["w"] * e["h"] > 0.25 * page_w * page_h]
    small = [e for e in images if e["w"] < 90 and e["h"] < 90]
    if len(images) == 1 and big:
        why = "une grande image : capture à encadrer (browser / laptop / phone) ou à reposer telle quelle" if re.search(r"site|page|[ée]cran|maquette|app|mobile|web", all_text) else "une grande image à reposer, ou galerie"
        add(images, ["browser", "laptop", "phone", "gallery"], why, "image")
    elif len(small) >= 3 and len(small) >= len(images) - 1:
        add(images, ["logo_wall", "logo_grid", "client_ticker"], f"{len(images)} petites images : logos ou pictos", "logos")
    elif len(images) >= 2:
        add(images, ["gallery", "ad_scoreboard", "card_grid"], f"{len(images)} images : galerie, tableau par annonce (visuels de campagne) ou cartes avec picto", "images")
    elif images:
        add(images, ["gallery", "card"], "une image à reposer (insert_image avec l'asset moissonné) ou dans une carte", "image")
    # text rows: shapes side by side (same y within 12 pt)
    remaining = [e for e in body if e["id"] not in used]
    remaining.sort(key=lambda e: (round(e["y"] / 12), e["x"]))
    i = 0
    while i < len(remaining):
        e = remaining[i]
        stack = [o for o in remaining[i:] if abs(o["x"] - e["x"]) < 4 and abs(o["w"] - e["w"]) < 4 and len(o["text"].split()) <= 6]
        if len(stack) >= 3 and len(e["text"].split()) <= 6:
            add(stack, ["table", "checklist", "chip_cloud", "numbered_list"], f"{len(stack)} libellés courts empilés : tableau, liste cochée ou nuage de tags", "stack")
            remaining = [o for o in remaining if o["id"] not in used]
            continue
        row = [o for o in remaining[i:] if abs(o["y"] - e["y"]) < 12]
        if len(row) >= 3:
            strong = sum(len(_STRONG_NUM.findall(o["text"])) for o in row)
            if strong >= len(row):
                add(row, ["kpi_grid", "stats", "big_numbers"], f"{len(row)} chiffres côte à côte : rangée d'indicateurs", "columns")
            else:
                add(row, ["card_grid", "big_numbers", "phase_cards", "content_cards", "process"], f"{len(row)} blocs côte à côte : cartes de même hauteur", "columns")
            i += len(row)
            continue
        if len(row) == 2:
            names = ["before_after", "compare_cards", "stat_pair"] if re.search(r"avant|apr[eè]s|before|after|n-1", all_text) else ["compare_cards", "content_cards", "card_grid", "do_dont"]
            add(row, names, "deux blocs face à face", "pair")
            i += 2
            continue
        names, why = _text_block_candidates(e, raw_by_id[e["id"]], at_bottom=e["y"] + e["h"] > page_h * 0.85)
        add([e], names, why, "text")
        i += 1
    arrows = [e for e in els if e["type"] in _ARROW_SHAPES and e["id"] not in used]
    if len(arrows) >= 2:
        add(arrows, ["process", "chevrons", "timeline_arrow", "flowchart"], f"{len(arrows)} flèches : enchaînement d'étapes (à fusionner avec les blocs de texte voisins)", "arrows")
    signals = {"title": title, "elements": len(els), "texts": len(texts), "images": len(images), "tables": sum(1 for e in els if e["type"] == "table"),
               "charts": sum(1 for e in els if e["type"] == "chart"), "arrows": len(arrows), "words": len(all_text.split()),
               "unused_elements": [e["id"] for e in els if e["id"] not in used and e is not title_el and (e.get("text") or e["type"] in ("image", "table", "chart"))]}
    slide_level: list[tuple[str, str]] = []
    text = (title + " " + all_text).lower()
    for pattern, names, why in _KEYWORDS:
        if re.search(pattern, text):
            for n in names:
                if all(n != o[0] for o in slide_level):
                    slide_level.append((n, why))
    if not body and not images and not blocks:
        slide_level.insert(0, ("section_header", "titre seul : slide de chapitre"))
    return signals, blocks, slide_level


@mcp.tool(annotations=READ_ONLY)
def suggest_components(presentation: str, slide: str, top: int = 4) -> dict:
    """Read a source slide and propose, block by block, the charter components that would present it.

    A slide usually holds several things: a title (→ the target layout's TITLE
    placeholder), a table, a row of figures, a paragraph, a screenshot, a
    source note… Each becomes a ``block`` with its zone on the source slide,
    the element ids it came from, a content excerpt and ranked ``candidates``
    (component, why, the catalogue's ``use`` sentence, variant titles). The
    zones keep the source's proportions so the blocks can be laid out inside
    the target layout's ``content_area`` (see ``list_layouts``).
    ``slide_level`` lists whole-slide alternatives read from the wording
    (« avant / après » → before_after, « équipe » → team_grid, « objectifs »
    → media_plan…) that may replace several blocks at once. Heuristics: the
    signals are returned so a better reading can override them, and a block
    may well deserve a component that is not listed.

    Args:
        slide: 1-based index or objectId of the source slide.
        top: candidates kept per block.

    Returns: ``{slide_id, index, title, blocks: [{kind, zone: {x, y, w, h}, elements,
    content, candidates: [{component, why, use, variants}]}], slide_level: [{component,
    why, use}], signals}``.

    Example: ``suggest_components(old_deck, 7)["blocks"][0]["candidates"][0]["component"]``
    """
    from .. import components as registry

    pid = parse_pres_id(presentation)
    pres = slide_service().presentations().get(presentationId=pid).execute()
    sl = deck_tools._resolve_slide(pres, slide)
    index = next(i for i, s in enumerate(pres["slides"], 1) if s["objectId"] == sl["objectId"])
    size = pres.get("pageSize", {})
    page_w = size.get("width", {}).get("magnitude", 9144000) / 12700
    page_h = size.get("height", {}).get("magnitude", 5143500) / 12700
    signals, blocks, slide_level = _blocks(sl, page_w, page_h)
    cat = {e["name"]: e for e in registry.catalogue()}

    def describe(name: str, why: str, with_variants: bool = True) -> dict | None:
        e = cat.get(name)
        if e is None:
            return None
        out = {"component": name, "why": why, "use": e.get("use", "")}
        if with_variants:
            out["variants"] = [v["title"] for v in e.get("variants", [])]
        return out

    for b in blocks:
        b["candidates"] = [d for n, why in b["candidates"][:top] if (d := describe(n, why))]
    return {"slide_id": sl["objectId"], "index": index, "title": signals["title"][:120], "page": {"w": round(page_w, 1), "h": round(page_h, 1)},
            "blocks": blocks, "slide_level": [d for n, why in slide_level[:top] if (d := describe(n, why, False))], "signals": signals}
