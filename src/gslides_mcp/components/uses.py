"""When to use each built-in component — the ``use`` field of the catalogue.

One sentence per component: the situations it fits, then the close
alternatives and what tips the choice. A component can serve several
intents; the text names them rather than filing the component under one.
Written for the model reading ``list_components``.
"""

USES: dict[str, str] = {
    # --- chiffres ---------------------------------------------------------------------
    "kpi": "Un indicateur avec sa variation (sessions +8 %) dans un bilan ou un reporting ; plusieurs côte à côte → kpi_grid ; sans variation et plus spectaculaire → bigstat ou stats ; version encadrée avec picto et point de série → kpi_cards.",
    "kpi_grid": "Rangée(s) de 2 à 6 indicateurs avec deltas (audience actuelle, résultats de campagne) ; pour des chiffres de fierté sans variation → stats ; pour des cartes bordées avec picto → kpi_cards.",
    "kpi_cards": "Comparer des sources ou canaux chiffrés (ChatGPT / Perplexity / Copilot, Google / Meta) avec valeur et variation dans des cartes bordées, un point de couleur par carte ; sans carte ni picto → kpi_grid.",
    "bigstat": "Un seul chiffre choc qui porte la slide (+42 % de trafic, 1 site sur 3) avec libellé et précision ; plusieurs chiffres → stats ; avec une variation signée → kpi.",
    "stats": "Rangée de 3 à 5 chiffres de fierté ou de contexte (25 ans, 4 M€, 50 clients) sur une slide « qui sommes-nous » ou un chapeau de résultats ; avec deltas → kpi_grid ; un seul → bigstat ; avant → après → stat_pair.",
    "stat_pair": "Montrer un avant → après chiffré (pages indexées 16 913 → 15 588, erreurs 404 divisées par six) ; pour une comparaison de listes ou de structures → before_after ; pour des variations en % → kpi.",
    "big_numbers": "Deux à quatre principes ou règles numérotés « 1 2 3 » avec titre surligné et paragraphe (nos convictions, trois règles d'arborescence) ; pour des étapes ordonnées avec picto et sous-texte → numbered_list ; pour des phases de mission → phase_cards.",

    # --- cartes ---------------------------------------------------------------------
    "card": "Un bloc autonome : constat, chiffre, valeur, offre, pilier ; variantes light/dark/mint/acid/outline/plain, picto en tête, gros chiffre ou numéro ; plusieurs cartes de même hauteur → card_grid ; pour un message d'alerte ou d'info → callout.",
    "card_grid": "Les « trois piliers », les constats côté à côté, les valeurs d'entreprise, les offres : 2 à 4 cartes (picto, libellé, titre, corps) aux hauteurs égalisées, chaque carte avec son variant ; pour idée reçue vs réponse → compare_cards ; pour des phases de mission → phase_cards.",
    "callout": "Mettre en avant une phrase : à retenir (info), idée, point de vigilance (warn), risque (alert), conclusion sur fond sombre (dark) ; pour un verbatim client ou une citation → quote ; pour un simple tag → badge.",
    "badge": "Un petit tag en capitales posé près d'un titre ou dans un tableau (priorité haute, quick win, en cours) ; plus grand et arrondi → pill ; une chip numérotée de sommaire → agenda.",
    "pill": "Capsule pleine ou en contour pour nommer un levier, un canal, un outil, un statut (Google Ads, SEO local) ; en rangée via draw ou une recette ; plus petit et carré → badge.",
    "quote": "Verbatim client, citation d'expert, phrase de positionnement avec auteur et rôle ; pour une conclusion ou un message clé sans auteur → callout ; pour une grande phrase manifeste → un texte seul via draw.",
    "phase_cards": "La slide méthodologie : 2 à 4 temps d'une mission (cadrage, conception, développement) avec numéro accent, texte, picto + note et livrables ; pour une frise datée → timeline ; pour des blocs enchaînés par des flèches → process ; pour des étapes en liste → numbered_list.",
    "compare_cards": "Idée reçue vs réponse, mythe vs réalité, avant vs recommandé, en 2 ou 3 cartes ✗ / ✓ / neutres ; pour deux listes en vis-à-vis (URLs actuelles vs cibles) → before_after ; pour des cartes sans jugement → card_grid.",
    "before_after": "Deux listes en vis-à-vis avec verdict ✗ / ✓ et flèche : structure d'URL actuelle vs cible, pratiques à abandonner vs à adopter, existant vs recommandé ; pour deux chiffres → stat_pair ; pour 3 cartes argumentées → compare_cards.",
    "logo_grid": "Les outils ou partenaires d'un dispositif (Figma, Jira, Slack…) avec logo, nom, titre surligné « pour quoi faire » et texte ; pour des logos seuls sans texte → logo_wall ; pour des colonnes picto + titre + liste sans logo de marque → card_grid en variant plain.",
    "logo_wall": "Mur de références clients ou de partenaires, logos seuls en grille (sur fond sombre avec dark=True) ; pour expliquer chaque outil → logo_grid.",

    # --- texte ---------------------------------------------------------------------
    "agenda": "La slide sommaire : sections numérotées avec chip acide (dark=True sur le layout sombre) ; pour des étapes avec picto et sous-texte → numbered_list ; pour une liste simple → chevrons.",
    "numbered_list": "Leviers, priorités, sources, piliers en liste verticale numérotée avec titre + sous-texte (disque picto « #1 » ou chip carrée), cartes et connecteur optionnels ; pour de courtes étapes markdown sans titre → steps ; pour des phases de mission détaillées → phase_cards ; pour 3 principes en colonnes → big_numbers.",
    "steps": "Une courte suite d'étapes ou d'actions en markdown (audit, plan, netlinking) avec pastilles numérotées ; avec titre, sous-texte et picto → numbered_list ; en blocs fléchés horizontaux → process.",
    "checklist": "Ce qui est fait / à faire, livrables cochés, pré-requis, périmètre couvert ou non ; pour une liste sans notion d'état → chevrons ou arrows ; pour des critères comparés entre solutions → table.",
    "chevrons": "Liste à puces charte (›) pour 3 à 6 points courts : constats, objectifs, bénéfices ; pour des enchaînements ou conséquences → arrows ; pour cocher → checklist.",
    "arrows": "Liste → pour des enchaînements, conséquences, recommandations (« → sécuriser », « → prioriser ») ; pour des points simples → chevrons ; pour un flux réel entre étapes → process ou flowchart.",
    "palette": "Slides identité et accessibilité : nuancier de la charte, contrastes RGAA avec ratio (« Aa » fond/texte) ; pour un tableau de critères → table.",

    # --- données ---------------------------------------------------------------------
    "table": "Budget, planning, SLA, comparatif de solutions, KPI par canal : tout tableau charté avec en-tête, première colonne en gras, ligne de total ; pour colorer les cellules par intensité → heatmap ; pour des ✓ / ✗ → checklist ou compare_cards.",
    "heatmap": "Matrice chiffrée à lire par intensité (positions par requête et par mois, scores par critère et par concurrent, 60 points de contrôle) ; sans échelle de couleur → table.",
    "serp": "Illustrer une page de résultats Google : résultat actuel vs résultat cible, rich snippet avec étoiles, title/description recommandés ; pour une capture réelle dans un navigateur → browser.",

    # --- graphiques ---------------------------------------------------------------------
    "chart_bars": "Comparer des catégories (trafic par canal, pages par erreur, requêtes par volume) en barres verticales ou horizontales ; en vertical, `y_axis` grille l'axe et `dividers` marque un changement de période (avant / après) ; plusieurs séries empilées → chart_stacked ; barres + courbe sur second axe → chart_combo ; part d'un tout → donut ou pie ; parts atteintes vs restantes → compare_bars.",
    "chart_line": "Une évolution dans le temps sur plusieurs séries (clics 2025 vs 2026, sessions mensuelles, courbe de positions) ; pour des catégories sans temporalité → chart_bars ; une courbe posée sur des barres d'une autre grandeur (nombre de dons sur collecte) → chart_combo.",
    "chart_combo": "Deux grandeurs par période sur un seul graphique : un montant en barres (collecte annuelle, chiffre d'affaires) et un compte ou un taux en courbe sur l'axe droit (nombre de dons, taux de conversion), valeurs affichées sur chaque barre et chaque point ; une seule grandeur → chart_bars ou chart_line ; plusieurs séries de même nature → chart_stacked ou chart_line.",
    "chart_stacked": "Répartition par série au sein de chaque catégorie (collecte par canal et par année, citations par IA et par marque, budget par levier et par trimestre) ; en vertical avec `y_axis` et `dividers` pour une série temporelle coupée en périodes (ISF | IFI) ; une seule série → chart_bars ; barres + courbe → chart_combo ; parts d'un seul total → donut.",
    "donut": "Répartition d'un total en parts (budget par levier, trafic par source) avec légende et texte central ; disque plein → pie ; une seule part à suivre → gauge.",
    "pie": "Répartition d'un total en disque plein pour 2 à 5 parts ; avec texte central ou plus sobre → donut ; plusieurs indicateurs en anneaux → target.",
    "gauge": "Un score ou un taux sur une échelle (autorité de domaine 43/100, score Lighthouse, complétion) en demi-anneau ; plusieurs scores à comparer → target ou compare_bars ; un chiffre sans échelle → bigstat.",
    "target": "Plusieurs taux d'atteinte concentriques (tests lancés / gagnants / industrialisés, objectifs par pilier) ; un seul taux → gauge ; en barres → compare_bars.",
    "funnel": "Parcours de conversion avec volumes et taux de passage (visites → leads → clients, impressions → clics → RDV) ; sans volumes, juste des niveaux → stack ; en barres simples → chart_bars.",
    "compare_bars": "Part atteinte vs angle mort sur pistes grises (couverture de requêtes, complétion par chantier) ; avec valeurs absolues comparées → chart_bars ; en anneaux → target.",
    "bubbles": "Positionnement de concurrents ou de sujets sur deux axes avec une taille (volume × difficulté × trafic) ; pour prioriser des actions en impact/effort → effort_matrix.",
    "effort_matrix": "Prioriser des recommandations en impact / effort (quick wins, chantiers lourds) avec bulles numérotées ; pour des données mesurées sur deux axes → bubbles.",

    # --- schémas ---------------------------------------------------------------------
    "timeline": "Planning ou calendrier daté (T1 audit, T2 contenus, T3 netlinking), jalons d'un projet ; pour détailler chaque temps avec livrables → phase_cards ; pour un tableau de dates → table.",
    "process": "Chaîne linéaire de 3 à 5 blocs enchaînés par des flèches (brief → production → validation) ; avec branches, retours ou plusieurs lignes → flowchart ; avec livrables détaillés → phase_cards.",
    "flowchart": "Schéma de flux non linéaire : pipeline de contenu, boucle d'itération, dispositif avec branches, nœud mis en avant ; strictement linéaire → process ; hiérarchique → tree ; central + satellites → hub_spoke.",
    "hub_spoke": "Un élément central et ses satellites (site de marque et ses canaux, écosystème d'un outil, sources d'un LLM) ; hiérarchie parent → enfants → tree ; flux orienté → flowchart.",
    "tree": "Arborescence de site, organigramme, plan de rubriques à deux niveaux avec sous-rubriques listées ; pour des flux entre nœuds → flowchart ; pour un centre et ses satellites → hub_spoke.",
    "stack": "Pyramide ou pile de niveaux (pyramide SEO, socle → contenus → notoriété, priorités par couche) ; avec volumes et taux → funnel.",

    # --- personnes ---------------------------------------------------------------------
    "person_card": "Une personne : intervenant clé, CV synthétique, contact (photo carrée ou initiales, fonction, bio, contact) ; toute l'équipe → team_grid.",
    "team_grid": "La slide équipe dédiée : 2 à 6 fiches photo + nom + fonction + rôle sur le projet, hauteurs égalisées ; une seule personne → person_card.",

    # --- mockups ---------------------------------------------------------------------
    "browser": "Montrer une capture de site ou de dashboard dans un cadre navigateur plat avec URL (dashboards GA4, maquettes desktop, pages concurrentes) ; ambiance matériel → laptop ; mobile → phone ; résultat Google reconstitué → serp.",
    "laptop": "Mettre en scène une capture desktop dans un laptop (références, maquettes, avant/après de site) ; plus neutre et avec URL → browser ; capture mobile → phone.",
    "phone": "Mettre en scène une capture mobile (maquette responsive, appli, parcours mobile) ; capture desktop → laptop ou browser.",
}
