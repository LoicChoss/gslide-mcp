# Prompt : graphiques chartés dans google-sheets-mcp

À coller dans une session Claude Code ouverte sur `C:\Users\Loic CHOSSIERE\Documents\GitHub\google-sheets-mcp`.

---

Tu travailles dans le dépôt `google-sheets-mcp` (serveur MCP Go pour Google Sheets, stdio, OAuth par utilisateur). Lis `CLAUDE.md` et `docs/architecture.md` avant tout : règles dures (rien d'interne dans le code, les docs, les fixtures et les commits ; A1 partout ; types wire maison dans `internal/gsheets`, jamais `google.golang.org/api` ; fixtures générées, jamais enregistrées ; branche topic, pas de push sur `main`).

## Objectif

Permettre au MCP de produire des graphiques **à la charte Periscope** que le serveur `gslide-mcp` embarque ensuite dans Google Slides en liaison vivante (`insert_sheets_chart` / `refresh_sheets_charts`, déjà livrés côté Slides). Aujourd'hui `manage_chart` sait créer column, bar, line, area, stepped_area, scatter, pie, doughnut avec empilement, titre, sous-titre, titre d'axe, légende, taille et ancrage. Il manque tout le style. Le Sheets API le permet, c'est vérifié en direct (voir « Vérifié » plus bas).

Les deux serveurs ne se parlent pas : le modèle orchestre. Le flux cible :

1. Classeur : celui de l'utilisateur (URL) ou `create_spreadsheet` nommé comme le deck.
2. Thème du classeur = charte (une fois par classeur) → tous les graphiques héritent police et couleurs.
3. `write_values` des données (catégories en première colonne, une série par colonne, une ligne d'en-tête ; formules bienvenues).
4. `manage_chart add` avec le style → renvoie `chart_id`.
5. Côté Slides, `insert_sheets_chart(deck, slide, spreadsheet, chart_id, x, y, w, h)` puis `refresh_sheets_charts` quand les données bougent.

## À livrer

### 1. Thème du classeur

Nouvelle action (`manage_sheet` ou un outil `manage_theme`, à toi de juger d'après l'architecture) qui pose `spreadsheetProperties.spreadsheetTheme` via `updateSpreadsheetProperties` : `primaryFontFamily` et `themeColors` (TEXT, BACKGROUND, ACCENT1…ACCENT6, LINK). Prévoir un preset nommé `periscope` et la forme libre (police + couleurs hex). Lister le thème courant dans la carte `get_spreadsheet`.

Charte Periscope (thème Google Slides « Présentation - Periscope ») :

| Rôle | Hex | Usage |
|---|---|---|
| TEXT | `#002B3C` | navy, texte et fond sombre |
| BACKGROUND | `#FFFFFF` | blanc |
| ACCENT1 | `#E8FF00` | acide |
| ACCENT2 | `#00F5B5` | menthe (accent principal) |
| ACCENT3 | `#45DBFF` | cyan |
| ACCENT4 | `#FF9170` | corail (négatif, alerte) |
| ACCENT5 | `#FA00A6` | magenta |
| ACCENT6 | `#9E38FF` | violet |
| LINK | `#002B3C` | navy |
| gris | `#EDEDED` | fonds, séries N-1 |
| police | Barlow | tous les textes |

Couleurs de régies utilisées dans les bilans (à documenter, pas à coder en dur) : Google `#00E5C3`, Bing `#C383FF`, Meta / Facebook `#FA00A6`, Instagram `#FF9170`, Pinterest `#E8FF00`, GA4 `#45DBFF`. Convention N / N-1 : N en couleur pleine, N-1 en teinte claire de la même couleur (ou gris `#EDEDED`).

Attention, constaté en direct : les parts d'un camembert ou d'un donut prennent les couleurs du thème **à partir d'ACCENT2**, pas d'ACCENT1. Documente-le et propose un ordre des accents en conséquence quand le preset est appliqué (ou laisse le preset tel quel et écris-le noir sur blanc dans la description de l'outil).

### 2. `manage_chart` : style

Étendre `add` et `update` (en gardant la relecture complète avant `updateChartSpec`, comme aujourd'hui) avec :

- `series_colors` : une couleur hex par série (`BasicChartSeries.colorStyle`), et `point_colors` optionnel (`styleOverrides` / `colorStyle` par point).
- `series_types` : par série `column | bar | line | area` → `chartType: COMBO` avec `type` par série ; `series_axes` : `left | right` par série (`targetAxis`).
- `line_width`, `line_dash` par série (`lineStyle`), `point_shape` (`pointStyle`).
- `data_labels: true | false` + format texte (`dataLabel` avec `textFormat`).
- `pie_hole` (0 à 1, 0,55 pour le donut charte), `pie_labels` (`LABELED_LEGEND` ou étiquettes).
- `font` (`fontName`), `title_format`, `axis_format`, `legend_format` : `{size, bold, color}` (`titleTextFormat`, `BasicChartAxis.format`, légende via `textFormat` où l'API l'accepte).
- `background` : hex ou `transparent` (`backgroundColorStyle`).
- `axis_min`, `axis_max`, `axis_number_format`, `hide_axis` (`viewWindowOptions`, `format`, `BasicChartAxis` visibilité selon ce que le discovery document accepte).
- Nouveaux `chart_type` : `combo` (raccourci de `series_types`), `bubble`, `scorecard`, `histogram`, `waterfall`, `treemap`, avec leurs specs propres ; refuser proprement ce que le serveur ne construit pas, comme aujourd'hui.
- Preset `style: periscope` : Barlow 10 pt, titre 11 pt gras navy, légende en haut, fond blanc, grille par défaut, étiquettes de valeurs en navy. Toute option explicite prime sur le preset.

`list` doit relire et afficher ces options (couleurs, axes, type par série), pas seulement le type.

### 3. Méthode

- Vérifie chaque champ contre le discovery document ou une sonde en direct, et consigne le verdict dans le journal de preuves de `docs/architecture.md` §18. La prose d'une page de référence n'est pas une preuve.
- Étends `internal/gsheets/chart.go` (types wire), `internal/service/chart.go`, `internal/tools/chart.go`, `internal/render/chart.go`, et le faux Sheets `internal/gapi/sheetstest/chart.go` pour que `updateChartSpec` et la relecture couvrent les nouveaux champs.
- Tests : golden de rendu, tests de service sur le faux, et le driver live sur un classeur que le test crée et remplit lui-même.
- Docs : `README.md` (tableau des outils), `docs/`, `CHANGELOG.md`.
- Commit par phase sur une branche topic, message qui dit quoi et pourquoi. Pas de push, pas de PR.

### 4. Connexion et test de bout en bout

- Le serveur s'authentifie avec `google-sheets-mcp login` (OAuth loopback, jeton dans le trousseau → fichier → env, voir `docs/configuration.md` et `docs/gcp-setup.md`). Dans Claude Desktop, le connecteur Sheets répondait `no_credentials` : il faut lancer ce login une fois avec le même profil que celui configuré dans le client.
- Le scope `spreadsheets` suffit pour tout ce qui précède ; `updateSpreadsheetProperties` (thème) est couvert.
- Test manuel de bout en bout, une fois le login fait : créer un classeur, poser le thème `periscope`, écrire un petit jeu de données, ajouter un donut (`pie_hole` 0,55), des colonnes N / N-1 (`series_colors` navy et gris, `data_labels`) et un combo (barres menthe axe gauche, courbe magenta axe droit, `line_width` 2), puis dans gslide-mcp `insert_sheets_chart` sur une slide et `screenshot`. Le rendu attendu : Barlow partout, couleurs charte, légende en haut.

## Vérifié en direct (2026-09-22, via l'API brute)

- `spreadsheetTheme` avec `primaryFontFamily: Barlow` et les neuf `themeColors` est accepté à la création du classeur.
- `pieChart.pieHole`, `basicChart.chartType: COMBO` avec `type` par série et `targetAxis: RIGHT_AXIS`, `colorStyle` par série, `dataLabel` avec `textFormat`, `fontName`, `titleTextFormat`, `backgroundColorStyle`, `BasicChartAxis.format` : tous acceptés et rendus dans Slides après `createSheetsChart` en mode `LINKED`.
- La couleur des lignes de grille n'est pas réglable.
- Slides conserve le ratio du graphique dans la boîte d'accueil (600 × 371 px par défaut).

Ne mets aucun identifiant de classeur ni de deck dans le code, les tests, les docs ou les commits du dépôt.
