# Bilan sync: a deck that follows its spreadsheet

A recurring bilan (monthly, quarterly) keeps its figures in a spreadsheet. The
deck is built once; every period afterwards, `sync_deck` brings it in line with
the spreadsheet in one call: KPI texts, tables, visuals and linked charts are
updated **in place** — every element keeps its id, place and look.

What links the two is a tab of the spreadsheet named **« Liaisons »**: one row
per deck element, saying where its content comes from. gslide-mcp only reads the
spreadsheet; the tab and the data are written with the Sheets MCP.

## The « Liaisons » tab

First row = headers (any order, case and accents ignored), then one row per
binding. An empty row, or a row whose `type` starts with `#`, is ignored.

| type | élément | source | options |
|---|---|---|---|
| texte | `kpi_depenses_value_1` | `bilan_depenses` | |
| texte | `kpi_depenses_delta_1` | `'Synthèse'!C4` | `delta=auto` |
| texte | `kpi_cpa_delta_1` | `'Synthèse'!C7` | `delta=inverse` |
| tableau | `regies_table_1` | `bilan_regies` | `style=slides; rows=fit` |
| tableau | `yt_top_table_1` | `bilan_youtube` | `rows=fit; columns=fit` |
| image | `yt_top_slot_1` | `'Visuels'!B2` | `fit=inside` |

- **type** — `texte` (a shape: KPI value, delta, date, sentence), `tableau` (a
  table), `image` (an image, typically a slot). `text`, `table` are accepted.
- **élément** — the element's id in the deck. Readable ids come from
  `insert_component(…, name="…")` (`<name>_<role>_<n>`, listed in `ids_by_role`)
  or `rename_element` on a hand-designed deck. A Drive copy of the deck
  (`clone_deck`, next month's bilan) keeps the ids, so the same tab serves every
  copy.
- **source** — a **named range** (preferred: it follows the data when rows are
  inserted) or A1 with the sheet (`'Données'!B4:F12`). For `texte`, one cell,
  written as Sheets displays it (`46 811 €`, `+8 %`). For `tableau`, the whole
  table, header included. For `image`, one cell holding a URL, an asset name
  (`list_assets`) or `drive:<file id>`; an empty cell puts the empty-slot
  placeholder back.
- **options** — `key=value` pairs separated by `;`:
  - `texte`: `delta` = `auto` (default: signed values in a variation keep their
    sign's colour), `true`, `false`, `inverse` (lower is better: CPC, CPA).
  - `tableau`: `style` = `slides` (default) | `sheets` | `charter`; `rows` and
    `columns` = `keep` (default) | `fit`; `row_height` = pt. Same meaning as
    `sync_table`.
  - `image`: `fit` = `inside` (default) | `crop`.

## Creating the tab (Sheets MCP)

1. `manage_sheet` (`add`, title `Liaisons`).
2. `write_values` from `A1`: the header row, then one row per binding.
3. `manage_range`:
   - `named_range` for each source block (`bilan_regies` = `'Données'!A1:F8`…);
   - `data_validation` `one_of_list` (`texte`, `tableau`, `image`) on column A;
   - `protected_range` with `warning_only: true` on the tab, so a hand edit is
     a deliberate one.

## Running it

- `sync_deck(deck, dry_run=True)` reads the tab, checks every binding (element
  present and of the right kind, range readable, image source usable) and
  reports what would change, writing nothing.
- `sync_deck(deck)` then writes: tables first (their rows and columns may
  change), then visuals and texts, then refreshes the linked Sheets charts.
- `spreadsheet` can be left out when the deck has linked charts: their
  spreadsheet is the bilan's. Otherwise pass its id or URL.
- `only=["tableau"]` (or `texte`, `image`) runs one kind of binding.

Everything is checked before the first write: a binding in error stops the run
and is reported with its row number in the tab.
