"""Ready-made settings of the built-in components — the ``variants`` field of the catalogue.

Each variant is ``{title, when, props}``: ``title`` says what it looks like, ``when``
the situation it fits (written for the model reading ``list_components``), ``props``
the call to copy. The catalogue deck renders one slide per variant after the
component's main example.

A component without an entry here still gets variants: the registry derives one per
value of each ``choice`` prop (see ``Component.schema``). Add an entry when the
interesting settings are combinations of props, or when the auto-derived list says
nothing useful about *when* to pick a value.
"""

VARIANTS: dict[str, list[dict]] = {
    # --- chiffres ---------------------------------------------------------------------
    "kpi": [
        {"title": "sans variation, note de source",
         "when": "Indicateur d'état sans comparaison de période (audience du mois, stock de pages) ; la note précise la source.",
         "props": {"value": "4 391", "label": "Sessions", "note": "(GA4)"}},
    ],
    "kpi_grid": [
        {"title": "2 colonnes",
         "when": "Deux indicateurs qui portent la slide (dépenses et collecte) : chacun prend la moitié de la largeur.",
         "props": {"items": [{"value": "130 311 €", "label": "Investissements", "delta": "+35,29 %"}, {"value": "196 623 €", "label": "Collecte", "note": "(GA4)", "delta": "+108,49 %"}], "cols": 2}},
        {"title": "rows : une rangée par libellé (Marque / Hors marque)",
         "when": "Mêmes indicateurs déclinés par segment, campagne ou période : un libellé en gras à gauche de chaque rangée, KPI compacts.",
         "props": {"rows": ["Marque", "Hors marque"], "cols": 3,
                   "items": [{"value": "46 811 €", "label": "Dépenses", "delta": "+52,18 %"}, {"value": "179 083 €", "label": "Collecte", "delta": "+172,10 %"}, {"value": "3,83", "label": "ROAS", "delta": "+78,80 %"},
                             {"value": "36 152 €", "label": "Dépenses", "delta": "+25,59 %"}, {"value": "7 100 €", "label": "Collecte", "delta": "-70,94 %"}, {"value": "0,20", "label": "ROAS", "delta": "-76,86 %"}]}},
        {"title": "3 colonnes sans variation",
         "when": "Chiffres de contexte sans période de comparaison (première campagne, audit initial).",
         "props": {"items": [{"value": "12 400", "label": "Visites"}, {"value": "620", "label": "Leads", "note": "formulaire"}, {"value": "5,0 %", "label": "Taux de conversion"}], "cols": 3}},
    ],
    "kpi_cards": [
        {"title": "2 cartes larges",
         "when": "Deux sources ou deux canaux comparés face à face, avec picto.",
         "props": {"items": [{"label": "Google Ads", "value": "11 454", "delta": "+12 %", "icon": "google"}, {"label": "Meta Ads", "value": "5 950", "delta": "-5 %", "icon": "share"}], "cols": 2, "icon_tint": "ink"}},
    ],
    "stats": [
        {"title": "5 chiffres courts, couleur accent",
         "when": "Rangée dense de chiffres de fierté (ans, clients, pays…) sur une slide « qui sommes-nous ».",
         "props": {"items": [["25", "ans"], ["60", "periscopers"], ["4 M€", "de CA"], ["120", "clients"], ["98 %", "de satisfaction"]], "color": "accent_dark"}},
    ],
    "big_numbers": [
        {"title": "2 colonnes, surlignage cyan",
         "when": "Deux principes larges avec paragraphe long ; le surlignage cyan pour un deck orienté design.",
         "props": {"items": [{"title": "Une page,\nune intention", "text": "Un carrefour oriente et ne raconte rien : la page de service convertit, la page carrefour distribue."},
                             {"title": "La fiscalité est une porte", "text": "La page « don et impôt » pèse près de 10 % des pages vues : elle mérite un parcours dédié."}], "cols": 2, "highlight": "highlight_alt"}},
        {"title": "4 colonnes courtes",
         "when": "Quatre règles ou quatre convictions en une rangée : titres brefs, une ligne de texte.",
         "props": {"items": [{"title": "Clair"}, {"title": "Rapide"}, {"title": "Accessible"}, {"title": "Sobre"}], "cols": 4}},
    ],
    "stat_box": [
        {"title": "enchaînement → sur trois boîtes",
         "when": "Parcours chiffré (visites → leads → clients) : l'opérateur relie les boîtes.",
         "props": {"boxes": [{"value": "12 400", "label": "Visites"}, {"value": "620", "label": "Leads"}, {"value": "74", "label": "Clients"}], "operator": "→"}},
        {"title": "produit ×",
         "when": "Décomposition d'un résultat (trafic × taux × panier) ; se lit comme une formule.",
         "props": {"boxes": [{"value": "2 400", "label": "Clics"}, {"value": "3,1 %", "label": "Taux de conv."}, {"value": "74", "label": "Contacts"}], "operator": "×"}},
    ],
    "takeaways": [
        {"title": "titres surlignés",
         "when": "Deux à trois messages clés à faire ressortir en fin de partie ; le marqueur accent souligne les titres.",
         "props": {"items": [{"title": "Sécuriser le budget des derniers jours", "text": "Les 7 derniers jours concentrent 52 % de la collecte GA4."},
                             {"title": "Réévaluer le budget search", "text": "Environ 56 851 € de collecte potentielle perdue faute de budget."}], "highlight": True}},
    ],

    # --- cartes ---------------------------------------------------------------------
    "card": [
        {"title": "mint, picto en disque",
         "when": "La carte à mettre en avant dans une série (constat clé, offre retenue) : fond menthe, picto en disque blanc.",
         "props": {"variant": "mint", "icon": "bolt", "label": "Constat", "title": "Un levier d'engagement", "body": "9 874 joueurs, 12 851 parties."}},
        {"title": "outline, gros chiffre",
         "when": "Un chiffre fort dans un cadre léger sans fond : à poser sur une slide déjà chargée.",
         "props": {"variant": "outline", "big": "+42 %", "label": "Trafic organique", "body": "vs 2025, hors marque"}},
        {"title": "acid, numéro",
         "when": "Accent jaune acide pour distinguer une carte d'une série (l'étape en cours, l'option recommandée).",
         "props": {"variant": "acid", "num": "02", "title": "Performance", "body": "- CRO\n- Conversion"}},
        {"title": "plain, sans fond",
         "when": "Texte structuré sans cadre ni fond : sur un fond coloré, une image ou dans une colonne déjà encadrée.",
         "props": {"variant": "plain", "label": "Méthode", "title": "Trois ateliers", "body": "Cadrage, idéation, priorisation."}},
    ],
    "card_grid": [
        {"title": "2 colonnes numérotées",
         "when": "Deux piliers ou deux options face à face : cartes larges avec numéro et liste.",
         "props": {"cards": [{"num": "01", "title": "Visibilité", "body": "- Autorité de domaine\n- Contenu evergreen", "dot": True},
                             {"num": "02", "title": "Conversion", "body": "- Parcours don\n- Formulaires", "dot": True}], "cols": 2}},
        {"title": "4 colonnes, libellé + titre",
         "when": "Quatre valeurs ou quatre briques en une rangée : textes courts, pas de picto.",
         "props": {"cards": [{"label": "Stratégie", "title": "Cadrer"}, {"label": "Data", "title": "Mesurer"}, {"label": "Design", "title": "Concevoir"}, {"label": "Tech", "title": "Construire"}], "cols": 4}},
    ],
    "callout": [
        {"title": "info",
         "when": "Précision neutre ou définition (périmètre, méthode de calcul).",
         "props": {"type": "info", "title": "Périmètre", "body": "Données Google Ads du 01/12 au 31/12, hors marque."}},
        {"title": "warn",
         "when": "Point de vigilance sans gravité immédiate (donnée partielle, estimation).",
         "props": {"type": "warn", "title": "Attention", "body": "Le tracking GA4 a été coupé du 12 au 15 : les conversions sont sous-estimées."}},
        {"title": "alert",
         "when": "Problème bloquant ou risque fort à traiter en priorité.",
         "props": {"type": "alert", "title": "Blocage", "body": "Le formulaire de don renvoie une erreur 500 sur mobile."}},
    ],
    "content_card": [
        {"title": "fond blanc, tags, CTA contour",
         "when": "Carte réalisation ou offre sur fond blanc : sur-titre, titre, tags et bouton en contour.",
         "props": {"ground": "white", "eyebrow": "Réalisation", "title": "Mirova — refonte ==éco-conçue==", "text": "Un site carbone-light, accessible AA.", "tags": ["UX", "ÉCO"], "cta": "Voir le cas", "cta_variant": "outline"}},
        {"title": "fond jaune acide",
         "when": "Carte d'accroche ou d'appel à l'action forte (événement, offre limitée).",
         "props": {"ground": "yellow", "eyebrow": "Événement", "title": "Atelier IA générative, le 12 octobre.", "text": "Une matinée pour cadrer vos cas d'usage.", "cta": "S'inscrire"}},
        {"title": "fond navy (show reel)",
         "when": "Bloc vidéo ou citation forte : le fond sombre hérité du design system, réservé à cette carte.",
         "props": {"ground": "dark", "eyebrow": "Show reel", "title": "L'agence engagée, des marques engagées.", "text": "2 minutes pour comprendre comment Periscope travaille.", "cta": "▶  Lire la vidéo"}},
    ],
    "content_cards": [
        {"title": "2 cartes larges",
         "when": "Deux cartes face à face (réalisation + engagement) avec plus de texte.",
         "props": {"cards": [{"ground": "white", "eyebrow": "Réalisation", "title": "Mirova — refonte éco-conçue", "text": "Un site carbone-light, accessible AA, qui double le temps passé sur les articles.", "tags": ["UX", "ÉCO"]},
                             {"ground": "cyan", "eyebrow": "Engagement", "title": "60 periscopers pour concevoir des expériences durables.", "text": "Stratégie, data, IA, design, tech.", "cta": "L'équipe"}], "cols": 2}},
    ],
    "section_header": [
        {"title": "centré, sans tags",
         "when": "Slide de chapitre ou d'ouverture : titre centré, un paragraphe.",
         "props": {"eyebrow": "Partie 2", "title": "Ce que disent les ==données==.", "text": "Trois mois de campagne, quatre régies, un objectif.", "align": "CENTER"}},
        {"title": "court : sur-titre et titre",
         "when": "Chapeau de section au-dessus d'un composant qui prend la slide.",
         "props": {"eyebrow": "Résultats", "title": "Une collecte ==doublée== en un an.", "size": 20}},
    ],
    "button": [
        {"title": "contour sur blanc",
         "when": "Action secondaire (en savoir plus, voir le cas) à côté d'un bouton plein.",
         "props": {"text": "En savoir plus", "variant": "outline"}},
        {"title": "navy plein, prévu pour un fond jaune",
         "when": "Bouton posé sur un bandeau ou une carte jaune acide : `ground` choisit les couleurs du bouton, le fond lui-même n'est pas dessiné.",
         "props": {"text": "Prendre rendez-vous", "ground": "yellow"}},
    ],
    "button_row": [
        {"title": "contours centrés",
         "when": "Boutons en contour centrés sous un titre de section ou une carte.",
         "props": {"items": [{"text": "Contact"}, {"text": "En savoir plus"}, {"text": "Télécharger"}], "variant": "outline", "align": "CENTER"}},
        {"title": "prévue pour un fond jaune",
         "when": "Bandeau CTA sur fond jaune acide : boutons navy pleins (le fond n'est pas dessiné, `ground` choisit les couleurs).",
         "props": {"items": [{"text": "Prendre rendez-vous"}, {"text": "Voir l'offre", "variant": "outline"}], "ground": "yellow"}},
    ],

    # --- listes ---------------------------------------------------------------------
    "numbered_list": [
        {"title": "sobre : carrés, sans carte ni fil",
         "when": "Liste numérotée compacte sur une slide dense (rappel d'objectifs, ordre du jour).",
         "props": {"items": ["Cadrer les objectifs", "Auditer l'existant", "Prioriser les chantiers"], "marker": "square"}},
        {"title": "numérotation reprise à 4",
         "when": "Suite d'une liste commencée sur la slide précédente.",
         "props": {"items": [{"title": "Mesurer", "sub": "Tableau de bord mensuel"}, {"title": "Ajuster", "sub": "Revue trimestrielle"}], "start": 4, "card": True}},
    ],

    # --- graphiques ---------------------------------------------------------------------
    "chart_bars": [
        {"title": "horizontal, libellés longs",
         "when": "Classement de catégories aux libellés longs (pages par erreur, requêtes, régies) : barres horizontales sur pistes grises.",
         "props": {"labels": ["Erreurs 404", "Titres dupliqués", "Images sans alt", "Pages lentes", "Liens cassés"], "values": [1320, 860, 540, 210, 95], "horizontal": True}},
        {"title": "mensuel, séparateur de période, panel",
         "when": "Série mensuelle avec un changement de période (avant / après refonte, ISF / IFI) : axe gradué, séparateur, cadre.",
         "props": {"labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août"], "values": [120, 140, 135, 160, 210, 260, 240, 290], "y_axis": True,
                   "dividers": [{"after": "Avr", "left": "Avant", "right": "Après"}], "panel": True, "title": "Sessions mensuelles", "color": "accent"}},
        {"title": "simple, une couleur, valeurs seules",
         "when": "Comparaison courte sans axe : les valeurs sur chaque barre suffisent.",
         "props": {"labels": ["Search", "Social", "Display", "Email"], "values": [42, 28, 18, 12], "unit": "%", "color": "accent_dark"}},
    ],
    "chart_line": [
        {"title": "une courbe, marqueurs, panel",
         "when": "Une seule série (sessions mensuelles, positions) : pas de légende, marqueurs, titre et cadre.",
         "props": {"labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"], "series": [{"name": "Sessions", "values": [120, 140, 135, 160, 210, 260], "color": "accent_dark"}],
                   "markers": True, "panel": True, "title": "Sessions organiques"}},
        {"title": "3 séries, légende en haut, plafond fixé",
         "when": "Plusieurs canaux sur la même échelle (une couleur de régie par courbe) ; `y_max` fige l'échelle entre slides.",
         "props": {"labels": ["S1", "S2", "S3", "S4", "S5"], "series": [{"name": "Google", "values": [40, 55, 60, 58, 70], "color": "regie_google"}, {"name": "Meta", "values": [20, 25, 35, 30, 45], "color": "regie_meta"},
                                                                   {"name": "Bing", "values": [5, 8, 6, 9, 12], "color": "regie_bing"}], "y_max": 80, "legend_pos": "top"}},
    ],
    "chart_stacked": [
        {"title": "horizontal, valeurs, légende en bas",
         "when": "Répartition par canal ou par segment en barres horizontales empilées, valeurs lisibles dans les segments.",
         "props": {"labels": ["Search", "Social", "Display"], "series": [{"name": "Marque", "values": [46811, 12000, 3000]}, {"name": "Hors marque", "values": [36152, 18000, 9000]}],
                   "horizontal": True, "show_values": True, "unit": "€", "legend_pos": "bottom"}},
        {"title": "vertical simple, deux séries",
         "when": "Évolution d'un total décomposé en deux parts (digital / hors digital) sans séparateur ni axe.",
         "props": {"labels": ["2023", "2024", "2025"], "series": [{"name": "Hors digital", "values": [3.3, 3.5, 3.8]}, {"name": "Digital", "values": [0.8, 1.2, 1.4]}], "unit": "M€", "show_values": True}},
    ],
    "chart_grouped": [
        {"title": "horizontal",
         "when": "Catégories nombreuses ou libellés longs : barres groupées horizontales.",
         "props": {"labels": ["Search Marque", "Search Hors marque", "PMax", "Demand Gen"], "series": [{"name": "N", "values": [179083, 7100, 10440, 4200]}, {"name": "N-1", "values": [65800, 24400, 4060, 0]}],
                   "horizontal": True, "unit": "€"}},
        {"title": "couleur par série (N navy, N-1 gris)",
         "when": "Comparer deux périodes quand la couleur doit dire la période et non la régie.",
         "props": {"labels": ["Google", "Bing", "Facebook", "Instagram"], "series": [{"name": "Collecte N", "values": [356118, 35079, 60007, 11522], "color": "accent_dark"},
                                                                                {"name": "Collecte N-1", "values": [0, 47353, 36090, 11726], "color": "gray_2"}], "unit": "€", "legend_pos": "bottom"}},
    ],
    "chart_combo": [
        {"title": "séparateur de période, légende en bas, panel",
         "when": "Bilan mensuel avec un changement de dispositif au milieu (avant / après), dans un cadre.",
         "props": {"labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"], "bars": {"name": "Dépenses", "values": [694, 825, 893, 817, 1200, 1350]},
                   "line": {"name": "Contacts", "values": [20, 48, 56, 59, 80, 95], "color": "regie_meta"}, "unit": "€", "dividers": [{"after": "Mar", "left": "Test", "right": "Scale"}],
                   "legend_pos": "bottom", "panel": True, "title": "Dépenses et contacts"}},
        {"title": "beaucoup de points : sans valeurs ni marqueurs",
         "when": "Jour par jour sur un mois : seule la forme compte, valeurs et marqueurs retirés.",
         "props": {"labels": [f"{d:02d}" for d in range(1, 32)], "bars": {"name": "Dépenses", "values": [943, 2319, 2964, 2850, 2723, 2377, 2272, 2258, 2555, 2545, 2946, 2961, 3784, 3483, 3314, 3149, 2904, 2984, 2900, 3127, 2951, 3352, 3094, 3424, 2956, 3456, 3793, 3794, 4250, 17248, 31338]},
                   "line": {"name": "Collecte", "values": [610, 2065, 4710, 2620, 1937, 2992, 3865, 3250, 3272, 4155, 3601, 1880, 3875, 2793, 5315, 4800, 4840, 3905, 5165, 3630, 7135, 6462, 8385, 10505, 2685, 6785, 7455, 4230, 14120, 30550, 42893], "color": "regie_meta"},
                   "unit": "€", "show_values": False, "markers": False}},
    ],
    "donut": [
        {"title": "total au centre, légende à droite",
         "when": "Sur une demi-slide à côté d'un texte : le total au centre, la légende à droite.",
         "props": {"segments": [{"label": "Google", "value": 740, "color": "regie_google"}, {"label": "Meta", "value": 300, "color": "regie_meta"}, {"label": "Bing", "value": 110, "color": "regie_bing"}, {"label": "Pinterest", "value": 54, "color": "regie_pinterest"}],
                   "center": "1 204\ndons", "legend_pos": "right"}},
        {"title": "compact : pourcentages sur les parts, sans légende, panel",
         "when": "Donut compact quand les couleurs sont expliquées ailleurs (légende partagée, tableau à côté).",
         "props": {"segments": [{"label": "Mobile", "value": 68, "color": "accent"}, {"label": "Desktop", "value": 27, "color": "accent_dark"}, {"label": "Tablette", "value": 5, "color": "gray_2"}],
                   "labels": True, "legend_pos": "none", "panel": True, "title": "Appareils"}},
    ],
    "donut_row": [
        {"title": "2 donuts, légende à droite",
         "when": "Deux répartitions côte à côte, chacune avec sa légende à droite.",
         "props": {"items": [{"title": "Impressions", "segments": [{"label": "Google", "value": 13}, {"label": "Meta", "value": 87}]}, {"title": "Dépenses", "segments": [{"label": "Google", "value": 70}, {"label": "Meta", "value": 30}]}],
                   "colors": ["regie_google", "regie_meta"], "legend_pos": "right", "labels": False}},
        {"title": "4 donuts compacts, sans légende",
         "when": "Mini bilan : quatre répartitions qui partagent une légende posée ailleurs sur la slide.",
         "props": {"items": [{"title": "Impressions", "segments": [{"label": "Google", "value": 13}, {"label": "Bing", "value": 1}, {"label": "Meta", "value": 86}]},
                             {"title": "Clics", "segments": [{"label": "Google", "value": 62}, {"label": "Bing", "value": 5}, {"label": "Meta", "value": 33}]},
                             {"title": "Dépenses", "segments": [{"label": "Google", "value": 70}, {"label": "Bing", "value": 11}, {"label": "Meta", "value": 19}]},
                             {"title": "Dons", "segments": [{"label": "Google", "value": 74}, {"label": "Bing", "value": 8}, {"label": "Meta", "value": 18}]}],
                   "colors": ["regie_google", "regie_bing", "regie_meta"], "cols": 4, "legend_pos": "none"}},
    ],
    "funnel": [
        {"title": "taux étape par étape",
         "when": "Taux de passage d'une étape à la suivante (conversion du parcours).",
         "props": {"items": [{"label": "Visites", "value": 12400}, {"label": "Fiches produit", "value": 4100}, {"label": "Paniers", "value": 620}, {"label": "Commandes", "value": 74}], "pct": "prev"}},
        {"title": "volumes seuls avec unité",
         "when": "Montants par étape (budget, collecte) sans taux.",
         "props": {"items": [{"label": "Budget", "value": 33000}, {"label": "Dépensé", "value": 28400}, {"label": "Collecté", "value": 18700}], "pct": "none", "unit": "€"}},
    ],
    "bar_list": [
        {"title": "simple : valeur dans la barre, sans états",
         "when": "Classement commenté court sans légende d'états : la valeur s'aligne dans la piste.",
         "props": {"items": [{"label": "amnesty.fr/legs", "value": 999.59}, {"label": "questionnaire-legs.amnesty.fr", "value": 511.88}, {"label": "transmettre.amnesty.fr", "value": 28.15}], "value_in_bar": True, "unit": "€"}},
    ],
    "score_matrix": [
        {"title": "2 critères, sans effectifs ni légende",
         "when": "Matrice courte (deux critères) dans une slide qui explique les seuils ailleurs.",
         "props": {"columns": ["Qualité", "Délais"], "rows": [{"label": "Sites web", "values": [2.5, 1.5]}, {"label": "CRM", "values": [3.7, 3.7]}, {"label": "Media", "values": [3.3, 2.0]}], "legend": False}},
    ],

    # --- blocs ---------------------------------------------------------------------
    "pill": [
        {"title": "pleine, compteur",
         "when": "Tag avec compteur « ×n » (occurrences d'un thème, votes) dans un nuage.",
         "props": {"text": "SEO", "count": 12}},
        {"title": "pleine acide",
         "when": "Pilule colorée pour un état ou une catégorie à distinguer.",
         "props": {"text": "En cours", "color": "acid"}},
    ],
    "source_note": [
        {"title": "avec logo, alignée à gauche",
         "when": "Sous un tableau ou un graphique aligné à gauche, avec le picto de la régie.",
         "props": {"text": "Meta Ads du 01/12/2025 au 31/12/2025", "platform": "Meta Ads", "logo": "share", "tint": "muted", "align": "START"}},
    ],
    "logo_wall": [
        {"title": "noms sous les logos, 3 colonnes",
         "when": "Partenaires ou outils avec leur nom en dessous.",
         "props": {"logos": [{"logo": "google", "name": "Google Ads"}, {"logo": "share", "name": "Meta"}, {"logo": "video", "name": "YouTube"}], "cols": 3, "names": True, "tint": "ink"}},
    ],
    "timeline_arrow": [
        {"title": "tous en dessous",
         "when": "Peu d'événements : tous sous la flèche, sans alternance.",
         "props": {"events": [{"date": "11/04", "text": "Début de la campagne", "style": "filled"}, {"date": "07/05", "text": "Bascule MDD IR"}, {"date": "27/05", "text": "Fin de campagne", "style": "outline"}], "alternate": False}},
    ],
    "person_card": [
        {"title": "photo au-dessus",
         "when": "Colonne étroite ou grille : photo au-dessus du nom.",
         "props": {"name": "Aurélie M.", "role": "Directrice de clientèle", "bio": "Coordonne le projet.", "layout": "top"}},
    ],
    "team_grid": [
        {"title": "photo au-dessus, 4 colonnes",
         "when": "Trombinoscope en colonnes, bio courte.",
         "props": {"people": [{"name": "Arnaud M.", "role": "Directeur associé"}, {"name": "Aurélie M.", "role": "Directrice de clientèle"}, {"name": "Théo L.", "role": "UX/UI designer"}, {"name": "Sébastien N.", "role": "Développeur web"}], "layout": "top", "cols": 4}},
        {"title": "2 personnes, bio longue",
         "when": "Deux interlocuteurs clés présentés avec leur rôle détaillé.",
         "props": {"people": [{"name": "Arnaud M.", "role": "Directeur associé", "bio": "Supervision stratégique, garantie de la qualité des livrables et de la relation."}, {"name": "Aurélie M.", "role": "Directrice de clientèle", "bio": "Pilote le projet, l'accompagnement et le planning."}], "cols": 2}},
    ],
    "table": [
        {"title": "simple : en-tête accent, titres seuls, total accent",
         "when": "Petit tableau de synthèse (3 à 5 colonnes, budget par levier, planning) sans pictos ni sous-lignes : le défaut quand rien ne justifie plus.",
         "props": {"rows": [["Levier", "Budget", "Part"], ["Google Ads", "18 000 €", "45 %"], ["Meta", "12 000 €", "30 %"], ["Pinterest", "3 000 €", "8 %"], ["Total", "33 000 €", "83 %"]],
                   "align": [None, "END", "END"], "total_row": True}},
        {"title": "pictos de canaux, en-tête sombre, total gris",
         "when": "Résultats par canal ou par régie (Search, Discover, YouTube, Meta…) : un picto par ligne identifie le canal, en-tête navy et total gris pour un bilan média dense.",
         "props": {"rows": [["Canal", "Impr.", "Clics", "Conv.", "Coût"], ["Recherche Google", "86 085", "4 530", "147", "18 024 €"], ["Discover", "1 729 943", "31 683", "50", "3 445 €"],
                            ["YouTube", "115 432", "811", "5", "442 €"], ["Gmail", "21 147", "586", "1", "74 €"], ["Total", "1 952 607", "37 610", "203", "21 985 €"]],
                   "icons": ["search", "star", "video", "share"], "icon_tint": "ink", "header_fill": "ink", "total_fill": "surface", "total_row": True,
                   "align": [None, "END", "END", "END", "END"]}},
        {"title": "colonne « vs N-1 » colorée par signe, sans total",
         "when": "Comparaison période à période (N vs N-1, avant / après) : `delta_cols` colore les variations en vert / corail selon le signe ; pas de total quand les lignes ne s'additionnent pas.",
         "props": {"rows": [["Famille", "Dépenses", "vs N-1", "Collecte GA4", "vs N-1", "ROAS"], ["Search Marque", "46 811 €", "+52,18 %", "179 083 €", "+172,10 %", "3,83"],
                            ["Search Hors marque", "36 152 €", "+25,59 %", "7 100 €", "-70,94 %", "0,20"], ["PMax", "22 296 €", "+138,61 %", "10 440 €", "+156,83 %", "0,47"]],
                   "delta_cols": [2, 4], "align": [None, "END", "END", "END", "END", "END"]}},
        {"title": "CPA en pilules par seuil, cumul en menthe",
         "when": "Suivi mensuel avec une métrique à juger (CPA, CPL, ROAS) : `pill_cols` met la colonne en pilules colorées par seuil, ligne de cumul menthe ; l'exemple principal combine tout (pastilles, sous-lignes, zéros, n/a).",
         "props": {"rows": [["Mois", "Impr.", "Clics", "CTR", "Coût", "Conv.", "CPA"], ["Janvier", "8 981", "946", "10,53 %", "694,28 €", "20", "34,71 €"],
                            ["Février", "9 820", "1 296", "13,20 %", "825,58 €", "48", "17,20 €"], ["Mars", "10 717", "1 443", "13,46 %", "893,63 €", "56", "15,96 €"],
                            ["Avril", "10 077", "1 161", "11,52 %", "817,64 €", "59", "13,86 €"], ["Cumul", "39 595", "4 846", "12,24 %", "3 231,13 €", "183", "17,66 €"]],
                   "header_fill": "ink", "total_row": True, "align": [None, "END", "END", "END", "END", "END", "CENTER"],
                   "pill_cols": {"6": [{"max": 17, "color": "accent"}, {"max": 30, "color": "accent_alt"}, {"color": "coral"}]}}},
    ],
}


