# Matière Periscope réutilisable

À proposer d'office dans le plan quand la prez est un AO, une reco ou une présentation d'agence. Reprendre le fond, adapter la forme au client ; ne pas paraphraser en affaiblissant. Composants suggérés entre parenthèses.

## Notre philosophie média (2 slides, `numbered_list` ou `big_numbers`)

Slide 1 · Notre philosophie média (1/2)

1. **On répare la maison avant de vendre du média.** SEO, UX, data, formulaires, téléphone d'abord, même si ça ralentit notre propre facturation.
2. **La techno et l'IA nous rendent plus présents auprès de vous, pas moins.** Le temps gagné sur le reporting revient à l'optimisation et au conseil.
3. **Notre pôle marketing digital existe depuis 2001.** Un quart de siècle d'expertise dédiée, pas une compétence ajoutée en cours de route.
4. **Nous sommes parmi les premières agences à intégrer le programme Ads de ChatGPT.** Anticiper la diversification des leviers d'acquisition, avant qu'elle devienne une évidence pour tous.

Slide 2 · Notre philosophie média (2/2)

5. **On assume nos propres angles morts plutôt que de les cacher.** Dire que la mesure a un trou, sur Google Analytics ou sur l'attribution, est une preuve de sérieux.
6. **On pense la relation donateur par typologie, pas par canal.** Grand public, legs, P2P, prélèvement automatique : chacun son rythme, chacun sa temporalité de confiance.
7. **On grandit par la preuve, pas par l'appétit budgétaire.** Rien ne se généralise avant d'avoir été testé à petite échelle.

## Arguments AO multi-lots (secteur associatif, collecte)

À placer dans « Pourquoi Periscope » (`card_grid`, `compare_cards` pour pure digital vs 360, `logo_grid` pour les co-agences).

- **Autonomie digitale** : l'agence Lot 4 (digital) ne peut pas être aux ordres de l'agence Lot 1, souvent peu experte en digital ; c'est l'une des raisons pour lesquelles les résultats digitaux stagnent. Periscope positionne son indépendance stratégique comme une garantie de performance.
- **Expertise pure digital vs agence 360** : une vraie agence digitale sera toujours plus performante qu'une agence 360 sur le Lot 4.
- **Expertise Rgive** : Periscope est expert de la solution de formulaires de collecte Rgive (client + relations privilégiées) ; impact direct sur le taux de conversion et la valeur du don.
- **Chatbot propriétaire** : quand l'AO demande un chatbot (relation testateurs, par exemple), Periscope dispose de son propre chatbot ; atout majeur sur l'axe innovation.
- **Expérience avérée du travail en co-agence** : dispositifs multi-lots en bonne intelligence, c'est dans notre culture. Exemples : Maxyma sur le compte Amnesty International, Hopening sur les comptes Fondation de France et 30 Millions d'Amis, Adfinitas sur le compte Armée du Salut. Nous savons co-construire sans ego, en maintenant une exigence de performance digitale totale.

## Couleurs de régies (bilans média)

Rôles du thème `periscope`, à passer tels quels dans les props `color` / `colors` / `category_colors` / `dots` : `regie_google` (#00E5C3), `regie_bing` (#C383FF), `regie_meta` et `regie_facebook` (#FA00A6), `regie_instagram` (#FF9170), `regie_pinterest` (#E8FF00), `regie_linkedin`, `regie_tiktok`, `regie_ga4` (#45DBFF). Convention N / N-1 : N en couleur pleine (`accent_dark` navy), N-1 en gris (`gray_2`). Côté Google Sheets (graphiques natifs), les mêmes hex dans `series_colors` / `point_colors`, et dans l'ordre des accents du thème pour les camemberts.

## Références visuelles

- Catalogue des composants (une slide par composant, puis une par variante ; les graphiques natifs Sheets y sont embarqués reliés) : deck `1cPrerkVnlbxs5QtKjlILoBDO-MczFd-WViffUEUfi1E`.
- Classeur des graphiques natifs du catalogue (une feuille par graphique, thème `periscope`) : `1YHQ1HC2MvXhFm6vk9rGsi8CB_jmBXPvvEyX_BVvqKdo` ; ses `manage_chart` sont ceux des blocs `native` de `list_components`.
- Le bilan média type (tableaux à pictos de canaux, KPI alignés, graphiques légende en haut et valeurs sur toutes les barres) est la référence de style des composants `kpi_grid`, `table`, `chart_*`, `media_plan`, `ad_scoreboard`, `source_note`.

## Assets du dossier Drive (septembre 2026)

Pictos blancs recolorables : `bolt`, `download`, `google`, `lightbulb`, `megaphone`, `people`, `search`, `share`, `star`, `video`. Pictos pixel-art du design system (décoratifs, 48 à 120 pt, teintés par le thème) : `px-*` (onze, dernière slide du catalogue). Captures de démo : `screen-demo` (16:9), `laptop-demo`. Les images moissonnées d'un deck source s'emploient par `drive:<id>`. La liste vivante : `list_assets()`.

## À enrichir

Ajouter ici, après accord de l'utilisateur, la matière qui a resservi pendant un run : chiffres agence, références par secteur, équipe, méthodologie type, clause juridique.
