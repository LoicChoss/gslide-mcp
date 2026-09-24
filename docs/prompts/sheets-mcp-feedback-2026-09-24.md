# Retour d'usage google-sheets-mcp, test de bout en bout du 24/09/2026

À coller dans une session Claude Code sur `google-sheets-mcp`. Contexte : le flux
`set_theme` → `write_values` → `manage_chart add` → (Slides) `insert_sheets_chart` →
`refresh_sheets_charts` marche de bout en bout, rendu Barlow et couleurs charte. Quatre
frottements rencontrés en route, à corriger dans l'ordre :

1. **`series` refuse une chaîne seule.** `series: "D1:D5"` est rejeté par le schéma
   (`want one of "null, array"`) alors que la description dit « B1:B20 draws one line ».
   Accepter une chaîne comme une liste d'un élément, ou dire dans la description que
   c'est toujours une liste.

2. **`manage_chart update` se trompe de feuille.** Sur un graphique ancré sur la feuille
   « Collecte » (une feuille normale, avec cellules), `update` sans `sheet` répond :
   « chart … is on "Collecte", which is a sheet of its own and holds no cells ». La
   détection « feuille de graphique sans grille » prend une feuille ordinaire pour une
   feuille d'objet. Avec `sheet: Collecte` ça passe. Corriger la détection (regarder
   `sheetType` / `gridProperties`, pas l'absence de valeurs), et de toute façon `update`
   devrait retrouver la feuille du graphique tout seul à partir de son id.

3. **Étiquettes d'un camembert.** `data_labels: true` sur un pie / doughnut est refusé
   avec un message qui renvoie vers `pie_labels`, et `pie_labels` est un booléen : on ne
   choisit pas entre pourcentage et valeur. Proposer `pie_labels: percent | value |
   none` (l'API : `PieChartSpec.legendPosition = LABELED_LEGEND` pour les libellés,
   et les étiquettes de données via `pieChart` n'existent pas ; le pourcentage se fait
   par `PieChartSpec` + `legendPosition`, à vérifier contre le discovery document et
   consigner). Au minimum, laisser `data_labels` fonctionner sur un pie comme alias.

4. **Ratio par défaut.** Un graphique naît en 600 × 371 px ; Slides le recentre dans la
   boîte au ratio près. Pour un donut, `width`/`height` carrés (par ex. 400 × 400) rendent
   mieux dans une slide : documenter, et laisser le preset `periscope` proposer un carré
   pour pie / doughnut quand `width` / `height` ne sont pas donnés.

Rappels du dépôt : rien d'interne dans le code, les docs, les fixtures et les commits ;
vérifier chaque champ contre le discovery document et le consigner dans
`docs/architecture.md` §18 ; branche topic, pas de push.