# --- natif Google Sheets ---------------------------------------------------------------
# The same charts (and a table) built by the Google Sheets MCP and embedded linked in Slides.
# ``native.sheets`` is what to give the Sheets MCP (data rows, then ``manage_chart add`` arguments
# without ``spreadsheet`` / ``sheet``); ``native.slides`` is the gslide-mcp call. The drawn ``props``
# stay the fallback when the deck has no spreadsheet.

_SHEETS_FLOW = ("Classeur : celui de l'utilisateur ou create_spreadsheet nommé comme le deck ; set_theme preset periscope une fois ; "
                "write_values des données ; format_cells number_format '#,##0' (ou '#,##0\" €\"') sur les colonnes de valeurs — les étiquettes et l'axe "
                "des graphiques suivent le format des cellules (1 085 349 au lieu de 1085349) ; manage_chart add (renvoie chart_id) ; "
                "puis insert_sheets_chart côté Slides, refresh_sheets_charts quand les données bougent.")
_CHART_SLIDES = "insert_sheets_chart(deck, slide, spreadsheet, chart_id, x_pt, y_pt, width_pt, height_pt) — relié : suit le classeur ; refresh_sheets_charts après une modification."


def _native_chart(title: str, when: str, props: dict, data: list[list], chart: dict) -> dict:
    return {"title": title, "when": when, "props": props,
            "native": {"kind": "chart", "flow": _SHEETS_FLOW, "sheets": {"data": data, "manage_chart": {"action": "add", "headers": 1, "style": "periscope", **chart}},
                       "slides": _CHART_SLIDES}}


