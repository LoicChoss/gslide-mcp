# Template et dossier par défaut : design

Date : 2026-10-02. Objectif : quand l'utilisateur ne donne aucune prez de référence,
le MCP part d'un template réglé une fois pour toutes dans l'extension Claude Desktop
et range la nouvelle prez dans un dossier Drive réglé de la même façon. Serveur local
seulement : le connecteur hébergé ne prend qu'une URL dans Claude Desktop, il n'a pas
de réglage par personne.

## 1. Réglages

Deux champs facultatifs dans `user_config` de `manifest.json`, chacun id ou URL :

| Champ | Titre | Variable |
|---|---|---|
| `default_template` | Template par défaut (Google Slides) | `GSLIDES_MCP_DEFAULT_TEMPLATE` |
| `default_folder` | Dossier de rangement par défaut (Drive) | `GSLIDES_MCP_DEFAULT_FOLDER` |

Un id de dossier suffit à Drive pour ranger un fichier ; une URL
`drive.google.com/drive/folders/<id>` ou `docs.google.com/presentation/d/<id>` est
ramenée à son id par `parse_drive_id` / `parse_pres_id`, comme le champ « Assets folder ».
Valeur vide ou absente = réglage absent. Pas de valeur codée en dur, pas de
documentation dans `docs/hosting.md`.

## 2. Outil `get_defaults()`

Lecture seule (`READ_ONLY`). Lit les deux variables et vérifie chaque réglage présent
par un `files.get` Drive (`supportsAllDrives=True`).

```json
{
  "template": {"id": "…", "url": "https://docs.google.com/presentation/d/…/edit", "title": "…"},
  "folder": {"id": "…", "name": "…"}
}
```

- Réglage absent : la clé vaut `null`.
- Réglage présent mais inutilisable (introuvable, non partagé, mauvais type : le template
  n'est pas une présentation, le dossier n'est pas un dossier) :
  `{"id": "…", "error": "<raison>"}` ; l'outil ne lève pas d'exception, pour que Claude
  dise « le template par défaut est inaccessible, vérifie le réglage de l'extension ».

## 3. Rangement des nouvelles prez

Un module partagé lit les réglages (`defaults.template_id()`, `defaults.folder_id()`,
chacun `None` si absent). Ordre de priorité quand un outil crée une prez :
dossier passé explicitement > dossier par défaut (dans les cas ci-dessous) > comportement actuel.

| Cas, sans dossier précisé | Aujourd'hui | Avec dossier par défaut |
|---|---|---|
| `clone_deck` dont `src` est le template par défaut | à côté du template | dossier par défaut, `placed: "default_folder"` |
| `clone_deck` d'un autre deck | à côté de la source | inchangé |
| `create_presentation` | racine de Mon Drive | dossier par défaut |
| `assemble_from_template` | racine de Mon Drive | dossier par défaut |

Sans dossier par défaut réglé, rien ne change. La comparaison « `src` est le template
par défaut » se fait sur les ids, après analyse des URL. Si le dossier par défaut refuse
le fichier (droits), chaque outil garde sa façon actuelle d'échouer ou de se rabattre
(`clone_deck` : copie dans Mon Drive + `folder_note` ; `assemble_from_template` :
`folder_move: "failed: …"` ; `create_presentation` : erreur claire de `_check_folder`).
Les docstrings disent la règle, pour que Claude la connaisse sans lire le skill.

## 4. Skill `gslides-prez`

- Étape 0 : pas d'URL de deck type → `get_defaults()`. Template réglé et accessible :
  l'annoncer en une ligne (« je pars du template *titre*, la prez sera rangée dans
  *dossier* ») et continuer avec `list_layouts` / `screenshot_layouts`. Template absent
  ou en erreur : demander l'URL comme aujourd'hui (et relayer l'erreur s'il y en a une).
- Question « Où ranger le deck ? » : proposer le dossier par défaut s'il est réglé et
  qu'on part du template par défaut ou d'un deck neuf ; sinon les défauts actuels.
- Référence rapide : `get_defaults` dans la ligne Cadrage.

## 5. Tests

- `get_defaults` : rien de réglé ; id ; URL ; fichier introuvable (HttpError 404) ;
  template qui n'est pas une présentation ; dossier qui n'est pas un dossier.
- `clone_deck` : template par défaut sans dossier → dossier par défaut ; même chose avec
  `parent_folder_id` → le dossier donné ; autre deck → à côté de la source ; pas de
  dossier par défaut → comportement actuel.
- `create_presentation` et `assemble_from_template` : dossier par défaut utilisé quand
  aucun dossier n'est donné, ignoré quand un dossier est donné.

Services Google simulés comme dans les tests existants ; pas d'appel réseau.
