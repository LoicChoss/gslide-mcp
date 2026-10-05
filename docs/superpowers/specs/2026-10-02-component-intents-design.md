# Composants par intention : design

Date : 2026-10-02. Constat : Claude reprend toujours les mêmes composants (`card`, `kpi_grid`,
`table`…). `list_components()` renvoyait les 85 composants d'un coup, triés par ordre
alphabétique, avec toutes les props, les exemples et les variantes : 161 000 caractères
(environ 45 000 tokens), lus une fois et survolés. Rien n'aidait au moment du plan :
`suggest_components` ne lisait qu'une slide source existante (refonte).

## 1. Table des intentions (`components/intents.py`)

- `INTENTS` : 13 intentions (`chiffres`, `comparer`, `repartition`, `evolution`, `classer`,
  `etapes`, `structure`, `messages`, `personnes`, `visuels`, `donnees`, `atelier`,
  `habillage`), chacune avec un libellé, une expression régulière sur la description et ses
  composants, meilleurs choix en tête. Un composant peut servir plusieurs intentions.
  Un test vérifie que chaque composant intégré en sert au moins une.
- Une recette déclare les siennes avec la clé `intents` (clés de la table, vérifiées) ;
  sans clé, elle tombe dans « Autres ».
- `KEYWORDS` : le vocabulaire qui désigne des composants (« avant / après » →
  `before_after`), déplacé de `harvest.py` et complété ; partagé par les deux modes de
  `suggest_components`. Les nouvelles entrées vont en fin de liste (l'ordre sert à la refonte).
- `USUAL` : les choix que Claude fait sans y penser (`card`, `card_grid`, `kpi`, `kpi_grid`,
  `table`, `callout`, `chart_bars`, `donut`, `chevrons`, `numbered_list`).

## 2. `list_components` en deux temps

- Sans `names` : l'index. `intents: [{key, label, components}]`, `components: {name: {use,
  variants: [titres]}}`, les thèmes, `catalogue_deck` (le deck catalogue visuel),
  `how_to_add`, les assets. Environ 26 000 caractères ; un test plafonne à 32 000.
- Avec `names` : les entrées complètes de ces composants (description, use, intents, props,
  exemple, variantes avec leurs props, source). Un nom inconnu est refusé avec les noms proches.

## 3. `suggest_components(description=…, avoid=…)`

- Deux modes exclusifs : `presentation` + `slide` (refonte, inchangé) ou `description`.
- Une intention est reconnue par ses propres mots (score 2). Si aucune ne l'est, un mot-clé
  de composant amène la meilleure intention de ce composant (score 1). Deux nombres ou plus
  dans la description amènent `chiffres`. Chaque mot-clé touché dans une intention ajoute 1.
- Dans une intention, les composants désignés par un mot-clé passent en tête, un mot-clé qui
  vise peu de composants pesant plus qu'un mot-clé large ; puis l'ordre de la table.
  `avoid` (composants déjà prévus ailleurs dans le plan) les renvoie en fin de liste, dans
  les deux modes.
- `less_obvious` : dans la meilleure intention d'abord, le premier candidat qui n'est ni
  habituel, ni évité, ni premier choix d'une intention.
- Rien de reconnu : `intents: []` et `all_intents` pour choisir.

## 4. Skill

Avant le plan, l'index ; pour chaque slide, partir de l'intention et lire le `use` de tous
les candidats ; en cas de doute, `suggest_components(description=…, avoid=…)` ; avant la
rédaction, `list_components(names=[…])` pour les props.
