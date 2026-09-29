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
    "checklist": "Ce qui est fait / à faire, livrables cochés, pré-requis, périmètre couvert ou non ; avec `groups`, une checklist de publication ou d'audit en sections numérotées sur deux colonnes ; pour une liste sans notion d'état → chevrons ou arrows ; pour des critères comparés entre solutions → table.",
    "chevrons": "Liste à puces charte (›) pour 3 à 6 points courts : constats, objectifs, bénéfices ; pour des enchaînements ou conséquences → arrows ; pour cocher → checklist.",
    "arrows": "Liste → pour des enchaînements, conséquences, recommandations (« → sécuriser », « → prioriser ») ; pour des points simples → chevrons ; pour un flux réel entre étapes → process ou flowchart.",
    "palette": "Slides identité et accessibilité : nuancier de la charte, contrastes RGAA avec ratio (« Aa » fond/texte) ; pour un tableau de critères → table.",

    # --- données ---------------------------------------------------------------------
    "table": "Budget, planning, SLA, comparatif de solutions, KPI par canal : tout tableau charté avec en-tête, première colonne en gras, ligne de total. Cinq réglages prêts dans `variants` (lire leur `when`) : simple, pictos de canaux, colonnes vs N-1, pilules par seuil, une colonne par élément avec vignette en tête : `image_row`, emplacements d'image remplaçables ; l'exemple principal montre pastilles + sous-lignes + pilules. Pour colorer les cellules par intensité → heatmap ; pour des ✓ / ✗ → checklist ou compare_cards.",
    "heatmap": "Matrice chiffrée à lire par intensité (positions par requête et par mois, scores par critère et par concurrent, 60 points de contrôle) ; sans échelle de couleur → table.",
    "serp": "Illustrer une page de résultats Google : résultat actuel vs résultat cible, rich snippet avec étoiles, title/description recommandés ; pour une capture réelle dans un navigateur → browser.",

    # --- graphiques ---------------------------------------------------------------------
    "chart_bars": "Comparer des catégories (trafic par canal, pages par erreur, requêtes par volume) en barres verticales ou horizontales ; en vertical, `y_axis` grille l'axe et `dividers` marque un changement de période (avant / après) ; plusieurs séries empilées → chart_stacked ; barres + courbe sur second axe → chart_combo ; part d'un tout → donut ou pie ; parts atteintes vs restantes → compare_bars.",
    "chart_line": "Une évolution dans le temps sur plusieurs séries (clics 2025 vs 2026, sessions mensuelles, courbe de positions) ; pour des catégories sans temporalité → chart_bars ; une courbe posée sur des barres d'une autre grandeur (nombre de dons sur collecte) → chart_combo.",
    "chart_combo": "Deux grandeurs par période sur un seul graphique : un montant en barres (collecte annuelle, chiffre d'affaires) et un compte ou un taux en courbe sur l'axe droit (nombre de dons, taux de conversion), valeurs affichées sur chaque barre et chaque point ; une seule grandeur → chart_bars ou chart_line ; plusieurs séries de même nature → chart_stacked ou chart_line.",
    "chart_stacked": "Répartition par série au sein de chaque catégorie (collecte par canal et par année, citations par IA et par marque, budget par levier et par trimestre) ; en vertical avec `y_axis` et `dividers` pour une série temporelle coupée en périodes (ISF | IFI) ; une seule série → chart_bars ; barres + courbe → chart_combo ; parts d'un seul total → donut.",
    "chart_grouped": "Comparer N et N-1 (ou plusieurs séries) catégorie par catégorie en barres côte à côte : collecte par régie foncé / clair avec `category_colors`, impressions et dépenses par famille de campagne ; séries empilées → chart_stacked ; une seule série → chart_bars ; un indicateur par mini-graphique → mini_charts.",
    "mini_charts": "Comparer deux ou trois acteurs (Google vs Bing) sur 4 ou 5 indicateurs d'un coup : un mini-histogramme par indicateur, mêmes catégories et couleurs partout ; un seul indicateur → chart_bars ; plusieurs séries par catégorie → chart_grouped.",
    "donut_row": "Répartition par régie de plusieurs grandeurs côte à côte (impressions, clics, dépenses) : petits donuts titrés avec pourcentages sur les parts et légende dessous ; une seule répartition → donut.",
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
    "tree": "Arborescence de site, organigramme, plan de rubriques à deux niveaux avec sous-rubriques listées, ou univers de mots-clés à trois niveaux (racine, univers, expressions en boîtes) ; pour des flux entre nœuds → flowchart ; pour un centre et ses satellites → hub_spoke ; pour une page cible et ses pages filles → cocon.",
    "cocon": "Cocon sémantique ou silo : la page cible au centre, ses pages filles autour, les pages d'action (dons, contact) en navy ; pour un écosystème sans notion de page → hub_spoke ; pour une arborescence à niveaux → tree.",
    "cycle": "Boucle sans fin (cycle de recherche off market → pre purchase → purchase → usage, cycle de vie, boucle d'amélioration) ; pour une suite linéaire → process ; pour un graphe orienté → flowchart.",
    "formula": "Raisonnement en équation : deux à cinq facteurs additionnés (ou multipliés) donnent un résultat (personnalisation + géolocalisation + recherche universelle = ranking moins fiable) ; pour des chiffres qui se composent → stat_box.",
    "persona_card": "Fiche persona d'une reco UX ou SEO : identité, contexte, jauges, appareils, attentes et freins ; pour une vraie personne (équipe, interlocuteur) → person_card.",
    "stack": "Pyramide ou pile de niveaux (pyramide SEO, socle → contenus → notoriété, priorités par couche) ; avec volumes et taux → funnel.",

    # --- personnes ---------------------------------------------------------------------
    "person_card": "Une personne : intervenant clé, CV synthétique, contact (photo carrée ou initiales, fonction, bio, contact) ; toute l'équipe → team_grid.",
    "team_grid": "La slide équipe dédiée : 2 à 6 fiches photo + nom + fonction + rôle sur le projet, hauteurs égalisées ; une seule personne → person_card.",

    # --- mockups ---------------------------------------------------------------------
    "browser": "Montrer une capture de site ou de dashboard dans un cadre navigateur plat avec URL (dashboards GA4, maquettes desktop, pages concurrentes) ; ambiance matériel → laptop ; mobile → phone ; résultat Google reconstitué → serp.",
    "laptop": "Mettre en scène une capture desktop dans un laptop (références, maquettes, avant/après de site) ; plus neutre et avec URL → browser ; capture mobile → phone.",
    "phone": "Mettre en scène une capture mobile (maquette responsive, appli, parcours mobile) ; capture desktop → laptop ou browser.",

    # --- bilan média ---------------------------------------------------------------------
    "analysis_block": "Le bloc « Notre analyse : » sous un graphique ou un tableau de bilan : titre gras + points en chevrons (ou un paragraphe avec `text`), `box` pour l'encadrer ; pour une mise en garde ou un message à retenir → callout ; pour une liste sans titre → chevrons.",
    "source_note": "La mention « * Sources : Google Ads du … au … » en haut à droite d'une slide de données, avec la plateforme en dessous ; pour un texte libre → draw.",
    "stat_box": "Deux ou trois chiffres encadrés reliés par un opérateur (taux CMP = part de données remontées) ; avant → après → stat_pair ; avec variation → kpi.",
    "takeaways": "Les slides Enseignements et Recos : titre gras (surligné en option) + paragraphe par point ; pour des points courts sans titre → chevrons ; pour un message unique → callout.",
    "placeholder": "La place d'un élément qui manque encore (export à venir, capture à déposer) dans un deck généré : cadre pointillé avec message ; pour des cases d'images → gallery.",
    "ad_scoreboard": "Résultats par publicité (Meta, Pinterest, YouTube) : une colonne par annonce avec vignette et une ligne par métrique ; pour un tableau classique avec une ligne par annonce → table avec `icons`.",
    "gallery": "Captures d'annonces ou visuels côte à côte à ratio fixe, avec cases « à déposer » tant qu'il n'y a pas d'image ; logos → logo_wall ; capture dans un cadre matériel → phone, laptop, browser.",
    "media_plan": "La slide « Rappel du dispositif et objectifs » d'un bilan : leviers avec logos régies, ordre d'insertion, dates, et panneau objectif ; pour un budget par levier en tableau → table.",
    "timeline_arrow": "Les temps forts d'une campagne sur une flèche (bascules, ajouts, coupures) en boîtes datées alternées ; pour un planning par phases → timeline ; pour des phases détaillées → phase_cards.",

    # --- design system (marque) ---------------------------------------------------------
    "button": "Un CTA pilule qui suit son fond (plein dark sur blanc, contour blanc ou cyan sur dark, plein dark sur cyan / jaune) ; plusieurs côte à côte → button_row ; une capsule de libellé sans action → pill.",
    "button_row": "Le duo CTA principal + secondaire d'une slide (Contact / En savoir plus) sur un même fond ; un seul → button.",
    "hashtags": "Les hashtags de positionnement (#IA #DATA #ÉCO CONCEPTION) en texte nu, capitales, accent sur fond sombre ; jamais en chips → pas badge ni pill.",
    "eyebrow": "Le sur-titre tracké en capitales (« DIGITALE DEPUIS 1999 », un nom de section) au-dessus d'un titre ; pour un tag coloré → badge.",
    "content_card": "Une carte éditoriale du site : réalisation, engagement, show reel, avec eyebrow, titre, texte, hashtags et CTA, sur fond blanc, cyan, dark ou jaune ; plusieurs → content_cards ; carte de constat ou de chiffre → card.",
    "content_cards": "Trois cartes éditoriales sur trois fonds (blanc / cyan / dark), hauteurs égalisées, CTA alignés en bas ; pour des cartes de constats sans CTA → card_grid.",
    "section_header": "L'en-tête de section signature (eyebrow, titre avec surlignage jaune, paragraphe, hashtags) en ouverture d'une partie ou d'une slide manifeste ; pour un sommaire → agenda.",
    "client_ticker": "Le bandeau de références clients en texte seul sur fond sombre ; avec logos → logo_wall.",
    "do_dont": "Ton et vocabulaire : paires ✓ / ✕ de verbatims commentés (on-brand / off-brand) ; idée reçue vs réponse → compare_cards ; listes avant / après → before_after.",

    # --- ateliers et restitutions ---------------------------------------------------------
    "score_matrix": "Notes par famille et par critère (mini audit, satisfaction, maturité) en tuiles colorées par seuil avec le nombre de réponses ; matrice chiffrée sans notes → heatmap ; un seul score → gauge.",
    "ranked_bars": "Résultat d'un vote ou d'un classement de priorités (« 3 choix par personne ») avec le compte à droite et le haut du classement mis en avant ; parts atteintes → compare_bars ; barres commentées avec sous-textes → bar_list.",
    "chip_cloud": "Les sujets ou chantiers cités en atelier, en chips avec compteur ×n ; un seul tag → pill ou badge ; hashtags de marque → hashtags.",
    "quadrant_matrix": "Quatre cadrans titrés (impact × urgence, effort × valeur) à remplir en séance ou déjà remplis d'items ; pour positionner des bulles chiffrées → effort_matrix ou bubbles.",
    "next_steps": "Les prochaines étapes en 3 ou 4 colonnes datées avec l'étape en cours marquée ; frise datée → timeline ; phases détaillées avec livrables → phase_cards.",
    "board_columns": "Le tableau d'un atelier (forces, irritants, chantiers) avec cartes numérotées et colonnes vides assumées ; cartes de constats sans colonnes → card_grid.",
    "session_plan": "Le déroulé d'une réunion ou d'un atelier : sections et bandeau horaire proportionnel ; sommaire simple → agenda.",
    "attention_points": "Alertes et points de vigilance calculés (tracking, budget, structure, qualité) avec niveau critique / vigilance / favorable et chiffres surlignés ; un seul message → callout.",
    "bar_list": "Barres horizontales commentées : pages, canaux ou natures de conversion avec libellé, sous-texte, valeur et état coloré, hachures pour un signal faible ; simple part atteinte → compare_bars ; classement de votes → ranked_bars ; histogramme → chart_bars.",
}
