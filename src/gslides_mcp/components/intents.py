"""Slide intentions: what a slide has to do, and the components that do it.

Claude kept reaching for the same few components: the catalogue came as one
huge alphabetical list, read once and skimmed. Two readers now start from the
intention instead of a familiar name: ``list_components()`` groups its index by
intention, so the whole catalogue is seen at once, and ``suggest_components
(description=…)`` matches a slide described in words against the same table.
``KEYWORDS`` (wording that points at one component, « avant / après » →
before_after) also serves the rework reading of a source slide.

A component sits under every intention it serves, best fits first. ``USUAL``
names the components Claude picks without being asked; a suggestion always
offers one that is not among them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    key: str
    label: str
    pattern: str                    # regex on the lower-cased description
    components: tuple[str, ...]     # best fits first


INTENTS: tuple[Intent, ...] = (
    Intent("chiffres", "Faire retenir des chiffres",
           r"\bchiffres?\b|\bkpis?\b|\bindicateurs?\b|\bm[ée]triques?\b|\bstatistiques?\b|\btaux\b|\bscores?\b"
           r"|\bpourcentages?\b|[\d,.]+\s?%",
           ("kpi_grid", "kpi", "stats", "bigstat", "kpi_cards", "stat_pair", "stat_box", "gauge", "target")),
    Intent("comparer", "Comparer des options, des acteurs, un avant et un après",
           r"\bcompar|\bvs\b|\bversus\b|\bface [àa]\b|\bavant\b.*\bapr[eè]s\b|\bmythes?\b|\bid[ée]es? re[çc]ues?\b"
           r"|\bdiff[ée]rences?\b|\bconcurren|\bbenchmark|\bplut[oô]t que\b|\bn-1\b|\bbonnes? pratiques?\b",
           ("compare_cards", "before_after", "kpi_cards", "mini_charts", "chart_grouped", "stat_pair", "do_dont",
            "diagram_compare", "compare_bars", "serp", "table")),
    Intent("repartition", "Montrer une répartition",
           r"\br[ée]partition|\bparts? de\b|\bmix\b|\bventil|\bpoids\b|\bpar (levier|canal|source|r[ée]gie|support)s?\b"
           r"|\bdistribution\b|\bsources? de trafic\b|\bcanaux\b",
           ("donut", "pie", "donut_row", "chart_stacked", "bar_list", "compare_bars")),
    Intent("evolution", "Montrer une évolution dans le temps",
           r"\b[ée]volution|\btendances?\b|\bmois par mois\b|\bmensuel|\bhebdo|\bdans le temps\b|\bcourbe"
           r"|\bprogression|\bcroissance|\bsaisonnalit|\bhistorique|\bjour par jour\b|\bsemaine par semaine\b",
           ("chart_line", "chart_combo", "chart_bars", "chart_grouped", "heatmap", "timeline_arrow")),
    Intent("classer", "Classer, prioriser",
           r"\bclass(e|er|ement)\b|\bprioris|\bpriorit[ée]s?\b|\btop \d+|\bpalmar[eè]s|\bmatrice\b|\bquick wins?\b"
           r"|\bmaturit[ée]\b|\bnotes? par\b",
           ("bar_list", "ranked_bars", "effort_matrix", "quadrant_matrix", "bubbles", "score_matrix", "heatmap",
            "numbered_list")),
    Intent("etapes", "Enchaîner des étapes, planifier",
           r"\b[ée]tapes?\b|\bprocess(us)?\b|\bm[ée]thod(e|ologie)\b|\bd[ée]marche\b|\bparcours\b|\bplanning\b"
           r"|\bcalendrier\b|\bretro-?planning\b|\btimeline\b|\broadmap\b|\bphases?\b|\bjalons?\b|\bd[ée]roul[ée]\b"
           r"|\bentonnoir\b|\bfunnel\b|\bcycle\b|\bboucle\b|\bpipeline\b|\bworkflow\b",
           ("process", "steps", "timeline", "phase_cards", "next_steps", "timeline_arrow", "flowchart", "cycle",
            "funnel", "session_plan", "arrows")),
    Intent("structure", "Montrer une structure, un écosystème",
           r"\barborescence|\bstructure\b|\bsilo\b|\bcocon\b|\b[ée]cosyst[eè]me|\bpyramide|\bniveaux\b"
           r"|\borganigramme|\bsatellites?\b|\bformule\b|\b[ée]quation\b|\barchitecture\b|\bmapping\b",
           ("tree", "hub_spoke", "stack", "cocon", "diagram_compare", "formula", "flowchart")),
    Intent("messages", "Poser des constats, des recommandations",
           r"\bconstats?\b|\benseignements?\b|\b[àa] retenir\b|\bsynth[eè]se\b|\bconclusion|\brecommandations?\b"
           r"|\brecos?\b|\banalyse\b|\bmessages?\b|\bpoints? (cl[ée]s?|de vigilance|d'attention)\b|\balertes?\b"
           r"|\bchecklist\b|\bpr[ée]-?requis\b|\blivrables?\b|\bcitation\b|\bverbatim|\bt[ée]moignage|\bpiliers?\b"
           r"|\bvaleurs\b|\bconvictions?\b|\bprincipes?\b|\bb[ée]n[ée]fices?\b|\benjeux?\b|\bobjectifs?\b",
           ("takeaways", "card_grid", "callout", "analysis_block", "card", "big_numbers", "attention_points",
            "checklist", "chevrons", "arrows", "numbered_list", "quote", "content_cards")),
    Intent("personnes", "Présenter des personnes, des références",
           r"\b[ée]quipe\b|\bteam\b|\binterlocuteurs?\b|\bintervenants?\b|\bexperts?\b|\bpersonas?\b"
           r"|\br[ée]f[ée]rences?\b|\bpartenaires?\b|\blogos?\b|\bqui sommes[- ]nous\b|\bconfiance\b",
           ("team_grid", "person_card", "persona_sheet", "persona_card", "logo_grid", "logo_wall", "client_ticker", "quote")),
    Intent("visuels", "Montrer un visuel, un écran, des annonces",
           r"\bcaptures?\b|\b[ée]crans?\b|\bscreenshots?\b|\bmaquettes?\b|\bwireframes?\b|\bmockups?\b|\bhome ?page\b"
           r"|\bpage d'accueil\b|\bmobile\b|\bannonces?\b|\bvisuels?\b|\bcr[ée]as?\b|\bserp\b|\bsnippet",
           ("browser", "laptop", "phone", "gallery", "ad_scoreboard", "serp", "placeholder")),
    Intent("donnees", "Détailler des données",
           r"\btableau\b|\bd[ée]taill|\bpar campagne\b|\bligne par ligne\b|\bbudget\b|\bplan m[ée]dia\b"
           r"|\bdispositif\b|\bheatmap\b",
           ("table", "heatmap", "score_matrix", "ad_scoreboard", "media_plan", "source_note")),
    Intent("atelier", "Restituer un atelier",
           r"\batelier\b|\bworkshop\b|\bbrainstorm|\bpost-?it\b|\bvotes?\b|\bs[ée]ance\b|\brestitution\b"
           r"|\birritants?\b",
           ("board_columns", "chip_cloud", "ranked_bars", "quadrant_matrix", "score_matrix", "session_plan")),
    Intent("habillage", "Habiller une slide : titres, sommaire, tags, boutons",
           r"\bsommaire\b|\bagenda\b|\bordre du jour\b|\bintercalaire\b|\bchapitre\b|\bsection\b|\bcta\b"
           r"|\bboutons?\b|\bhashtags?\b|\btags?\b|\bnuancier\b|\bpalette\b|\bcontrastes?\b|\baccessibilit[ée]\b",
           ("section_header", "agenda", "eyebrow", "hashtags", "badge", "pill", "button", "button_row",
            "content_card", "content_cards", "palette", "source_note")),
)

OTHER = "autres"  # index group of the recipes that declare no intention

USUAL = frozenset({"card", "card_grid", "kpi", "kpi_grid", "table", "callout", "chart_bars", "donut", "chevrons",
                   "numbered_list"})

# Wording that points at given components, whole slide. Read by suggest() and by the
# rework reading of a source slide (harvest.suggest_components): keep new entries at the end.
KEYWORDS: list[tuple[str, list[str], str]] = [
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
    (r"\bpersona", ["persona_sheet", "persona_card"], "fiche persona"),
    (r"\bcocon\b|\bsilo\b|\bpage cible\b", ["cocon", "tree"], "cocon sémantique ou silo"),
    (r"\bcycle\b|\bboucle\b", ["cycle", "process"], "cycle ou boucle d'étapes"),
    (r"\bchecklist\b|\bcheck-list\b|\bà v[ée]rifier\b", ["checklist"], "liste à cocher"),
    (r"\bunivers\b.*\bmots?[- ]cl[ée]s?\b|\bmapping\b", ["tree"], "univers de mots-clés"),
    (r"\bclients?\b|\br[ée]f[ée]rences?\b|\bpartenaires?\b|\bils nous font confiance", ["logo_wall", "logo_grid", "client_ticker"], "références clients ou partenaires"),
    (r"\br[ée]partition\b|\bpart de\b|\bmix\b", ["donut", "donut_row", "chart_stacked"], "répartition en parts"),
    (r"\b[ée]volution\b|\btendance\b|\bmois par mois\b|\bjour par jour\b", ["chart_line", "chart_combo", "chart_bars"], "évolution dans le temps"),
    (r"\bgoogle\b.*\b(bing|meta|chatgpt)\b|\bplusieurs acteurs\b|\bdeux acteurs\b|\bsur \d+ (kpis?|indicateurs)\b", ["mini_charts", "kpi_cards"], "plusieurs acteurs sur les mêmes indicateurs"),
    (r"\bun seul chiffre\b|\bchiffre choc\b|\bchiffre cl[ée]\b", ["bigstat"], "un chiffre qui porte la slide"),
    (r"\bscore\b|/100\b|\bsur 100\b|\btaux d'atteinte\b", ["gauge", "target"], "un score ou un taux sur une échelle"),
    (r"\bimpact\b.*\beffort\b|\beffort\b.*\bimpact\b|\bquick wins?\b", ["effort_matrix", "quadrant_matrix"], "prioriser en impact / effort"),
    (r"\bvigilance\b|\balertes?\b|\brisques?\b", ["attention_points", "callout"], "points de vigilance"),
    (r"\bannonces?\b|\bcr[ée]as?\b|\bpublicit[ée]s?\b", ["ad_scoreboard", "gallery"], "annonces ou créas"),
    (r"\bclassement\b|\btop \d+\b|\bpalmar[eè]s\b", ["ranked_bars", "bar_list"], "un classement"),
    (r"\bsatisfaction\b|\bmaturit[ée]\b|\bgrille d'[ée]valuation\b", ["score_matrix", "heatmap"], "des notes par critère"),
    (r"\bpositionnement\b|\bvolume\b.*\bdifficult[ée]\b", ["bubbles", "quadrant_matrix"], "positionnement sur deux axes"),
    (r"\bton de (la )?marque\b|\bvocabulaire\b|\b(on|off)-brand\b", ["do_dont"], "ton et vocabulaire"),
    (r"\bpr[ée]-?requis\b|\blivrables?\b|\bp[ée]rim[eè]tre\b", ["checklist"], "livrables, prérequis ou périmètre"),
    (r"\bformule\b|\b[ée]quation\b", ["formula"], "un raisonnement en équation"),
    (r"\bpyramide\b|\bsocle\b", ["stack"], "une pyramide de niveaux"),
    (r"\b[ée]cosyst[eè]me\b|\bsatellites?\b", ["hub_spoke"], "un élément central et ses satellites"),
    (r"\bm[ée]thodologie\b|\bmission\b", ["phase_cards"], "les temps d'une mission"),
]

_KEYS = {i.key for i in INTENTS}
_NUMBER = re.compile(r"\d[\d  .,]*")


def check(keys: list[str]) -> list[str]:
    """The intention keys a recipe declares, refused when one is unknown."""
    unknown = [k for k in keys if k not in _KEYS]
    if unknown:
        raise ValueError(f"unknown intention {unknown[0]!r}; intentions: {', '.join(i.key for i in INTENTS)}")
    return list(keys)


def of(name: str, declared: list[str] | None = None) -> list[str]:
    """Keys of the intentions a component serves: the table's, plus those a recipe declares."""
    return [i.key for i in INTENTS if name in i.components or i.key in (declared or ())]


