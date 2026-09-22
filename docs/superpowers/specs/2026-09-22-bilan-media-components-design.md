# Composants « bilan média » et style de graphiques : design

Date : 2026-09-22. Source : le template Google Slides « Bilan CFA » (62 slides) et le
bilan CFA 2025 30MA généré en .pptx (41 slides), qui est la **référence visuelle**
pour les graphiques. Objectif : que le MCP sache produire un bilan média complet
(reporting régies + GA4) avec ses composants chartés, propres sans être pixel-perfect.

## 1. Thème `periscope`

- Nouveaux tokens : `google #00E5C3`, `bing #C383FF`, `meta #FA00A6`, `pinterest #E8FF00`,
  `instagram` = `orange` (#F5A623), `facebook` = `meta`, `linkedin #0A66C2`, `tiktok #111418`.
- Nouveaux rôles : `regie_google`, `regie_bing`, `regie_meta`, `regie_facebook`,
  `regie_instagram`, `regie_pinterest`, `regie_linkedin`, `regie_tiktok`, `regie_ga4`
  (= `orange`). Un composant graphique accepte `color: "regie_meta"` comme n'importe
  quel rôle ; le thème `default` mappe les mêmes rôles sur `series_1…6`.
- `Theme.tint(color, amount)` : mélange une couleur résolue avec le blanc
  (`amount` 0 → 1) et renvoie un hex. Sert aux séries N-1 (« foncé = N, clair = N-1 »).
- `Theme.is_dark(color)` : luminance relative < 0,45. Sert à choisir `on_dark` ou `ink`
  pour un texte posé sur une part de donut ou une boîte colorée.
- Rôle `chart_grid` = `row_line` (grille fine), `chart_axis` = `row_line` (ligne de
  base). Les graphiques n'utilisent plus `ink` pour l'axe.

## 2. Canvas `draw`

- `box.line.dash` : `DASH`, `DOT`, `DASH_DOT` sur le contour d'une forme
  (`outline.dashStyle`). Sert aux cadres « à déposer » et aux boîtes pointillées de la frise.
- `table.row_heights` : liste de hauteurs par ligne (défaut : `row_h` partout). Sert à la
  ligne « Visuel » du scoreboard. La hauteur totale de la table est la somme.

## 3. Style commun des graphiques (référence pptx)

Appliqué à `chart_bars`, `chart_line`, `chart_combo`, `chart_stacked`, `chart_grouped`,
`mini_charts` :

- Grille horizontale : `chart_grid`, 0,5 pt. Ligne de base : `chart_axis`, 1 pt. Plus
  d'axe vertical dessiné.
- Courbes : 1,5 pt (était 2,5 à 3). Marqueurs : 4 pt, prop `markers` (`auto` = affichés
  quand il y a au plus 12 points, sinon masqués ; `true` / `false` forcent).
- Légende : prop `legend_pos` (`top` | `bottom` | `none`), défaut `top` centrée pour
  `chart_combo` et `chart_grouped`, `bottom` pour les autres (inchangé). Swatch 8 × 8.
- Libellés d'axe X : éclaircis automatiquement quand un slot est plus étroit que le
  libellé (on garde un libellé sur k, le premier et le dernier toujours). Pas de rotation
  (l'API le permet mais les ops ne la portent pas : hors périmètre).
- Valeurs sur les barres et les points : `show_values` inchangé, mais `auto` par défaut
  sur `chart_combo` : affichées jusqu'à 12 points, masquées au-delà.
- Prop `title` (caption centrée au-dessus) et `panel` (fond `surface`, coins arrondis,
  padding 10) sur tous les graphiques listés plus `donut` : c'est le « chart_panel » du
  pptx, réalisé par un helper `panelize(ops, height, w, title, panel)` dans `axes.py`.

## 4. Nouveaux composants et props

### Graphiques

| Nom | Props | Rendu |
|---|---|---|
| `chart_grouped` | `labels*`, `series*` `[{name, values, color?}]`, `category_colors` (liste de couleurs, une par catégorie : la série k prend `tint(couleur, 0.55·k)`), `horizontal` (défaut false), `unit`, `max`, `y_axis` (défaut true), `show_values` (défaut true), `legend_pos`, `title`, `panel` | Barres côte à côte par catégorie. Avec `category_colors` : foncé = N, clair = N-1, une teinte par régie. Horizontal : libellés à gauche, valeurs au bout des barres. |
| `chart_bars` | + `colors` (liste, une par barre), `title`, `panel` | Inchangé sinon. |
| `donut` | + `labels` (pourcentages posés sur les parts ≥ 6 %), `legend_pos` (`right` défaut, `bottom`), `title`, `panel` | Texte de part en `on_dark` ou `ink` selon `is_dark`. |
| `donut_row` | `items*` `[{title, segments}]`, `cols`, `gap`, `labels` (défaut true), `legend_pos` (défaut `bottom`), `panel` | `donut` répété, titre au-dessus, légende dessous. |
| `mini_charts` | `labels*` (catégories partagées), `charts*` `[{title, values, unit?}]`, `colors` (une par catégorie), `cols`, `y_axis` (défaut true) | Petits multiples : un histogramme par indicateur, mêmes catégories, largeur partagée. |

### Chiffres et texte

| Nom | Props | Rendu |
|---|---|---|
| `kpi` | + `note` | Petit suffixe muted après le libellé : « Collecte (GA4) ». |
| `kpi_grid` | items `{…, note?}` ; + `rows` (libellés de ligne) | Avec `rows` : une colonne de libellés en gras à gauche (largeur 90 pt), une rangée par libellé, `cols` = nombre d'indicateurs. |
| `analysis_block` | `title` (défaut « Notre analyse : »), `items` (liste, rendue en chevrons ›) ou `text` (markdown), `box` (contour accent, défaut false), `size` | Titre en gras `callout_title`, puis chevrons ou paragraphe. Remplace le bloc texte nu des deux decks. |
| `source_note` | `text*`, `platform` (texte : « Google Ads »), `logo` (asset), `align` (défaut `END`) | Une ligne caption italique « * Sources : … », puis la plateforme en dessous (logo 14 pt + nom, ou nom seul). |
| `stat_box` | `boxes*` `[{value, label}]`, `operator` (défaut `=`), `box_w`, `box_h` | Chiffres encadrés `accent` 1,5 pt, valeur `kpi_value` centrée, libellé dessous, opérateur en gras entre les boîtes. |
| `takeaways` | `items*` `[{title, text}]` ou textes, `highlight` (surligne les titres, défaut false), `gap` | Titre gras (surligné en `highlight` si demandé) + paragraphe. Slides Enseignements / Recos. |
| `placeholder` | `text*`, `height` (défaut 120), `dash` (défaut true) | Cadre `surface` à contour pointillé `divider`, texte muted centré. |

### Tableaux et médias

| Nom | Props | Rendu |
|---|---|---|
| `table` | + `icons` (un asset par ligne de données, ou null), `icon_w` (défaut 16), `delta_cols` (index de colonnes dont le texte se colore par signe), `row_heights` | `icons` ajoute une colonne vide de 26 pt en tête où l'image est posée (contain), l'en-tête garde son fond. `delta_cols` colore `+` en `positive`, `-` en `negative`. |
| `ad_scoreboard` | `ads*` `[{name, image?, values: {metric: valeur}}]`, `metrics*` (liste ordonnée des lignes), `image_h` (défaut 56), `top_note`, `first_col_w` | Table transposée : en-tête = noms d'annonces (fond `ink`, texte `on_dark`), ligne « Visuel » avec images (contain) ou cadre pointillé, lignes de métriques, première colonne fond `accent`. `top_note` en italique caption à droite, sous la table. |
| `gallery` | `images*` (asset, url, ou null), `cols`, `gap`, `ratio` (w/h, défaut 0.62), `captions`, `placeholder_text` (défaut « Capture de l'annonce (à déposer) ») | Images en `contain` dans des cases de ratio fixe ; case vide = cadre pointillé `surface` avec le texte. |

### Dispositif

| Nom | Props | Rendu |
|---|---|---|
| `media_plan` | `levers*` `[{name, logos: [asset], budget, dates}]`, `objective` `{title, items}` (optionnel), `budget_label` (défaut « Ordre d'insertion : »), `dates_label` (défaut « Date : »), `split` (part de la largeur pour le panneau, défaut 0.45) | Gauche : « Leviers déployés » puis par levier une pastille accent, le nom en capitales gras, les logos (16 pt, contain), deux lignes libellé + valeur en gras. Droite : panneau `accent` plein avec pastille blanche, titre gras et chevrons. Sans `objective`, la liste prend toute la largeur. |
| `timeline_arrow` | `events*` `[{date, text, style: filled|outline|dashed, above?}]`, `box_w` (défaut 120), `box_h` (défaut 46), `alternate` (défaut true) | Flèche `accent` 10 pt pleine (ligne à `end_arrow`), boîtes alternées au-dessus / au-dessous reliées par un trait `ink` 1 pt ; `filled` = fond `accent`, `outline` = contour `ink`, `dashed` = contour pointillé `ink`. Date en gras, texte en dessous, centrés. |

## 5. Ce qui ne change pas

`kpi_cards`, `table` (par défaut), `chart_stacked` (défaut légende bas), `timeline`
(pastilles), `chevrons`. Les composants existants gardent leurs props et leurs valeurs
par défaut, sauf les changements de style listés au § 3 (épaisseurs, grille, légende
de `chart_combo` en haut, `markers` et `show_values` en `auto` sur `chart_combo`).

## 6. Fichiers

- `themes/periscope.json`, `themes/default.json`, `themes/__init__.py` (tint, is_dark).
- `draw.py` (dash sur box, row_heights sur table).
- `components/axes.py` : style commun (`GRID`, `AXIS`, `LINE_W`), `thin_labels`,
  `legend_ops(entries, x, y, w, pos)`, `panelize`.
- `components/builtin.py` : kpi `note`, kpi_grid `rows`, chart_bars `colors`, donut
  `labels` / `legend_pos`, table `icons` / `delta_cols` / `row_heights`, style commun.
- `components/charts2.py` : chart_stacked style commun.
- `components/charts3.py` (nouveau) : chart_grouped, donut_row, mini_charts.
- `components/reporting.py` (nouveau) : analysis_block, source_note, stat_box,
  takeaways, placeholder, ad_scoreboard, gallery, media_plan, timeline_arrow.
- `components/uses.py`, `docs/components.md`, `README.md` (tableau des composants),
  `CHANGELOG.md`.
- Tests : `tests/test_components6.py` (nouveaux composants), mises à jour ciblées de
  `test_components5.py` (chart_combo) et `test_themes.py` (rôles régies, tint).

## 7. Vérification

1. Tests unitaires sur les ops (géométrie, rôles, textes), rendu de chaque `example`
   dans les deux thèmes, requêtes générées sans erreur.
2. Contrôle visuel sur un deck de test créé dans le Drive de l'utilisateur
   (« gslides-mcp · test composants · 2026-09 ») : une slide par composant, insérée avec
   le code du dépôt (pas le bundle installé), capturée avec `screenshot_range`, comparée
   au pptx de référence. On corrige jusqu'à propre ; le deck de test est laissé en place
   pour la revue.