VARIANTS["chart_bars"].append(_native_chart(
    "natif Sheets, relié (column)",
    "Quand les chiffres vivent dans un classeur ou doivent se rafraîchir (bilan récurrent) : colonnes Sheets à la charte, une couleur de régie par barre via point_colors, valeurs affichées.",
    {"labels": ["Google", "Bing", "Facebook", "Instagram"], "values": [3.9, 2.5, 3.45, 1.5], "colors": ["regie_google", "regie_bing", "regie_facebook", "regie_instagram"], "title": "ROAS par régie"},
    [["Régie", "ROAS"], ["Google", 3.9], ["Bing", 2.5], ["Facebook", 3.45], ["Instagram", 1.5]],
    {"chart_type": "column", "domain": "A1:A5", "series": ["B1:B5"], "title": "ROAS par régie", "legend": "none", "data_labels": True,
     "point_colors": ["1:1 #00e5c3", "1:2 #c383ff", "1:3 #fa00a6", "1:4 #ff9170"]}))

VARIANTS["chart_grouped"].append(_native_chart(
    "natif Sheets, relié (colonnes N / N-1)",
    "Comparaison N / N-1 reliée au classeur : deux séries, N en navy et N-1 en gris (convention charte), valeurs sur les barres, légende en haut.",
    {"labels": ["Google", "Bing", "Facebook", "Instagram"], "series": [{"name": "Collecte N", "values": [356118, 35079, 60007, 11522], "color": "accent_dark"},
                                                                       {"name": "Collecte N-1", "values": [0, 47353, 36090, 11726], "color": "gray_2"}], "unit": "€", "legend_pos": "top"},
    [["Régie", "Collecte N", "Collecte N-1"], ["Google", 356118, 0], ["Bing", 35079, 47353], ["Facebook", 60007, 36090], ["Instagram", 11522, 11726]],
    {"chart_type": "column", "domain": "A1:A5", "series": ["B1:B5", "C1:C5"], "title": "Collecte N et N-1 par régie", "legend": "top",
     "series_colors": ["#002b3c", "#ededed"], "data_labels": True}))

