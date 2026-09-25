# Prompt : retours sur google-sheets-mcp après le catalogue de graphiques natifs (2026-09-25)

À coller dans une session Claude Code ouverte sur `C:\Users\Loic CHOSSIERE\Documents\GitHub\google-sheets-mcp`.

---

Tu travailles dans le dépôt `google-sheets-mcp`. Lis `CLAUDE.md` et `docs/architecture.md` avant tout et respecte les règles dures (rien d'interne dans le code, les docs, les fixtures et les commits ; A1 partout ; types wire maison dans `internal/gsheets` ; fixtures générées ; branche topic, pas de push sur `main`).

## Contexte

Le serveur `gslide-mcp` embarque en liaison vivante les graphiques que ce serveur construit (`insert_sheets_chart`, `refresh_sheets_charts`). Le 2026-09-25 nous avons construit avec les deux MCP le classeur « gslides-mcp · catalogue graphiques natifs » (id `1YHQ1HC2MvXhFm6vk9rGsi8CB_jmBXPvvEyX_BVvqKdo`, une feuille par graphique : bars, grouped, stacked, line, combo, donut, pie, table) et embarqué chaque graphique dans le deck catalogue de composants. Tout a fonctionné ; ce qui suit est ce que l'usage réel a révélé. Chaque point donne le constat, la preuve et le changement demandé.

## 1. Couleurs de régies (le plus utile)

Constat : dans un bilan média, chaque régie a une couleur fixe (Google `#00e5c3`, Bing `#c383ff`, Meta / Facebook `#fa00a6`, Instagram `#ff9170`, Pinterest `#e8ff00`, LinkedIn `#0a66c2`, TikTok `#002b3c`, GA4 `#45dbff`). Aujourd'hui il faut connaître ces hex et les passer un par un dans `series_colors` ou `point_colors`.

Demandé :

- `series_colors` et `point_colors` acceptent un **nom de régie** (`google`, `bing`, `meta`, `facebook`, `instagram`, `pinterest`, `linkedin`, `tiktok`, `ga4`, insensible à la casse) en plus d'un hex ou d'un slot de thème, résolu vers la table ci-dessus. La table vit à un seul endroit (à côté du style `periscope`) et est citée dans la description de l'outil.
- Nouveau paramètre `domain_colors: true` (ou `color_by: domain`) sur `add` / `update` d'un graphique à une série : une couleur par point d'après le **libellé de la catégorie** (la colonne domaine), quand ce libellé est une régie connue ; les autres points gardent la couleur de la série. C'est ce que fait aujourd'hui `point_colors: ["1:1 #00e5c3", "1:2 #c383ff", …]`, mais sans avoir à compter les lignes.
- Camemberts et doughnuts : l'API n'a **aucun champ de couleur par part** (`PieChartSpec` = `legendPosition`, `domain`, `series`, `threeDimensional`, `pieHole`, vérifié sur la référence et sur une spec relue). Les parts prennent les accents du thème du classeur **à partir d'accent2**, dans l'ordre des lignes. Vérifié le 2026-09-25 : `set_theme` avec `accent2 #00e5c3, accent3 #fa00a6, accent4 #c383ff` a recoloré un doughnut Google / Meta / Bing aux couleurs de régies, y compris dans Slides après `refresh_sheets_charts`. Demandé :
  - `set_theme` : preset `periscope_regies` = preset `periscope` avec les accents 2 à 6 dans l'ordre Google, Meta, Bing, Instagram, GA4 ; et une forme `accents_from: ["google", "meta", "bing", …]` qui range les accents d'après des noms de régies.
  - `manage_chart add` pour `pie` / `doughnut` : paramètre `slice_colors` (hex ou noms de régies, un par part dans l'ordre des lignes) qui **écrit les accents du thème** accent2… en conséquence, avec dans le résultat l'avertissement que le thème vaut pour tout le classeur (tous les camemberts du classeur suivent le même ordre) ; refuser proprement au-delà de cinq parts (accent2 à accent6).
  - `list` : pour un pie / doughnut, dire quelle couleur du thème chaque part reçoit (accent2 = Google…), puisque la spec ne le porte pas.

## 2. `line_width`, `line_dash`, `point_shape` sur un combo

Constat : `line_width: [2, 2]` sur un combo `["column", "line"]` est refusé par Google (`series[0].lineStyle not supported when chartType is COLUMN`) ; `["", 2]` est refusé par le schéma (entiers attendus) ; seul `[0, 2]` passe.

Demandé : sur un combo, ignorer `line_width` / `line_dash` / `point_shape` pour les séries `column` et `area` (ne pas envoyer `lineStyle` / `pointStyle` pour elles) et accepter `null` dans la liste ; le dire dans la description. Test de service sur le faux Sheets + golden.

## 3. Libellés de parts d'un camembert

Constats, tous vérifiés le 2026-09-25 :

- `pie_labels: true` (légende `LABELED_LEGEND`) : rien ne s'affiche une fois le graphique embarqué dans Slides, ni légende ni libellés.
- Les pourcentages sur les parts (éditeur Sheets : Personnaliser → Graphique à secteurs → Libellé de secteur → Pourcentage) n'ont **aucun champ dans l'API** : une spec relue après ce réglage manuel ne le montre pas, et un `updateChartSpec` (donc tout `manage_chart update`) remplace la spec et l'efface.

Demandé :

- Description de `pie_labels` : dire que c'est invisible dans Slides et recommander `legend: right` pour un graphique destiné à un deck.
- Résultat de `update` sur un `pie` / `doughnut` : avertir que les libellés de parts posés à la main dans l'éditeur sont perdus (l'API ne sait ni les lire ni les écrire) et qu'il faut les reposer en dernier.

## 4. Format de nombre des étiquettes et de l'axe

Constat : les étiquettes de valeurs et l'axe suivent le **format des cellules sources**. Sans `format_cells number:#,##0` sur les colonnes de valeurs, un combo affiche « 1085349 » ; avec, « 1 085 349 » (locale fr_FR).

Demandé : paramètre `number_format` sur `manage_chart add` / `update` (même syntaxe que `format_cells`, ex. `number:#,##0` ou `currency:#,##0" €"`) appliqué aux plages des séries dans le même batch ; et, dans la description de `data_labels`, la phrase qui renvoie vers ce paramètre ou vers `format_cells`.

## 5. Tableaux

Constat : l'API Slides n'offre pas de tableau relié à une plage. Le flux retenu : ce serveur écrit ou lit la plage, `read_range` avec `formatted: true, format: json` renvoie les chiffres à la française, et gslide-mcp rend la table chartée (colonnes « N-1 » en gris, « vs N-1 » colorées par signe, reconnues sur l'en-tête). Rien à changer ici, sinon une ligne dans la doc de `read_range` : « pour un tableau dans Slides, lire formaté en JSON et le donner au composant `table` de gslide-mcp ».

## Méthode

- Vérifie chaque champ contre le discovery document ou une sonde en direct, et consigne le verdict dans le journal de preuves de `docs/architecture.md`.
- Tests : golden de rendu, tests de service sur le faux Sheets, driver live sur un classeur que le test crée.
- Docs : `README.md` (tableau des outils), `docs/`, `CHANGELOG.md`.
- Commit par point sur une branche topic, message qui dit quoi et pourquoi. Pas de push, pas de PR.
