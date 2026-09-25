# Remettre un deck existant à la charte

Un deck ancien (autre charte, autre agence, export PowerPoint) se refait
**dans une nouvelle présentation** bâtie sur le template : on ne copie pas
ses slides, on en réécrit le contenu avec les layouts et les composants
chartés. Quatre outils portent ce flux : `harvest_deck_assets`,
`inspect_slide` (enrichi), `suggest_components` et `list_layouts`
(`content_area`).

## 1. Mettre les visuels de côté

Les URL d'images que renvoie l'API Slides expirent après une trentaine de
minutes. Première étape, une fois pour tout le deck :

```
harvest_deck_assets(presentation=old_deck, folder=None)
```

**Demander d'abord à l'utilisateur** où stocker : un dossier Drive existant
(passer son id ou son URL dans `folder`), ou laisser l'outil créer
« *<titre du deck>* · sources » dans le dossier d'assets (`folder_name`
pour un autre nom). L'outil renvoie l'id du dossier ; le relancer réutilise
les fichiers déjà présents.

Chaque image est stockée sous `sNN-k-<alt>.png` et revient avec :

- `url` — pour `insert_image` et les ops `image` de `draw` ;
- `asset` — `drive:<id>`, accepté par toutes les props `icon` / `image` /
  `logo` / `photo` des composants (`browser`, `gallery`, `card`,
  `ad_scoreboard`, `logo_wall`…), teinte comprise ;
- la géométrie d'origine (`x, y, w, h` en pt) et le texte alternatif.

Une capture de chaque slide (`sNN-slide.png`) est rangée au même endroit
pour garder l'original sous les yeux pendant la refonte.

## 2. Lire une slide source

```
inspect_slide(old_deck, 7)
```

renvoie, en plus de la géométrie : le type de placeholder (`TITLE`,
`BODY`…), les paragraphes avec leur niveau et leur puce (prêts pour le
markdown), les cellules des tableaux (`rows`, à passer telles quelles au
composant `table`) et l'URL temporaire des images (`image_url`, que la
moisson a déjà copiée).

## 3. Choisir les composants, bloc par bloc

```
suggest_components(old_deck, 7)
```

Une slide porte souvent plusieurs choses : un titre, un tableau, une rangée
de chiffres, un paragraphe, une capture, une note de source. L'outil découpe
la slide en `blocks` — chacun avec sa zone sur la slide source, les éléments
d'origine, un extrait et des candidats classés (composant, raison, phrase
`use` du catalogue, titres des variantes) :

| Ce que la slide contient | Candidats proposés |
|---|---|
| tableau de résultats par canal | `table` variante pictos ; CPA / ROAS → variante pilules ; « vs N-1 » → variante deltas ; que des chiffres → `heatmap` |
| trois blocs de chiffres côte à côte | `kpi_grid`, `stats`, `big_numbers` |
| trois ou quatre blocs de texte côte à côte | `card_grid`, `phase_cards`, `content_cards`, `process` |
| deux blocs face à face | `compare_cards`, `before_after` (si « avant / après »), `do_dont` |
| liste à puces | `chevrons`, `takeaways`, `numbered_list`, `checklist` |
| paragraphe long | `analysis_block`, `content_card`, `callout` |
| une grande image | `browser` / `laptop` / `phone` (capture d'écran), `gallery` |
| plusieurs petites images | `logo_wall`, `logo_grid`, `client_ticker` |
| plusieurs images moyennes | `gallery`, `ad_scoreboard` (visuels de campagne) |
| graphique Sheets | `chart_*` charté, ou graphique Sheets natif relié |
| « Sources : … » en bas | `source_note` |
| flèches | `process`, `chevrons`, `timeline_arrow` |

`slide_level` ajoute des alternatives lues dans le vocabulaire de la slide
(« équipe » → `team_grid`, « objectifs / dispositif » → `media_plan`,
« planning » → `timeline`, « atelier » → `ranked_bars`…) qui peuvent
remplacer plusieurs blocs d'un coup. Ce sont des heuristiques : les
`signals` sont renvoyés pour trancher autrement, et un bloc peut mériter un
composant qui n'est pas listé. Le titre, lui, va dans le placeholder
`TITLE` du layout cible, pas dans un composant.

## 4. Reconstruire sur le layout cible

Le layout change presque toujours : titre plus haut, pied de page, marges.

```
list_layouts(new_deck)  →  layouts[i].content_area = {x, y, w, h}
create_slide_from_layout(new_deck, "Titre et contenu", fills={"TITLE": "…"})
insert_component(new_deck, slide, "kpi_grid", props, x_pt=area.x, y_pt=area.y, width_pt=area.w)
```

`content_area` est la zone libre du layout (la boîte des placeholders de
corps, sinon la bande entre le titre et le pied de page). Les `zone` des
blocs sources donnent leurs proportions : un bloc qui occupait le tiers
supérieur de l'ancienne slide prend le tiers supérieur de `content_area`.
Les composants renvoient leur hauteur, ce qui permet d'empiler les blocs
suivants ; `screenshot` puis `overlap_check` valident la slide.

## Ce qui n'est pas pris en charge

- Les vidéos, les formes libres et le WordArt ne sont pas moissonnés :
  `inspect_slide` les signale, ils se refont à la main ou se laissent.
- Les images sont partagées « toute personne ayant le lien » dans le dossier
  choisi, condition pour que Slides puisse les charger ; choisir le dossier
  en conséquence.