VARIANTS["chart_stacked"].append(_native_chart(
    "natif Sheets, relié (colonnes empilées)",
    "Total décomposé en parts, relié au classeur : stacked, une couleur charte par série, légende en haut ; percent pour des parts en %.",
    {"labels": ["2023", "2024", "2025"], "series": [{"name": "Hors digital", "values": [3.3, 3.5, 3.8]}, {"name": "Digital", "values": [0.8, 1.2, 1.4]}], "unit": "M€", "show_values": True},
    [["Année", "Hors digital", "Digital", "Dons ≥ 1 000 €"], [2023, 3.3, 0.8, 1.2], [2024, 3.5, 1.2, 1.3], [2025, 3.8, 1.4, 1.4]],
    {"chart_type": "column", "stacked": "stacked", "domain": "A1:A4", "series": ["B1:B4", "C1:C4", "D1:D4"], "title": "Collecte par source (M€)", "legend": "top",
     "series_colors": ["#002b3c", "#00f5b5", "#45dbff"], "data_labels": True}))

VARIANTS["chart_line"].append(_native_chart(
    "natif Sheets, relié (courbes)",
    "Évolution reliée au classeur : une couleur charte par courbe, la période précédente en pointillé (line_dash), largeur 2 px, valeurs sur les points, légende en haut.",
    {"labels": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"], "series": [{"name": "2025", "values": [120, 140, 135, 160, 150, 170], "color": "accent_dark"},
                                                                       {"name": "2026", "values": [130, 150, 165, 190, 210, 240], "color": "accent"}], "legend_pos": "top"},
    [["Mois", "2025", "2026"], ["Jan", 120, 130], ["Fév", 140, 150], ["Mar", 135, 165], ["Avr", 160, 190], ["Mai", 150, 210], ["Juin", 170, 240]],
    {"chart_type": "line", "domain": "A1:A7", "series": ["B1:B7", "C1:C7"], "title": "Sessions organiques", "legend": "top",
     "series_colors": ["#ededed", "#002b3c"], "line_dash": ["dashed", "solid"], "line_width": [2, 2], "data_labels": True}))

