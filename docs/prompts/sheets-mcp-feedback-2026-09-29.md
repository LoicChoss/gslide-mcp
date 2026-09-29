# Prompt : retours sur google-sheets-mcp après le remplissage d'un bilan maquetté (2026-09-29)

À coller dans une session Claude Code ouverte sur `C:\Users\Loic CHOSSIERE\Documents\GitHub\google-sheets-mcp`.

---

Tu travailles dans le dépôt `google-sheets-mcp`. Lis `CLAUDE.md` et `docs/architecture.md` avant tout et respecte les règles dures (rien d'interne dans le code, les docs, les fixtures et les commits ; A1 partout ; types wire maison dans `internal/gsheets` ; fixtures générées ; branche topic, pas de push sur `main`).

## Contexte

Un bilan média récurrent a été mis à jour avec les deux MCP : les chiffres du mois écrits dans le classeur par ce serveur, puis le deck Slides maquetté rempli par gslide-mcp. Deux points côté Sheets ont coincé. Chaque point donne le constat et le changement demandé.

## 1. `write_values` efface les cellules voisines d'une plage de plusieurs colonnes

Constat : pour écrire les colonnes B et D d'une ligne sans toucher C, le modèle a écrit `B2:D2` avec `""` en C2, comme le suggère le message du refus d'un tableau irrégulier (« Pad the short rows with empty strings to clear those cells »). Avec `overwrite`, C2 a été vidée ; la valeur a dû être restaurée à la main. Le refus sans `overwrite` nommait bien C2 parmi les cellules occupées, mais au milieu des cellules qu'on voulait vraiment écraser : rien ne distinguait « sera remplacée » de « sera vidée ».

Demandé :

- **`null` = laisser la cellule telle quelle.** Accepter `null` dans `values` (et une cellule vide de `tsv` reste `""`, inchangé) : l'API `values.update` saute les valeurs nulles (« Null values will be skipped », référence `ValueRange.values`) ; le vérifier en direct et le consigner dans le journal de preuves. Les cellules sautées n'entrent ni dans le contrôle d'occupation ni dans `overwrite`. Le résultat les liste (`skipped`).
- **Dire ce qui sera vidé.** Dans le refus, le `dry_run` et le résultat, séparer `cleared` (une `""` écrite sur une cellule non vide) de `overwritten` (une valeur remplacée par une autre). Le refus avec des cellules `cleared` dit en une phrase : « `""` vide la cellule ; `null` la laisse telle quelle ».
- **Message du tableau irrégulier** : proposer `null` pour laisser les cellules telles quelles et `""` pour les vider, au lieu de la seule piste `""`.
- **Plusieurs blocs en un appel** (optionnel, si simple) : `writes: [{range, values}]` envoyé en un `values.batchUpdate`, avec le même contrôle d'occupation sur l'ensemble, pour remplir une période colonne par colonne sans englober les colonnes à garder.

Tests : service sur le faux Sheets (null sauté, `cleared` vs `overwritten`, refus), golden de la description, driver live qui écrit `["x", null, "y"]` sur trois cellules pleines et relit la cellule du milieu.

## 2. Choisir le dossier d'un classeur créé

Constat : `create_spreadsheet` crée le classeur à la racine de Mon Drive. Le classeur des graphiques d'un deck doit vivre à côté du deck ; aujourd'hui il faut le déplacer après coup avec l'outil `move_to_folder` de gslide-mcp.

Demandé :

- `create_spreadsheet` accepte `folder` (id ou URL `drive.google.com/drive/folders/<id>`) : création par Drive `files.create` avec `parents` et `mimeType` classeur (`supportsAllDrives`), puis la suite habituelle (feuilles, valeurs de départ) sur le classeur créé. Et `next_to` (id ou URL d'un fichier Drive : le deck) : même dossier que ce fichier, lu par `files.get(fields=parents)`. Refus clair si `folder` n'est pas un dossier ou n'est pas accessible ; si le dossier de `next_to` n'accepte pas de nouveau fichier, créer à la racine et le dire dans le résultat (`folder_note`), comme `clone_deck` côté Slides.
- Le résultat donne `folder_id` et le nom du dossier.
- Vérifier le scope : `folder` / `next_to` demandent le scope Drive complet (un scope `drive.file` ne voit pas un dossier que l'app n'a pas créé). Le serveur hébergé l'a déjà ; en local, dire dans la description ce qui se passe sans lui.

## Méthode

- Vérifie chaque champ contre le discovery document ou une sonde en direct, et consigne le verdict dans le journal de preuves de `docs/architecture.md`.
- Docs : `README.md` (tableau des outils), `docs/`, `CHANGELOG.md`.
- Commit par point sur une branche topic, message qui dit quoi et pourquoi. Pas de push, pas de PR.