def index(entries: list[dict]) -> list[dict]:
    """``[{key, label, components}]`` for catalogue entries (each with ``intents``); recipes without one go to ``autres``."""
    present = {e["name"] for e in entries}
    groups = []
    for i in INTENTS:
        names = [n for n in i.components if n in present]
        names += [e["name"] for e in entries if i.key in e.get("intents", ()) and e["name"] not in i.components]
        groups.append({"key": i.key, "label": i.label, "components": names})
    others = [e["name"] for e in entries if not e.get("intents")]
    if others:
        groups.append({"key": OTHER, "label": "Autres", "components": others})
    return groups


def suggest(description: str, catalogue: dict[str, dict], avoid: list[str] | None = None, top: int = 4) -> dict:
    """Intentions read in a slide description, with ranked candidates and one less obvious pick.

    An intention matches by its own words (score 2); only when none does, a
    component keyword (« persona » → persona_card) brings in that component's
    best home (score 1). Each keyword hit inside an intention adds 1 and ranks
    the component first, a keyword naming few components weighing more than a
    broad one. ``avoid`` (components already planned elsewhere) go to the end
    of every list.
    """
    text = description.lower()
    avoid = list(dict.fromkeys(avoid or []))
    hits: dict[str, str] = {}               # component -> why, first keyword that named it
    weight: dict[str, float] = {}
    rank: dict[str, tuple[int, int]] = {}    # (keyword index, place in its list) of the first hit
    for k, (pattern, names, why) in enumerate(KEYWORDS):
        if re.search(pattern, text):
            for place, n in enumerate(names):
                hits.setdefault(n, why)
                rank.setdefault(n, (k, place))
                weight[n] = weight.get(n, 0) + 1 / len(names)
    scores: dict[str, int] = {}
    whys: dict[str, str] = {}
    for i in INTENTS:
        m = re.search(i.pattern, text)
        if m:
            scores[i.key], whys[i.key] = 2, f"« {m.group(0).strip()} »"
    if "chiffres" not in scores and len(_NUMBER.findall(text)) >= 2:
        scores["chiffres"], whys["chiffres"] = 1, "plusieurs chiffres dans la description"
    pull = not scores
    for n, why in hits.items():
        homes = [i for i in INTENTS if n in i.components]
        if pull and homes and not any(i.key in scores for i in homes):
            home = min(homes, key=lambda i: i.components.index(n))
            scores[home.key], whys[home.key] = 0, why
        for i in homes:
            if i.key in scores:
                scores[i.key] += 1

    order = [i for i in INTENTS if i.key in scores]
    order.sort(key=lambda i: -scores[i.key])  # stable: the table's order on ties
    lists: dict[str, list[str]] = {}
    for i in order:
        boosted = sorted((n for n in hits if n in i.components), key=lambda n: (-weight[n], rank[n]))
        names = boosted + [n for n in i.components if n not in hits]
        names += [n for n, e in catalogue.items() if i.key in e.get("intents", ()) and n not in i.components]
        names = [n for n in names if n in catalogue]
        lists[i.key] = [n for n in names if n not in avoid] + [n for n in names if n in avoid]

    def candidate(n: str) -> dict:
        e = catalogue[n]
        out = {"component": n, "use": e.get("use", ""), "variants": [v["title"] for v in e.get("variants", [])]}
        if n in hits:
            out["why"] = hits[n]
        if n in avoid:
            out["avoid"] = True
        return out

    # the best intention first: its best candidate that is neither usual, planned, nor a first pick
    tops = {lst[0] for lst in lists.values() if lst}
    less = next(({"component": n, "intent": i.key, "why": f"moins attendu que {lists[i.key][0]} pour « {i.label} »",
                  "use": catalogue[n].get("use", "")}
                 for i in order for n in lists[i.key][1:]
                 if n not in USUAL and n not in avoid and n not in tops), None)

    out: dict = {
        "description": description,
        "intents": [{"intent": i.key, "label": i.label, "why": whys[i.key],
                     "candidates": [candidate(n) for n in lists[i.key][:top]]} for i in order],
        "less_obvious": less,
    }
    if avoid:
        out["avoided"] = avoid
    if not order:
        out["all_intents"] = [{"key": i.key, "label": i.label} for i in INTENTS]
        out["hint"] = "aucune intention reconnue : en choisir une dans all_intents, puis lire ses composants dans list_components()"
    return out