VARIANTS["chart_combo"].append(_native_chart(
    "natif Sheets, relié (combo colonnes + courbe)",
    "Barres et courbe sur second axe reliées au classeur : series_types column / line, series_axes left / right, barres menthe, courbe magenta 2 px (line_width entier par série, 0 pour la série colonne).",
    {"labels": ["2021", "2022", "2023", "2024", "2025", "2026"], "bars": {"name": "Collecte annuelle", "values": [664974, 1085349, 826300, 1152729, 1067244, 708134]},
     "line": {"name": "Nombre de dons", "values": [524, 780, 497, 780, 404, 259], "color": "regie_meta"}, "unit": "€"},
    [["Année", "Collecte annuelle", "Nombre de dons"], [2021, 664974, 524], [2022, 1085349, 780], [2023, 826300, 497], [2024, 1152729, 780], [2025, 1067244, 404], [2026, 708134, 259]],
    {"chart_type": "combo", "domain": "A1:A7", "series": ["B1:B7", "C1:C7"], "series_types": ["column", "line"], "series_axes": ["left", "right"],
     "series_colors": ["#00f5b5", "#fa00a6"], "line_width": [0, 2], "title": "Collecte et nombre de dons", "legend": "top", "data_labels": True}))

VARIANTS["donut"].append({**_native_chart(
    "natif Sheets, relié (doughnut)",
    "Répartition reliée au classeur : doughnut pie_hole 0,55, légende à droite, 400 × 400 px. Couleurs des parts = accents du thème à partir d'accent2 : set_theme avec les accents dans l'ordre des régies (valable pour tout le classeur). Les % sur les parts ne se posent qu'à la main dans Sheets (Libellé de secteur → Pourcentage ; un update les efface) : donut dessiné si les % doivent se lire sans intervention.",
    {"segments": [{"label": "Google", "value": 62, "color": "regie_google"}, {"label": "Meta", "value": 25, "color": "regie_meta"}, {"label": "Bing", "value": 13, "color": "regie_bing"}],
     "labels": True, "legend_pos": "bottom", "title": "Répartition des dépenses"},
    [["Régie", "Dépenses"], ["Google", 62], ["Meta", 25], ["Bing", 13]],
    {"chart_type": "doughnut", "domain": "A1:A4", "series": ["B1:B4"], "pie_hole": 0.55, "legend": "right", "title": "Répartition des dépenses", "width": 400, "height": 400}),
    "native_extra": None})
