# Point de titre, entonnoir d'étages, fan-out, schémas face à face : design

Date : 2026-10-06. Six maquettes de Loïc (formation SEO / GEO, Institut Pasteur) comparées au
catalogue : une existe déjà (« Sécuriser » = `card` dark + `dot`), deux sont des variantes
(`stack` numéroté, `hub_spoke` à un satellite), trois demandent du neuf. Constat en passant : le
point du `card` est placé 2,5 pt trop haut (centre à y + 11 au lieu de y + 13,4 pour des
capitales 11 pt) et trop collé au titre (4,5 pt au lieu d'environ un diamètre).

## Mesures faites en direct (deck de test)

- Capitales Barlow dans une zone de texte Google, ancrée en haut : hauteur = 0,7 × taille,
  centre à 7 + 0,6 × taille sous le haut de la zone (mesuré à 11, 14, 16, 18, 24 pt, écart
  ≤ 0,2 pt).
- Maquette « Sécuriser » : point de diamètre = hauteur des capitales, centré sur elles, écart
  point → texte ≈ 0,9 diamètre ; titre ≈ 15 pt (rapport 1,38 avec le corps 11 pt), en casse
  normale.
- `TRAPEZOID` : retrait = 0,25 × min(l, h) du cadre rendu (Slides normalise la taille et met
  tout dans l'échelle : impossible d'écraser la forme pour changer la pente). Le retournement
  (`scaleY` négatif) marche. `FLOW_CHART_MANUAL_OPERATION` a un retrait fixe de 20 % de la
  largeur. Aucune ne donne la pente de la maquette : un étage d'entonnoir sera un rectangle et
  deux triangles rectangles retournés.
- `createLine` en catégorie `CURVED` trace un S à tangentes horizontales entre les deux bouts,
  y compris vers le haut avec `scaleY` négatif : exactement les liens du fan-out.
- Rotation d'une zone de texte par la matrice (cos, −sin, sin, cos) autour de son centre :
  correcte (lecture de bas en haut à −90°).

## Lot A — point, carte, pile numérotée

**A1. `title_dot(x, top, size, d=None)`** (`builtin.py`) : l'op du point placé devant un titre
dont la zone de texte commence à `top` ; diamètre `d` = 0,7 × taille par défaut, centre sur les
capitales (7 + 0,6 × taille) ; renvoie aussi l'avance (d + 0,9 d) pour placer le titre. Utilisé
par `card` et `media_plan` (qui garde son point de 10 pt, seul le centrage change).

**A2. `card`, titre comme la maquette** : le titre n'est plus forcé en capitales, il passe à
15 pt (gras, couleur de tête du variant : menthe sur dark), hauteur estimée à 15 pt ; le point le
suit (10,5 pt, centré, écart 9,5 pt). Libellé, gros chiffre, numéro et corps inchangés.

**A3. `stack`** :
- `numbered` (bool) : « 01 », « 02 »… à gauche de chaque couche ; `num` dans un item force le
  texte. Sur fond sombre le numéro alterne menthe / acide, sinon encre (maquette 2).
- `palette` : `navy` (défaut actuel : navy, navy 2, gris) ou `brand` (navy, menthe, navy,
  acide).
- Coins arrondis (`ROUND_RECTANGLE`), règle charte.

## Lot B — `hub_spoke` enrichi, `diagram_compare`

**B1. `hub_spoke`** :
- satellites `{label, hl, logo, logo_url}` : avec un logo, disque blanc et logo contenu
  (56 % du diamètre) à la place du libellé ;
- `hub_shape` (`box` | `disc`), `hub_fill` (rôle, défaut accent ; texte clair sur fond
  sombre), `hub_logo` (asset, au-dessus du texte du bloc) ;
- `link_dash`, `link_color`, `link_weight` ;
- `dark` : sur fond sombre, liens `muted`, satellites blancs sans contour (hl → contour accent) ;
- un seul satellite : schéma en ligne, bloc à gauche, satellite à droite (maquette 4).

**B2. `diagram_compare`** (nouveau, `diagrams.py`) : deux ou trois panneaux arrondis côte à côte,
chacun `{ground: light | dark, eyebrow, component, props, text}` : titre en capitales (encre /
menthe), un composant du catalogue dessiné dans le panneau à hauteur commune `diagram_h`, texte
markdown dessous (texte / blanc). Un panneau sombre passe `dark: true` au composant qui a cette
prop, s'il ne la fixe pas. Hauteurs égalisées. Maquette 5 : `hub_spoke` à un satellite à gauche,
`hub_spoke` à logos à droite.

## Lot C — `funnel_stages` (nouveau, `diagrams.py`)

Entonnoir qualitatif TOFU / MOFU / BOFU (maquette 1), distinct de `funnel` (données) :
- `stages*` `[{title, sub, text, note, note_sub, fill, color}]` : titre gras, sous-titre
  italique, ligne grasse, centrés ; hauteur de l'étage selon son texte (min 44 pt).
- Étages jointifs : largeur linéaire de `top_ratio` (1) à `bottom_ratio` (0,4) de la colonne,
  chaque étage = rectangle + deux triangles rectangles retournés, sans contour.
- Fonds par défaut : acide, gris, menthe, navy, navy 2 ; texte d'après le fond.
- Colonne de lecture à droite (`note` gras 14 pt, `note_sub` gris), centrée sur chaque étage.
- `stage_header` / `note_header` : titres de colonnes en capitales espacées, gris.
- `axis` : filet vertical gris fléché vers le bas, libellé tourné à −90° à sa gauche.
- `conclusion` `{title, text}` : bloc navy arrondi sous l'entonnoir, titre menthe 15 pt, texte
  blanc, centrés.

`draw` gagne `flip` (`x`, `y`, `xy`) sur `box` et `rotate` (degrés) sur `box` / `text`.

## Lot D — `fan_out` (nouveau, `flow.py`) et `tree` vertical

- `draw` : `line` accepte `curve: true` (catégorie `CURVED`).
- `tree` `layout: vertical` : racine en haut (`{label, sub}`, accent), enfants empilés en
  retrait, filet vertical et départs horizontaux (arborescence de fichiers) ; `bus` reste le
  défaut.
- `fan_out` : `source*` (texte, `==x==` en menthe gras) dans un bloc navy, point menthe sur son
  bord droit, liens courbes menthe vers `branches*` (cases blanches à filet gris), flèche puis
  `target` optionnel `{root, children}` dessiné en `tree` vertical ; `source_label`,
  `branches_label`, `target_label` en capitales espacées au-dessus des colonnes.

## Catalogue, docs, tests

- `uses.py` (phrases nouvelles et mises à jour), `intents.py` (`funnel_stages` → étapes,
  structure ; `fan_out` → structure, étapes ; `diagram_compare` → comparer, structure ;
  mots-clés TOFU / fan-out / fragile en fin de `KEYWORDS`), `variants.py`.
- `docs/components.md`, `CHANGELOG.md` (Unreleased).
- Tests : `tests/test_components11.py` (point centré sur les capitales, titre de carte,
  numéros de pile, satellites à logo, un satellite en ligne, panneaux et `dark` transmis,
  étages jointifs, lien courbe, arbre vertical), `test_draw.py` (flip, rotate, curve).
- Deck catalogue rafraîchi à la fin : `card`, `card_grid`, `media_plan`, `stack`, `hub_spoke`,
  `tree` et les trois nouveaux, variantes comprises, ordre alphabétique.

Hors périmètre : pas de nouveau rôle de thème (liens sombres en `muted`), pas de déploiement
sans accord.
