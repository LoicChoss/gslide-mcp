---
name: gslides-prez
description: Utiliser dès que l'utilisateur veut produire une présentation Google Slides (reco, AO, bilan, audit, prez client) à partir d'un Google Slides type ou template, avec le MCP gslides-mcp, ou modifier un deck déjà copié ou déjà produit ainsi (« j'ai déjà copié, tu peux modifier »). Aussi quand il donne une URL docs.google.com/presentation et parle de « faire une prez », « des slides », « un deck ».
---

# Présentation Google Slides depuis un deck type (MCP gslides-mcp)

Le deck type porte la charte (masters, layouts, décors). On construit **sur une copie vidée** de ce deck, avec ses layouts et les composants chartés du MCP.

**Trois règles absolues**

1. **Le deck type est en lecture seule.** Aucun outil d'écriture ne reçoit son id : ni `build_from_outline`, ni `insert_component`, ni `delete_slides`, ni `set_*`. Tout se fait sur une **copie de travail** : celle que crée `clone_deck`, ou celle que l'utilisateur désigne lui-même (« j'ai déjà copié, tu peux modifier », « c'est une copie de mon template, écris dedans »). Dans ce cas on travaille dedans sans recloner ; on le redit en une ligne dans le premier message, et l'URL donnée est la copie, pas le type.
2. **Étapes gated** : validation explicite de l'utilisateur avant l'étape suivante. La pression (« call dans 40 min », « pas de questions ») raccourcit les messages, pas les étapes : un plan de 8 slides tient en 10 lignes et se valide en une réponse.
3. **On n'invente pas la matière.** Chiffres, faits client, résultats, dates et périodes : ils viennent du brief, des documents lus ou de `periscope.md`. À défaut, la valeur est écrite `[À CONFIRMER]`, jamais plausible-et-fausse.

Violer la lettre de ces règles, c'est violer leur esprit.

**Deux modes.** *Création* : URL d'un deck type → tout le parcours 0 → 5. *Reprise* : l'utilisateur donne un deck déjà copié ou déjà produit avec ce skill et demande une modification (ajouter, refaire, corriger des slides) → pas de clone, cadrage réduit à ce qui manque (les layouts se lisent dans le deck : `list_slides` + `list_layouts`, les slides existantes disent lesquels sont en usage), plan limité aux slides touchées, puis 2 → 5. Les slides qu'on n'a pas à toucher ne bougent pas.

## 0. Cadrage (un seul message, trois blocs)

Si l'URL manque, la demander. Puis, en lecture seule sur le deck type : `list_layouts` et `screenshot_layouts` (planche captionnée). Poser en un message :

1. **La prez** : client, objectif (AO, reco, bilan…), audience, nombre de slides, messages clés, matière disponible (brief, données, docs : les lire).
2. **Le layout des slides de titre / section** et **le layout des slides de contenu** : montrer la planche, proposer un défaut par nom exact tel que renvoyé par `list_layouts` (titre : le layout de couverture ou de section ; contenu : celui qui a un `TITLE` et de la place libre, souvent le plus `used_by_slides`). Les noms sont propres à chaque deck (« Hero », « Texte_Basique04 », « Title_dark + subtitle »…) : ne jamais les deviner.
3. Les réutilisations Periscope pertinentes (voir `periscope.md`) à proposer d'office pour un AO ou une reco.

Attendre la réponse. Les deux noms de layouts retenus sont écrits en tête du plan.

## 1. Plan des slides

Appeler `list_assets()` pour connaître les pictos, logos et photos disponibles (noms sans extension : `bolt`, `people`, `screen-demo`…) avant de proposer un `icon`, un `logo` ou une `photo` ; un fichier local passé à ces props est uploadé dans le dossier. Puis appeler `list_components()` **une fois, avant d'écrire le plan** : c'est le seul endroit où sont les noms de props, les exemples et le champ `use` (quand l'utiliser, alternatives proches). Choisir chaque composant d'après `use`, pas d'après son nom : `compare_cards` oppose ✗/✓, `team_grid` montre des personnes, des agences partenaires vont dans `logo_grid`.

Plan numéroté : par slide → titre, objectif, **layout** (titre / contenu / autre layout du deck si un format spécial s'impose, par son nom exact), **composant(s)** et contenu résumé. Un message par slide, ~5 puces max. Itérer jusqu'à validation.

## 2. Rédaction

Contenu définitif slide par slide : titres, textes markdown des placeholders, props des composants **copiées sur la structure de `example` du catalogue** (mêmes clés : `cards`, `items`, `people`, `phases`…, jamais de clé de mémoire). Chiffres au format français `12 400`, `+8 %` ; message clé en `==surligné==`. Jamais de tiret cadratin « — » : utiliser « : » ou une virgule. Validation.

## 3. Construction sur la copie vide

1. Création : `clone_deck(src, name="<Client> · <objet> · <AAAA-MM>")` → id `P`, puis `list_slides(P)` : noter les ids **de toutes les slides d'origine**. Reprise : `P` = l'URL donnée ; `list_slides(P)` ; les slides à supprimer sont seulement celles que l'utilisateur a nommées (slides d'exemple, slides à refaire).
2. Pour chaque layout retenu qui a plus d'un placeholder : `screenshot_layout(P, layout, annotate=True)` **sur la copie** (l'annotation crée puis supprime une slide temporaire : c'est une écriture). Lire la carte des clés (`TITLE[1]`, `SUBTITLE[0]`…) avant d'écrire le moindre `fills`.
3. `build_from_outline(P, outline=[{layout, fills}, …])` : une seule écriture, tout est résolu avant. Sur une slide à composant, remplir le titre et laisser les autres placeholders vides.
4. `delete_slides(P, <ids à retirer>)` : en création, toutes les slides d'origine, pour que la copie ne contienne que nos slides (l'API accepte 0 slide, mais créer avant de supprimer) ; en reprise, uniquement celles demandées. Vérifier avec `list_slides(P)`. Pour insérer au milieu d'un deck existant : `insertion_index` (0-based) de `build_from_outline`, ou `move_slide` ensuite.
5. Composants, slide par slide : `get_page(P, slide, compact=True)` pour la géométrie du titre et des placeholders vides ; `insert_component` sous le titre (x = gauche du titre, y = bas du titre + 20 pt, width = largeur du titre ou de la zone libre). Chaîner avec le `height_pt` renvoyé. Supprimer les placeholders restés vides (`delete_elements`) pour éviter les « Cliquez pour ajouter ». Sur fond sombre : `dark: true` ou variant `dark`.
6. Notes orateur si demandées : `set_speaker_notes`.

Quota : 60 écritures par minute et par utilisateur. Une erreur 429 se réessaie après une minute, elle ne se contourne pas.

## 4. Contrôle visuel (obligatoire avant de livrer)

`screenshot_range` sur toutes les slides, puis `overlap_check`. Regarder chaque capture : texte coupé ou débordant, composant qui chevauche un décor du layout (tubes, logo, bandeau), placeholder vide visible, couleurs illisibles. Corriger (`transform_element`, largeur, props, `delete_elements`), recapturer, jusqu'à propre. L'absence d'erreur API ne dit rien du rendu.

Livrer : URL de la copie + liste numérotée des slides. Le deck type n'a pas bougé.

## 5. Retour d'expérience (fin de run)

Après la livraison, un bloc « Améliorations du skill » : ce qui a coincé (erreur d'outil, composant manquant ou mal rendu, layout piège, question de cadrage manquante) et une proposition concrète pour chacun : ligne à ajouter aux pièges de `SKILL.md`, matière à ajouter à `periscope.md`, recette à figer avec `save_component`, correction côté MCP. Attendre l'accord avant de modifier quoi que ce soit.

## Rationalisations à refuser

| Excuse | Réalité |
|---|---|
| « Pas le temps de valider, je construis direct » | Le plan tient en 10 lignes. Reconstruire 8 slides à côté coûte plus qu'une réponse. |
| « J'écris sur le template, je nettoierai après » | Le template n'est jamais modifié. `clone_deck` d'abord, sauf copie désignée par l'utilisateur. |
| « Il dit que c'est une copie, mais par sécurité je reclone » | Non : une copie désignée est la copie de travail. Recloner crée un deck orphelin et ignore la demande. |
| « Je garde les slides du template dans la copie, l'utilisateur triera » | La copie ne contient que les slides créées. `delete_slides` des ids d'origine. |
| « Les layouts s'appellent Titre et Contenu » | Chaque deck a ses noms. `list_layouts`, et l'utilisateur choisit. |
| « Je mets des chiffres plausibles » | `[À CONFIRMER]`. Un chiffre inventé dans un AO est une faute. |
| « Pas d'erreur API, donc c'est bon » | `screenshot_range` et regarder. |
| « Je connais les composants, pas besoin de `list_components` » | Les props et le champ `use` ne sont que là. Un appel, avant le plan. |
| « Les clés du layout sont sûrement TITLE[0] et SUBTITLE[0] » | L'ordre des placeholders n'est pas l'ordre visuel. `annotate=True` sur la copie. |
| « À partir de ce Google Slides » = « retouche une copie » | Non : nouveau contenu sur les layouts du type. Si doute, demander. |
| « J'exporte aussi un PDF, ça peut servir » | Rien qui n'ait été demandé. |
| « La slide masquée a les chiffres que je cherche » | Masquée = écartée, souvent fausse. Demander avant de s'en servir. |

## Pièges connus

- Les clés de placeholders (`SUBTITLE[3]`) suivent l'ordre des éléments du layout, pas l'ordre visuel : `screenshot_layout(P, layout, annotate=True)` sur la copie avant d'écrire des `fills` sur un layout à plusieurs placeholders. Sans `annotate`, `screenshot_layout` et `screenshot_layouts` sont en lecture seule et peuvent viser le deck type.
- Layouts homonymes (decks fusionnés) : l'appel échoue en listant les candidats ; passer `layout_id`.
- Pas de composant sur un layout à décor plein (couverture, intercalaire) sauf demande.
- Pictos du dossier assets : blancs sur transparent ; `card.icon` se teinte seul, `logo_grid` / `logo_wall` demandent `tint: "ink"` sur fond clair. La liste est dans `list_assets()`, pas dans le catalogue des composants.
- Tailles de texte : le thème impose 11 pt minimum aux textes et 10 pt aux libellés, sur-titres, légendes et badges (tableaux exemptés). Un `size` plus petit est relevé au rendu ; ne pas chercher à passer dessous, réduire le texte à la place.
- Un composant retourne `height_pt` : l'utiliser pour empiler, ne pas estimer.
- Un placeholder vide est invisible en présentation mais visible en édition : le supprimer.
- Slides masquées (`hidden: true` dans `list_slides` / `inspect_slide`) : elles ne sont pas présentées et sont souvent une version périmée, avec des chiffres faux. Ne jamais s'en inspirer ni les copier sans l'accord de l'utilisateur ; en reprise, les signaler dans le cadrage (« la slide 19 est masquée, je l'ignore ? »). `set_slide_hidden` masque ou réaffiche.
- Format de page : lire `get_presentation(P, fields="pageSize")` (templates Periscope : 960 × 540 pt) avant de positionner à la main.
- Deck à beaucoup de layouts (80 et plus) : `list_layouts` dépasse la taille de sortie et `screenshot_layouts` sans filtre épuise le quota de 60 lectures par minute. Lire le fichier de sortie de `list_layouts` avec un script (nom, id, placeholders, `used_by_slides`), puis appeler `screenshot_layouts` avec une liste de 6 à 8 noms : les layouts en usage dans le deck et les candidats titre / contenu.
- `build_from_outline` crée aussi les placeholders laissés sans `fills`, avec des ids Google aléatoires (`SLIDES_API…`). Avant `delete_elements`, un `get_page(P, slide, compact=True)` par slide pour récupérer ces ids ; les placeholders remplis, eux, portent des ids prévisibles (`<slide_id>_subtitle0`).
- La géométrie du layout n'est pas celle des slides réelles : sur `Texte_Basique04`, le titre fait 272 pt de large dans le layout et 800 pt sur les slides du deck. Avant de remplir, comparer `get_page` d'une slide existante du même layout avec celle du layout. Pour redimensionner, `transform_element` ne fait que déplacer : passer par `batch_apply` avec `updatePageElementTransform` (`applyMode: ABSOLUTE`, `scaleX = largeur_pt / 236.22` quand la taille de base est 3 000 000 EMU, lire `size` et `transform` avec `raw_request`).
- `numbered_list` sans `icon` : le marqueur `circle` affiche le numéro dans le disque et un « #1 » à côté, en double. Utiliser `marker: "square"` tant que ce n'est pas corrigé côté MCP.

## Référence rapide

| Étape | Outils |
|---|---|
| Cadrage (lecture seule) | `list_layouts`, `screenshot_layouts`, `list_assets`, `list_components` (champ `use`, props, `example`), `list_slides`, `screenshot_range` sur le type pour s'inspirer |
| Construction (copie) | `clone_deck`, `screenshot_layout(annotate=True)`, `build_from_outline`, `create_slide_from_layout`, `delete_slides`, `get_page(compact)`, `insert_component`, `draw`, `delete_elements`, `write_text_markdown`, `set_speaker_notes` |
| Contrôle | `screenshot_range`, `screenshot`, `overlap_check`, `transform_element`, `inspect_slide` |
| Capitalisation | `save_component`, `periscope.md`, pièges de ce fichier |