VARIANTS["donut"][-1]["native"]["sheets"]["set_theme"] = {"colors": {"accent2": "#00e5c3", "accent3": "#fa00a6", "accent4": "#c383ff", "accent5": "#ff9170", "accent6": "#45dbff"},
                                                         "note": "les parts prennent accent2, accent3… dans l'ordre des lignes : ranger les accents comme les régies (Google, Meta, Bing, Instagram, GA4) ; un seul thème par classeur, donc un seul ordre pour tous les camemberts"}
del VARIANTS["donut"][-1]["native_extra"]

VARIANTS["pie"] = VARIANTS.get("pie", []) + [_native_chart(
    "natif Sheets, relié (pie)",
    "Camembert relié au classeur : pie plein, légende à droite ; mêmes règles que le doughnut (couleurs par l'ordre des accents du thème, % sur les parts à la main seulement, pie_labels invisible dans Slides).",
    {"segments": [{"label": "Mobile", "value": 68}, {"label": "Desktop", "value": 27}, {"label": "Tablette", "value": 5}]},
    [["Appareil", "Sessions"], ["Mobile", 68], ["Desktop", 27], ["Tablette", 5]],
    {"chart_type": "pie", "domain": "A1:A4", "series": ["B1:B4"], "legend": "right", "title": "Sessions par appareil", "width": 400, "height": 400})]

