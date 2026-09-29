---
name: gslides-prez
description: Utiliser dès que l'utilisateur veut produire une présentation Google Slides (reco, AO, bilan, audit, prez client) à partir d'un Google Slides type ou template, avec le connecteur Péri Slides MCP (gslides-mcp, hébergé ou local), ou modifier un deck déjà copié ou déjà produit ainsi (« j'ai déjà copié, tu peux modifier »), ou remettre à la charte un deck existant (« refais-moi ce deck dans notre template », « reprends ces slides proprement »). Aussi quand il donne une URL docs.google.com/presentation et parle de « faire une prez », « des slides », « un deck », ou veut des graphiques ou des tableaux reliés à un Google Sheets dans ses slides (Péri Sheets MCP + Péri Slides MCP), y compris un bilan récurrent dont les chiffres vivent dans un classeur.
---

# Présentation Google Slides depuis un deck type (Péri Slides MCP + Péri Sheets MCP)

Le deck type porte la charte (masters, layouts, décors). On construit **sur une copie vidée** de ce deck, avec ses layouts et les composants chartés du MCP. Les chiffres qui vivent dans un classeur passent par **Péri Sheets MCP** et arrivent dans les slides reliés.

**Trois règles absolues**

1. **Le deck type est en lecture seule.** Aucun outil d'écriture ne reçoit son id : ni `build_from_outline`, ni `insert_component`, ni `delete_slides`, ni `set_*`. Tout se fait sur une **copie de travail** : celle que crée `clone_deck`, ou celle que l'utilisateur désigne lui-même (« j'ai déjà copié, tu peux modifier », « c'est une copie de mon template, écris dedans »). Dans ce cas on travaille dedans sans recloner ; on le redit en une ligne dans le premier message, et l'URL donnée est la copie, pas le type. Même règle pour un classeur source que l'utilisateur ne demande pas de modifier : on le lit, on écrit dans un autre.
2. **Étapes gated** : validation explicite de l'utilisateur avant l'étape suivante. La pression (« call dans 40 min », « pas de questions ») raccourcit les messages, pas les étapes : un plan de 8 slides tient en 10 lignes et se valide en une réponse.
3. **On n'invente pas la matière.** Chiffres, faits client, résultats, dates et périodes : ils viennent du brief, des documents lus, du classeur désigné ou de `periscope.md`. À défaut, la valeur est écrite `[À CONFIRMER]`, jamais plausible-et-fausse.

Violer la lettre de ces règles, c'est violer leur esprit.

**Trois modes.** *Création* : URL d'un deck type → tout le parcours 0 → 5. *Reprise* : l'utilisateur donne un deck déjà copié ou déjà produit avec ce skill et demande une modification (ajouter, refaire, corriger des slides, mettre à jour les chiffres d'un bilan) → pas de clone, cadrage réduit à ce qui manque (les layouts se lisent dans le deck : `list_slides` + `list_layouts`, les slides existantes disent lesquels sont en usage ; `list_sheets_charts` dit quels graphiques sont reliés à quel classeur), plan limité aux slides touchées, puis 2 → 5. Les slides qu'on n'a pas à toucher ne bougent pas. *Refonte* : un deck **source** (ancienne charte, autre agence, export PowerPoint) à refaire dans une **nouvelle** présentation bâtie sur le deck type → on ne copie pas ses slides, on en réécrit le contenu avec les layouts et les composants (section « Refonte »). Le deck source est en lecture seule comme le type.

## Environnement : hébergé ou local

Les deux MCP existent en **connecteurs hébergés** pour l'équipe, nommés **Péri Slides MCP** (outils Slides : `clone_deck`, `insert_component`…) et **Péri Sheets MCP** (outils Sheets : `read_range`, `manage_chart`…), chacun connecté avec son compte Google @periscope.digital, et en **serveurs locaux** chez qui les a installés. Les outils portent les mêmes noms en local et en hébergé ; quelques différences en hébergé :

- **Pas de fichier local.** Le serveur ne voit pas le disque de l'utilisateur : une prop image (`icon`, `logo`, `photo`, `image`, l'`asset` de `draw`) prend un nom du dossier d'assets (`list_assets()`) ou `drive:<id>` d'un fichier Drive, jamais un chemin. Pour une image que l'utilisateur a sur son poste : il la dépose dans le dossier d'assets ou dans son Drive, ou `insert_image_local` avec `image_base64`. `export_pres` renvoie un lien de téléchargement, pas un fichier.
- **Catalogue en lecture seule.** `save_component` et `delete_component` n'existent pas en hébergé, et aucun outil ne modifie le thème `periscope` : le catalogue et la charte évoluent en local, par la personne qui maintient le MCP. Côté Sheets, les outils de suppression (`clear_values`, `delete_sheet`, `delete_dimensions`…) sont désactivés : un outil absent est voulu, on ne le contourne pas.
- **Appels en file.** Le serveur sert un nombre limité d'appels à la fois pour toute l'équipe : un appel lent attend son tour, ce n'est pas une panne. Ne pas lancer vingt captures en parallèle.
- **Outils Sheets absents** (Péri Sheets MCP non ajouté ou non connecté) : les graphiques se font en version dessinée, et on le dit dans le plan (« natif Sheets impossible ici : ajoute Péri Sheets MCP dans tes connecteurs pour des graphiques reliés »). Même logique si Péri Slides MCP manque : rien ne se construit, on demande de l'ajouter. Tableaux : `rows` écrites à la main depuis les chiffres fournis.

## 0. Cadrage (un seul message, trois blocs)

Si l'URL manque, la demander. Puis, en lecture seule sur le deck type : `list_layouts` et `screenshot_layouts` (planche captionnée). Poser en un message :

1. **La prez** : client, objectif (AO, reco, bilan…), audience, nombre de slides, messages clés, matière disponible (brief, données, docs : les lire). **Les chiffres sont-ils dans un classeur ?** Si oui, son URL, et s'il faut écrire dedans ou dans un classeur à part (par défaut : on lit le sien, on écrit dans un classeur nommé comme le deck). Pour un bilan récurrent, proposer d'office le natif Sheets.
2. **Le layout des slides de titre / section** et **le layout des slides de contenu** : montrer la planche, proposer un défaut par nom exact tel que renvoyé par `list_layouts` (titre : le layout de couverture ou de section ; contenu : celui qui a un `TITLE` et de la place libre, souvent le plus `used_by_slides`). Les noms sont propres à chaque deck (« Hero », « Texte_Basique04 », « Title_dark + subtitle »…) : ne jamais les deviner.
3. Les réutilisations Periscope pertinentes (voir `periscope.md`) à proposer d'office pour un AO ou une reco.

Si un classeur est donné : `get_spreadsheet` (titres exacts des feuilles) et `read_range` sur les plages utiles **avant** le plan, pour que le plan cite de vrais chiffres. Attendre la réponse. Les deux noms de layouts retenus sont écrits en tête du plan.

## 1. Plan des slides

Appeler `list_assets()` pour connaître les pictos, logos et photos disponibles (noms sans extension : `bolt`, `people`, `screen-demo`…) avant de proposer un `icon`, un `logo` ou une `photo`. Puis appeler `list_components()` **une fois, avant d'écrire le plan** : c'est le seul endroit où sont les noms de props, les exemples et le champ `use` (quand l'utiliser, alternatives proches). Choisir chaque composant d'après `use`, pas d'après son nom : `compare_cards` oppose ✗/✓, `team_grid` montre des personnes, des agences partenaires vont dans `logo_grid`. Chaque entrée porte aussi des **`variants`** : d'autres réglages prêts du même composant, avec `title` (à quoi ça ressemble), `when` (la situation) et `props` (l'appel à copier). Lire les `when` avant de choisir : une `table` a sa variante simple, pictos de canaux, « vs N-1 » et pilules par seuil ; une `card` ses fonds mint / outline / acid / plain ; un `chart_bars` sa version horizontale et sa version « mensuel avec séparateur de période ». Le catalogue visuel (une slide par composant puis une par variante) est le deck `1cPrerkVnlbxs5QtKjlILoBDO-MczFd-WViffUEUfi1E` : y renvoyer l'utilisateur quand il hésite entre deux rendus.

**Graphiques : dessiné ou natif Sheets.** Les composants `chart_*`, `donut`, `pie` dessinent le graphique dans Slides à partir des `props` : rapide, charte garantie, pourcentages sur les parts, mais figé. Leur variante « natif Sheets, relié » (bloc `native` de la variante) construit le même graphique dans un Google Sheets avec **Péri Sheets MCP** et l'embarque relié avec `insert_sheets_chart`. Choisir ainsi :

| Situation | Choix |
|---|---|
| Chiffres déjà dans un classeur, deck récurrent (bilan mensuel), utilisateur qui veut retoucher les données | **natif Sheets** : on change les cellules, `refresh_sheets_charts` met les slides à jour |
| Parts d'un camembert à lire en % sur le graphique | **dessiné** (`donut` / `pie`) : l'API Sheets ne sait pas afficher les % sur les parts |
| Chiffres ponctuels d'un brief, AO, pas de classeur | **dessiné** |
| Péri Sheets MCP absent | **dessiné**, et le dire |

Dans le plan, dire pour chaque graphique lequel des deux et pourquoi ; en natif, indiquer le classeur (celui de l'utilisateur, ou un nouveau nommé comme le deck) et la feuille. **Tableaux** : il n'existe pas de tableau relié dans Slides ; un tableau « depuis le classeur » est lu avec `read_range` puis inséré avec le composant `table`, et se réinsère à chaque mise à jour.

Plan numéroté : par slide → titre, objectif, **layout** (titre / contenu / autre layout du deck si un format spécial s'impose, par son nom exact), **composant(s)**, source des chiffres (brief, classeur + plage) et contenu résumé. Un message par slide, ~5 puces max. Itérer jusqu'à validation.

## 2. Rédaction

Contenu définitif slide par slide : titres, textes markdown des placeholders, props des composants **copiées sur la structure de `example` du catalogue ou de la variante retenue** (`variants[k].props` : mêmes clés : `cards`, `items`, `people`, `phases`…, jamais de clé de mémoire). Dans une `table`, les colonnes de la période précédente (« Clics N-1 », « P-1 ») et de variation (« vs N-1 », « Évol. ») sont reconnues sur l'en-tête : nommer les colonnes ainsi suffit, pas de `delta_cols` à calculer. Pour un graphique natif, rédiger aussi les **données du classeur** (une ligne d'en-tête, catégories en première colonne, une série par colonne, formules bienvenues pour les totaux et les variations) : c'est ce que Péri Sheets MCP écrira. Chiffres au format français `12 400`, `+8 %` ; message clé en `==surligné==`. Jamais de tiret cadratin « — » : utiliser « : » ou une virgule. Validation.

## 3. Construction sur la copie vide

1. Création : `clone_deck(src, name="<Client> · <objet> · <AAAA-MM>")` → id `P`, puis `list_slides(P)` : noter les ids **de toutes les slides d'origine**. Reprise : `P` = l'URL donnée ; `list_slides(P)` ; les slides à supprimer sont seulement celles que l'utilisateur a nommées (slides d'exemple, slides à refaire).
2. Pour chaque layout retenu qui a plus d'un placeholder : `screenshot_layout(P, layout, annotate=True)` **sur la copie** (l'annotation crée puis supprime une slide temporaire : c'est une écriture). Lire la carte des clés (`TITLE[1]`, `SUBTITLE[0]`…) avant d'écrire le moindre `fills`.
3. `build_from_outline(P, outline=[{layout, fills}, …])` : une seule écriture, tout est résolu avant. Sur une slide à composant ou à graphique, remplir le titre et laisser les autres placeholders vides.
4. `delete_slides(P, <ids à retirer>)` : en création, toutes les slides d'origine, pour que la copie ne contienne que nos slides (l'API accepte 0 slide, mais créer avant de supprimer) ; en reprise, uniquement celles demandées. Vérifier avec `list_slides(P)`. Pour insérer au milieu d'un deck existant : `insertion_index` (0-based) de `build_from_outline`, ou `move_slide` ensuite.
5. Composants, slide par slide : `get_page(P, slide, compact=True)` pour la géométrie du titre et des placeholders vides ; `insert_component` sous le titre (x = gauche du titre, y = bas du titre + 20 pt, width = largeur du titre ou de la zone libre). `list_layouts` donne aussi `content_area` par layout (la zone libre sous le titre, au-dessus du pied de page) : un bon défaut, à croiser avec `get_page` d'une slide réelle puisque la géométrie du layout peut différer de celle des slides. Chaîner avec le `height_pt` renvoyé. Supprimer les placeholders restés vides (`delete_elements`) pour éviter les « Cliquez pour ajouter ». Sur fond sombre : `dark: true` ou variant `dark`.
6. **Graphiques natifs Sheets** (Péri Sheets MCP d'abord, Péri Slides MCP ensuite) :
   1. Classeur : celui que l'utilisateur désigne (URL) s'il a accepté qu'on y écrive, sinon `create_spreadsheet` nommé comme le deck, avec une feuille par graphique (`sheets: ["bars", "donut", …]`). Toujours `get_spreadsheet` pour les titres exacts des feuilles : jamais « Sheet1 » ni « Feuille 1 » supposés.
   2. `set_theme` une fois par classeur : `preset: "periscope"` (Barlow, couleurs charte) ou `preset: "periscope_regies"` quand les camemberts sont par régie (accent2 Google, accent3 Meta, accent4 Bing, accent5 Instagram, accent6 GA4). Camemberts et donuts prennent les accents **à partir d'accent2 dans l'ordre des lignes** : écrire les lignes dans l'ordre Google, Meta, Bing, Instagram, GA4. Une régie absente décale les couleurs des suivantes : pour un autre ordre ou une liste incomplète, passer `colors: {accent2: …, accent3: …}` en plus du preset, dans l'ordre des lignes. Un seul thème par classeur, donc un seul ordre pour tous ses camemberts.
   3. `write_values` des données (`input: "typed"` pour que les nombres et les dates soient compris comme si on les tapait ; le serveur refuse d'écraser des cellules non vides sans `overwrite` : lire le refus, ne pas forcer à l'aveugle), puis `format_cells` avec `number_format: "number:#,##0"` (ou `currency:#,##0" €"`) sur les colonnes de valeurs : les étiquettes et l'axe du graphique suivent le format des cellules.
   4. `manage_chart(action: "add", style: "periscope", headers: 1, …)` avec les arguments du bloc `native.sheets.manage_chart` de la variante (type, `domain`, `series` en liste, `series_colors` ou `point_colors` par régie, `data_labels`, `legend: top`, `stacked`, `series_types` + `series_axes` pour un combo, `pie_hole: 0.55` et `legend: right` pour un donut, `width`/`height` 400 × 400 pour un camembert). Noter le `chart_id` renvoyé.
   5. `screenshot_chart(spreadsheet, id)` : regarder le graphique **avant** de l'embarquer (couleurs, étiquettes, légende, format des nombres). Corriger avec `manage_chart(action: "update")` tant qu'il n'est pas propre ; c'est moins cher que de corriger après coup dans la slide.
   6. Côté Slides : `insert_sheets_chart(P, slide, spreadsheet, chart_id, x_pt, y_pt, width_pt, height_pt)` dans la zone libre ; Google garde les proportions du graphique (600 × 371 px, ratio 1,6 ; 1 pour un camembert) et le recentre dans la boîte : donner à la boîte le même ratio. `list_sheets_charts` pour retrouver les liens, `refresh_sheets_charts(P)` après toute modification du classeur, `transform_element` pour bouger ou redimensionner (le lien tient).
   7. Tableau depuis un classeur : `read_range(formatted: true, format: "json")` puis `insert_component(P, slide, "table", {rows: <lignes lues>, header_fill: "ink", total_row: true, …})` ; pour actualiser, `delete_elements` sur la table puis réinsérer à la même place.
7. **Mise à jour d'un bilan récurrent** (reprise) : `list_sheets_charts(P)` pour les liens, écrire les nouvelles valeurs dans le classeur (`write_values` avec `overwrite` sur les cellules de la période, après les avoir lues), `screenshot_chart` sur un graphique pour vérifier, `refresh_sheets_charts(P)`, puis réinsérer les tableaux et mettre à jour les textes qui citent des chiffres (titres, `==surligné==`, cartes KPI) : un graphique relié se met à jour seul, le texte non.
8. Notes orateur si demandées : `set_speaker_notes`.

Quota : 60 écritures par minute et par utilisateur, côté Slides comme côté Sheets. Une erreur 429 se réessaie après une minute, elle ne se contourne pas.

## 4. Contrôle visuel (obligatoire avant de livrer)

`screenshot_range` sur toutes les slides, puis `overlap_check`. Regarder chaque capture : texte coupé ou débordant, composant qui chevauche un décor du layout (tubes, logo, bandeau), placeholder vide visible, couleurs illisibles, graphique relié mal cadré (bandes vides : ratio de la boîte), chiffres du texte différents de ceux du graphique. Corriger (`transform_element`, largeur, props, `delete_elements`), recapturer, jusqu'à propre. L'absence d'erreur API ne dit rien du rendu.

Livrer : URL de la copie + liste numérotée des slides + URL du classeur s'il y en a un (« les graphiques des slides 4, 6 et 7 sont reliés à ce classeur : modifier les cellules puis Actualiser dans Slides »). Le deck type n'a pas bougé.

## 5. Retour d'expérience (fin de run)

Après la livraison, un bloc « Améliorations du skill » : ce qui a coincé (erreur d'outil, composant manquant ou mal rendu, layout piège, question de cadrage manquante, option de graphique absente côté Sheets) et une proposition concrète pour chacun : ligne à ajouter aux pièges de `SKILL.md`, matière à ajouter à `periscope.md`, recette de composant à faire entrer au catalogue, correction côté MCP. Une recette se propose en JSON dans la réponse, pour la personne qui maintient le MCP : en hébergé, `save_component` n'existe pas, et en local on ne l'enregistre qu'avec son accord explicite, après `list_components` pour ne pas écraser une recette existante. Attendre l'accord avant de modifier quoi que ce soit.

## Refonte d'un deck existant (mode 3)

Cadrage comme en création (deck type, layouts titre / contenu), plus le deck **source** en lecture seule. Puis :

1. **Mettre les visuels de côté** : demander à l'utilisateur où (un dossier Drive existant, id ou URL, ou laisser l'outil créer « *<titre>* · sources » dans le dossier d'assets), puis `harvest_deck_assets(source, folder=…)`. Les images reviennent avec une `url` stable et une référence `asset: "drive:<id>"` acceptée par toutes les props image (`browser`, `gallery`, `card.icon`, `logo_wall`…) ; une capture de chaque slide source est rangée au même endroit. Les fichiers moissonnés sont partagés en lecture à qui a le lien : pour des visuels client confidentiels, préférer un dossier dédié au client plutôt que le dossier d'assets commun. Les URL d'images de l'API expirent en trente minutes : cette étape vient en premier.
2. **Lire chaque slide source** : `inspect_slide(source, n)` donne le type de placeholder, les paragraphes avec leurs puces, les cellules des tableaux (`rows`, à passer telles quelles à `table`) et les images.
3. **Choisir les composants par bloc** : `suggest_components(source, n)` découpe la slide en blocs (tableau, rangée de chiffres, blocs côte à côte, liste, image, note de source…) avec des candidats classés, la raison, le `use` et les variantes ; `slide_level` propose des alternatives lues dans le vocabulaire (« avant / après » → `before_after`, « équipe » → `team_grid`, « objectifs » → `media_plan`). Ce sont des heuristiques : le titre va dans le placeholder du layout, une slide donne souvent **plusieurs** composants, et un bloc peut mériter un composant qui n'est pas listé. Un graphique source (image d'un export Excel, graphique Sheets) se refait en dessiné ou en natif selon le tableau de l'étape 1 ; ses chiffres se relisent sur la source ou se demandent, ils ne se devinent pas sur l'image. Le plan (étape 1) liste, par slide source, la slide cible, son layout et ses composants.
4. Rédaction, construction et contrôle comme en 2 → 4 : `create_slide_from_layout` ou `build_from_outline`, le titre en placeholder, les composants dans `content_area` en gardant les proportions des `zone` des blocs sources, les visuels par leur `asset` moissonné. Les slides masquées du source (`hidden`) se signalent et s'ignorent sauf accord.

## Rationalisations à refuser

| Excuse | Réalité |
|---|---|
| « Pas le temps de valider, je construis direct » | Le plan tient en 10 lignes. Reconstruire 8 slides à côté coûte plus qu'une réponse. |
| « J'écris sur le template, je nettoierai après » | Le template n'est jamais modifié. `clone_deck` d'abord, sauf copie désignée par l'utilisateur. |
| « Il dit que c'est une copie, mais par sécurité je reclone » | Non : une copie désignée est la copie de travail. Recloner crée un deck orphelin et ignore la demande. |
| « Je garde les slides du template dans la copie, l'utilisateur triera » | La copie ne contient que les slides créées. `delete_slides` des ids d'origine. |
| « Les layouts s'appellent Titre et Contenu » | Chaque deck a ses noms. `list_layouts`, et l'utilisateur choisit. |
| « Je mets des chiffres plausibles » | `[À CONFIRMER]`. Un chiffre inventé dans un AO est une faute. |
| « Pas d'erreur API, donc c'est bon » | `screenshot_range` et regarder ; `screenshot_chart` pour un graphique natif. |
| « Je connais les composants, pas besoin de `list_components` » | Les props et le champ `use` ne sont que là. Un appel, avant le plan. |
| « Les clés du layout sont sûrement TITLE[0] et SUBTITLE[0] » | L'ordre des placeholders n'est pas l'ordre visuel. `annotate=True` sur la copie. |
| « À partir de ce Google Slides » = « retouche une copie » | Non : nouveau contenu sur les layouts du type. Si doute, demander. |
| « J'exporte aussi un PDF, ça peut servir » | Rien qui n'ait été demandé. |
| « La slide masquée a les chiffres que je cherche » | Masquée = écartée, souvent fausse. Demander avant de s'en servir. |
| « J'écris directement dans son classeur, c'est plus simple » | Seulement s'il l'a dit. Sinon on lit le sien et on écrit dans un classeur nommé comme le deck. |
| « Le refus d'écraser bloque, je passe `overwrite` partout » | Le refus nomme les cellules : les lire, vérifier que ce sont bien celles de la période, puis écraser celles-là. |
| « Le graphique est relié, les chiffres du texte suivront » | Non : titres, cartes KPI et surlignés sont du texte. Les mettre à jour à la main. |
| « Il manque un outil de suppression / `save_component`, je contourne avec `raw_request` » | Absent en hébergé, c'est voulu. Le dire à l'utilisateur. |
| « Je lui donne le chemin de mon fichier local » | En hébergé, pas de disque partagé : dossier d'assets, `drive:<id>` ou `image_base64`. |

## Pièges connus

- Les clés de placeholders (`SUBTITLE[3]`) suivent l'ordre des éléments du layout, pas l'ordre visuel : `screenshot_layout(P, layout, annotate=True)` sur la copie avant d'écrire des `fills` sur un layout à plusieurs placeholders. Sans `annotate`, `screenshot_layout` et `screenshot_layouts` sont en lecture seule et peuvent viser le deck type.
- Layouts homonymes (decks fusionnés) : l'appel échoue en listant les candidats ; passer `layout_id`.
- Pas de composant sur un layout à décor plein (couverture, intercalaire) sauf demande.
- Pictos du dossier assets : blancs sur transparent ; `card.icon` se teinte seul, `logo_grid` / `logo_wall` demandent `tint: "ink"` sur fond clair. La liste est dans `list_assets()`, pas dans le catalogue des composants. Un asset absent se dépose dans le dossier d'assets Drive (partagé avec le domaine), il ne s'invente pas.
- Tailles de texte : le thème impose 11 pt minimum aux textes et 10 pt aux libellés, sur-titres, légendes et badges (tableaux exemptés). Un `size` plus petit est relevé au rendu ; ne pas chercher à passer dessous, réduire le texte à la place.
- Un composant retourne `height_pt` : l'utiliser pour empiler, ne pas estimer.
- Un placeholder vide est invisible en présentation mais visible en édition : le supprimer.
- Slides masquées (`hidden: true` dans `list_slides` / `inspect_slide`) : elles ne sont pas présentées et sont souvent une version périmée, avec des chiffres faux. Ne jamais s'en inspirer ni les copier sans l'accord de l'utilisateur ; en reprise, les signaler dans le cadrage (« la slide 19 est masquée, je l'ignore ? »). `set_slide_hidden` masque ou réaffiche.
- Format de page : lire `get_presentation(P, fields="pageSize")` (templates Periscope : 960 × 540 pt) avant de positionner à la main.
- Deck à beaucoup de layouts (80 et plus) : `list_layouts` dépasse la taille de sortie et `screenshot_layouts` sans filtre épuise le quota de 60 lectures par minute. Lire le fichier de sortie de `list_layouts` avec un script (nom, id, placeholders, `used_by_slides`), puis appeler `screenshot_layouts` avec une liste de 6 à 8 noms : les layouts en usage dans le deck et les candidats titre / contenu.
- `build_from_outline` crée aussi les placeholders laissés sans `fills`, avec des ids Google aléatoires (`SLIDES_API…`). Avant `delete_elements`, un `get_page(P, slide, compact=True)` par slide pour récupérer ces ids ; les placeholders remplis, eux, portent des ids prévisibles (`<slide_id>_subtitle0`).
- La géométrie du layout n'est pas celle des slides réelles : sur `Texte_Basique04`, le titre fait 272 pt de large dans le layout et 800 pt sur les slides du deck. Avant de remplir, comparer `get_page` d'une slide existante du même layout avec celle du layout. Pour redimensionner, `transform_element(width_pt=…)` ou `height_pt` (une seule dimension garde les proportions, les deux fixent le cadre) ; il déplace aussi (`x_pt` / `y_pt` ou `dx_pt` / `dy_pt`).
- Graphiques natifs Sheets, appris en construisant le catalogue : `series` est toujours une liste, même pour une série ; sur un combo, `line_width` / `line_dash` se donnent par série avec `0` pour la série colonne (Google refuse un style de ligne sur une colonne) ; `pie_labels` (légende sur les parts) ne s'affiche pas une fois embarqué dans Slides, prendre `legend: right` ; les pourcentages sur les parts n'existent pas dans l'API (réglage manuel dans l'éditeur Sheets, effacé par tout `manage_chart update`) : garder le `donut` dessiné quand les parts doivent se lire ; les couleurs des parts viennent du thème (accent2…), pas d'une couleur par part ; sans `format_cells` sur les colonnes de valeurs, les étiquettes sortent sans séparateur de milliers.
- Graphique relié et droits : chacun voit l'image embarquée, mais **Actualiser** (dans Slides ou par `refresh_sheets_charts`) demande l'accès au classeur. Partager le classeur avec les mêmes personnes que le deck ; un graphique d'un classeur supprimé ou non partagé reste figé sur sa dernière image.
- Noms de feuilles : un classeur créé sur un compte en français s'appelle « Feuille 1 », pas « Sheet1 ». Les titres viennent de `get_spreadsheet`, toujours.
- Un deck source à moissonner peut contenir des images minuscules (puces, pictos) : `harvest_deck_assets` les saute (`min_pt`) et les liste dans `skipped` ; ce qui n'est pas une image (vidéos, formes libres, WordArt) n'est pas moissonné, `inspect_slide` le signale.

## Référence rapide

| Étape | Outils |
|---|---|
| Cadrage (lecture seule) | `list_layouts`, `screenshot_layouts`, `list_assets`, `list_components` (champ `use`, props, `example`), `list_slides`, `list_sheets_charts`, `screenshot_range` sur le type pour s'inspirer · Sheets : `get_spreadsheet`, `read_range`, `find_in_spreadsheet` |
| Construction (copie) | `clone_deck`, `screenshot_layout(annotate=True)`, `build_from_outline`, `create_slide_from_layout`, `delete_slides`, `get_page(compact)`, `insert_component`, `draw`, `delete_elements`, `write_text_markdown`, `set_speaker_notes` |
| Graphiques natifs (Péri Sheets MCP puis Péri Slides MCP) | `create_spreadsheet`, `get_spreadsheet`, `set_theme` (`periscope` / `periscope_regies`), `write_values`, `format_cells`, `manage_chart`, `screenshot_chart`, `read_range` · `insert_sheets_chart`, `list_sheets_charts`, `refresh_sheets_charts`, `transform_element` |
| Refonte (source en lecture seule) | `harvest_deck_assets`, `inspect_slide`, `suggest_components`, `list_layouts` (`content_area`), puis la construction |
| Contrôle | `screenshot_range`, `screenshot`, `overlap_check`, `screenshot_chart`, `transform_element`, `inspect_slide` |
| Capitalisation | recette JSON proposée au mainteneur (`save_component` en local seulement), `periscope.md`, pièges de ce fichier |