VARIANTS["table"].append({
    "title": "alimentée par Sheets (lecture, pas de liaison)",
    "when": "Quand les chiffres vivent dans un classeur (formules, cumuls) : le MCP Sheets écrit ou lit la plage, gslide la rend en table chartée. L'API Slides n'offre pas de tableau relié : pour actualiser, relire la plage et réinsérer la table.",
    "props": {"rows": [["Canal", "Impr.", "Clics", "Conv.", "Coût"], ["Recherche Google", "86 085", "4 530", "147", "18 024 €"], ["Discover", "1 729 943", "31 683", "50", "3 445 €"],
                       ["YouTube", "115 432", "811", "5", "442 €"], ["Gmail", "21 147", "586", "1", "74 €"], ["Total", "1 952 607", "37 610", "203", "21 985 €"]],
              "header_fill": "ink", "total_fill": "surface", "total_row": True, "align": [None, "END", "END", "END", "END"]},
    "native": {"kind": "table", "flow": _SHEETS_FLOW,
               "sheets": {"data": [["Canal", "Impr.", "Clics", "Conv.", "Coût"], ["Recherche Google", 86085, 4530, 147, 18024], ["Discover", 1729943, 31683, 50, 3445],
                                   ["YouTube", 115432, 811, 5, 442], ["Gmail", 21147, 586, 1, 74], ["Total", "=SUM(B2:B5)", "=SUM(C2:C5)", "=SUM(D2:D5)", "=SUM(E2:E5)"]],
                          "format_cells": [{"range": "B2:D6", "number_format": "number:#,##0"}, {"range": "E2:E6", "number_format": "currency:#,##0\" €\""}],
                          "read_range": {"range": "A1:E6", "formatted": True, "format": "json"}},
               "slides": "insert_component(deck, slide, 'table', {rows: <lignes lues>, header_fill: 'ink', total_row: true, align: [...]}) ; delete_component puis réinsérer pour actualiser."},
})
