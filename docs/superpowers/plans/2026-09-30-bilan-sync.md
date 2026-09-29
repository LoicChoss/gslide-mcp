# Bilan sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** « Mets à jour le bilan » becomes one call: a « Liaisons » tab in the bilan's spreadsheet says which deck element follows which range, and `sync_deck` updates texts, tables, images and linked charts in place, keeping every element's id, frame and style.

**Architecture:** Three phases, each shippable on its own. Phase 1 adds the building blocks (image replacement that keeps the id, element renaming, table sizing, readable ids per role, real image slots). Phase 2 makes an existing table follow a spreadsheet range (`sync_table`), including tables with a row of images (ad scoreboards). Phase 3 reads the « Liaisons » tab and runs everything (`sync_deck`). gslide-mcp reads spreadsheets itself, read-only, like it already refreshes linked charts; Péri Sheets MCP writes the tab.

**Tech Stack:** Python 3.11, fastmcp 3, Google Slides API v1, Google Sheets API v4 (read-only, through the `drive` scope already granted), Pillow for generated placeholders, pytest (`uv run --no-sync pytest -q`).

Origin: Loïc's Apps Script bilan updater (tables from ranges with Sheets formatting, images replaced by id, row count synced, charts refreshed) and the 2026-09-29 feedback (`refill_text`, donut, Drive folders).

## Decisions (2026-09-30)

- Only Claude runs updates: no Apps Script menu, no support for the old « Liste Tableaux - MAJ » / « Liste Images - MAJ » tabs.
- gslide-mcp reads the spreadsheet itself (values, formats, named ranges); Péri Sheets MCP creates and edits the « Liaisons » tab and the data. No change needed on the Sheets MCP (pending asks there stay: `null` in `write_values`, folder branch).
- `sync_table` style defaults to `slides` (the deck's look); `sheets` (copy the source formatting) and `charter` (theme table style) are options.
- Bindings point to named ranges when possible (they follow the data when rows are inserted); A1 ranges accepted.
- Tests and live checks run on a new deck and spreadsheet of our own, never on the Bilan CFA template.
- The old phase 4 (auto-suggested bindings, Apps Script parity) is dropped.

## API behaviours to verify live (each task says where)

- V1 (verified 2026-09-30 on the test deck): `replaceImage` works in the same batch right after `createImage`. `createImage` shrinks the element to the picture's aspect (`screen-demo` in 300 × 100 → 177.5 × 100), hence the placeholder at the box's aspect. After `replaceImage` the element's `size` is the new picture's natural size: CENTER_CROP keeps the frame (non-uniform scale + crop), CENTER_INSIDE shrinks the element to the picture (uniform scale, centred — 100 × 100 → 100 × 56.3). Restoring the frame's transform just before a CENTER_INSIDE replacement gives the frame back exactly. So a slot stores its frame in its alt-text description (`slot:x,y,w,h`, pt) and every replacement restores it first. `replaceImage` also clears the alt text: the frame is written again after it, in the same batch (verified: restore → replace → alt text gives 99.4 × 56 centred in a 166.7 × 56 frame, alt text kept).
- V2 (verified 2026-09-30): `duplicateObject` puts the copy **on top** of the slide; `SEND_BACKWARD` moves an element one step back. So a rename is one batch: duplicate, delete, then as many SEND_BACKWARD as computed from the original order.
- V3 (verified 2026-09-30): `insertTableRows` copies the reference row's cell fill, text style and alignment. So new data rows are inserted **below the last data row** (never next to a total, whose look they would take); a table that grows pushes down what is under it: the component's own elements (same name prefix) are moved.
- V4: `spreadsheets.get` with `ranges` + `includeGridData` works with the `drive` scope, locally and hosted.
- V5: whether a table's `tableRows[].rowHeight` read back reflects rows grown by their text (needed to realign images over a row).

Live checks use the pattern in memory « live-test-via-connector »: repo code run against a real `get_page` JSON with a stub service, requests sent with the connector's `batch_apply`, then `screenshot`; after a release, the hosted connector runs the new tools directly.

---

## Phase 1 — building blocks

### Task 1: `refill_text` empty cells and merged cells
- Modify: `src/gslides_mcp/tools/refill.py`
- Behaviour: an empty `text` on a table cell writes one space carrying the cell's style (an empty cell falls back to Slides' 18 pt default paragraph and the row grows, the trap `draw` already avoids); on a shape it still just clears. A cell covered by a merge (inside another cell's `rowSpan` / `columnSpan`) is refused before any write, naming the head cell to write instead.
- Test: `tests/test_refill.py` — `""` on a cell gives deleteText + insertText " " + the kept style; `""` on a shape gives deleteText only; a covered cell raises « merged into (r, c) » and nothing is sent.
- Commit: `fix(refill_text): empty cells keep a styled space, merged cells are refused`

### Task 2: `resize_table`
- Modify: `src/gslides_mcp/tools/tables.py`; `tests/test_annotations.py` (IDEMPOTENT list)
- Behaviour: new tool `resize_table(presentation, table_id, row_height_pt=None, rows=None, column_widths_pt=None)`. Row height is a minimum (`updateTableRowProperties.minRowHeight`) on the given rows or all; column widths is one value per column, `null` keeps a column (`updateTableColumnProperties`). Refuses widths under 32 pt (Slides minimum), a list of the wrong length, rows out of range. Docstring: a row never shrinks below its text plus Google's 7.2 pt padding (≈ 26 pt at 10.5 pt).
- Test: `tests/test_tables.py` — requests and fields; validation errors send nothing.
- Commit: `feat(tables): resize_table sets row heights and column widths of an existing table`

### Task 3: generated slot placeholders in the assets store
- Modify: `src/gslides_mcp/assets.py`
- Behaviour: an asset ref `slot:<w>x<h>:<fill>:<line>` (pixels at 4 px per pt, long side capped at 1600 px, hex colours) is generated with Pillow — flat fill, dashed 1 pt border — uploaded once to the assets folder as `slot-<w>x<h>-<fill>-<line>.png` (shared like tinted variants) and cached; `asset_size` answers from the ref without a download. A helper `slot_ref(w_pt, h_pt, fill_hex, line_hex)` builds the ref. Server-generated file, so allowed in hosted mode.
- Test: `tests/test_assets.py` — generated PNG has the ref's size, border pixels in the line colour, centre in the fill colour; second call hits the cache; `asset_size` makes no Drive call.
- Commit: `feat(assets): generated slot placeholders at any aspect ratio`

### Task 4: `draw` image slots
- Modify: `src/gslides_mcp/draw.py` (image op), `docs/components.md` (ops list)
- Behaviour: an image op with `slot: true` is created from the slot placeholder of its exact box (fill `surface`, line `divider`, overridable with `slot_fill` / `slot_line`), so the element's frame is the box; its alt-text description records the frame (`slot:x,y,w,h`, page pt); when the op also has `asset` / `url`, a `replaceImage` in the same batch puts the picture in with `fit` (`inside` → CENTER_INSIDE, default; `crop` → CENTER_CROP). Without a source the placeholder stays: an empty slot that `replace_images` can fill later. `summarize_deck` ignores `slot:` alt texts when it guesses a slide's topic.
- Test: `tests/test_draw.py` — slot without source: one createImage from the slot asset and the alt text with the frame; with source: then replaceImage on the same id with the right method; `summarize_deck` topic skips `slot:`.
- Live check V1 on the test deck (create the test deck here: « gslides-mcp · test bilan sync · 2026-09 », plus its spreadsheet, in the same Drive folder).
- Commit: `feat(draw): image slots keep their frame and take any picture later`

### Task 5: `replace_images`
- Modify: `src/gslides_mcp/tools/images.py`; `tests/test_annotations.py` (IDEMPOTENT)
- Behaviour: new tool `replace_images(presentation, images=[{element, source, fit?}])`, one batch: for each image, its frame (the `slot:` alt text when the current box still sits inside it, else the current box, then recorded in the alt text) is restored with `updatePageElementTransform` when the box differs, then `replaceImage` — the element keeps its id, frame and z-order, month after month, even with CENTER_INSIDE. A rotated or sheared element is replaced without restoring (reported). `source` is a URL (http/https, ≤ 2 kB, checked to serve PNG / JPEG / GIF with the existing raster probe), an assets-folder name or `drive:<id>`; empty or null puts the slot placeholder back (sized from the element's frame). Refuses an element that is not an image (a shape or table: say to re-insert it as a slot), a duplicate element, an unreachable or non-raster URL — all before writing, naming the element.
- Test: `tests/test_images.py` (new) — requests per source kind; empty source → slot asset with CENTER_CROP; refusals send nothing (raster probe monkeypatched).
- Commit: `feat(images): replace_images swaps pictures and keeps each element`

### Task 6: `rename_element`
- Modify: `src/gslides_mcp/tools/layout.py`; `tests/conftest.py` (fake: `duplicateObject` and `deleteObject` on page elements, dup placed on top); `tests/test_annotations.py`
- Behaviour: new tool `rename_element(presentation, renames=[{element, new_id}])`: `duplicateObject` with the id map then `deleteObject` of the original, in one batch; then the z-order is restored (read the page back, `SEND_BACKWARD` / `BRING_FORWARD` the renamed element to its former index). Refuses: invalid id, id already used anywhere in the presentation, element inside a group, element missing. Docstring: comments anchored on the element and links pointing to it are lost; a linked chart keeps its link.
- Test: `tests/test_layout_*` or new `tests/test_rename.py` — requests, z-order moves computed from the fake, refusals.
- Live check V2.
- Commit: `feat(layout): rename_element gives an element a readable id and keeps its place`

### Task 7: readable ids per role on `insert_component` and `draw`
- Modify: `src/gslides_mcp/draw.py` (`_Canvas.new_id` knows the current op's role; `ops_to_requests(..., named=False, roles_out=None)`), `src/gslides_mcp/tools/components.py`
- Behaviour: `insert_component(..., name="yt_top")` names every element `<name>_<role>_<n>` (role from the op, else the op kind: `yt_top_table_1`, `yt_top_slot_1`, `yt_top_slot_2`, `yt_top_value_1`) and the group `<name>`; `name` must match `[A-Za-z][A-Za-z0-9_-]{4,29}` and not be used in the deck yet (refused with the element found). Without `name`, ids stay as today. The result gains `ids_by_role` (always), so the model can write bindings from it.
- Test: `tests/test_component_tools.py` — named ids and group id, `ids_by_role`, collision refused, unnamed ids unchanged; `tests/test_draw.py` — per-role counters.
- Commit: `feat(components): name a component to get readable ids per role`

### Task 8: `ad_scoreboard` with slots
- Modify: `src/gslides_mcp/components/reporting.py`, `components/variants.py` if a variant mentions the dashed box
- Behaviour: every visual cell is an image slot (role `slot`, `fit: inside`), with or without a picture; no more dashed shape. With `name`, the slots are `<name>_slot_1…n` in column order.
- Test: `tests/test_components7.py` — update the scoreboard test: one slot per ad, the ones with a picture carry it.
- Commit: `feat(ad_scoreboard): every visual cell is a slot`

### Task 9: `swap_client` keeps the logo element
- Modify: `src/gslides_mcp/tools/semantic.py`
- Behaviour: the logo swap is one `replaceImage` (CENTER_INSIDE) instead of delete + create: same id, frame and z-order. The result reports `element` instead of `deleted_id`.
- Test: new test in `tests/test_semantic.py` (or the closest existing file) — a replaceImage on the logo id, no deleteObject.
- Commit: `fix(swap_client): replace the logo in place`

### Task 10: Phase 1 release
- Modify: `README.md` (tool table), `CHANGELOG.md` (Unreleased), `.claude/skills/gslides-prez/SKILL.md` (Remplissage mode: `rename_element` for readable ids, `replace_images` for visuals, `resize_table`; construction: `insert_component(name=…)` on decks meant to be updated) + zip, `docs/components.md`
- Verify: full test suite; live checks V1 and V2 recorded in `docs/components.md` (« What the Slides API imposes »).
- Push `main` (Coolify redeploys).
- Commit: `docs: phase 1 of bilan sync`

---

## Phase 2 — tables that follow a range

### Task 11: spreadsheet reader
- Create: `src/gslides_mcp/sheets_source.py`; Modify: `src/gslides_mcp/auth.py` (`sheets_service()`, per user in hosted mode like the others); `tests/conftest.py` (fake Sheets service)
- Behaviour: `read_cells(spreadsheet, range)` → grid of cells `{text (formatted value), is_number, fill, color, bold, italic, underline, strikethrough, font, size, h_align, v_align}` plus merges, from `spreadsheets.get(ranges=…, includeGridData=true, fields=…)`. `range` is A1 with the sheet (`'Données'!B4:F12`) or a named range. Horizontal `general` resolves like Sheets: numbers and dates right, text left. Accepts a spreadsheet id or URL.
- Test: `tests/test_sheets_source.py` — formatted values, formats, `general` alignment, named range passed through, merges.
- Live check V4.
- Commit: `feat(sheets): read a range with its formatting`

### Task 12: `sync_table` — values in place
- Create: `src/gslides_mcp/tools/sync.py`; Modify: `src/gslides_mcp/tools/__init__.py`, `tests/test_annotations.py`
- Behaviour: `sync_table(presentation, table, spreadsheet, range, style="slides", rows="keep", columns="keep", row_height_pt=None, dry_run=False)`. Cell by cell with the refill logic of Task 1 (style kept, empty → styled space, merged cells skipped, variation colours by sign). Dimension mismatch with `keep`: writes the overlap and reports what was left out. `dry_run` returns the changed cells (old → new) and the dimension report without writing. One batch per table.
- Test: `tests/test_sync_table.py` — values mapped, styles kept, report, dry run writes nothing.
- Commit: `feat(sync): sync_table writes a range into an existing table`

### Task 13: `sync_table` styles `sheets` and `charter`
- Modify: `src/gslides_mcp/tools/sync.py`
- Behaviour: `sheets` copies each cell's fill, text colour, weight, italics, underline, strikethrough, font, size and alignments from the source; `charter` applies the `table` component's look (header fill, banding, first column bold, previous-period columns muted, variation columns coloured) using its header detection.
- Test: fill / text style / alignment requests per mode.
- Commit: `feat(sync): sync_table can copy the sheet's formatting or apply the charter`

### Task 14: `rows="fit"`
- Modify: `src/gslides_mcp/tools/sync.py`
- Behaviour: rows are added or removed just before the last row, so the header and the total row keep their place and style; the new rows take the style of the row above (per V3: inherited from `insertTableRows`, or copied cell by cell when not). A removed row holding a merge is refused.
- Test: insert / delete requests before the last row; style of new rows.
- Live check V3.
- Commit: `feat(sync): sync_table adds or removes rows to match the range`

### Task 15: image row in `table`, `ad_scoreboard` built on it
- Modify: `src/gslides_mcp/components/builtin.py` (`table`: prop `image_row: {row, images, height, fit}`, images as slots over that row's cells, role `slot`; prop `one_line_header` shrinking header text to one line so the row height stays put), `components/reporting.py` (`ad_scoreboard` renders through `table` with `image_row`), `components/variants.py` (`table` variant « une colonne par élément, vignette en tête »), `components/uses.py`
- Test: `tests/test_components*.py` — slots aligned on the cells of the image row, scoreboard output unchanged apart from the slots, one-line header.
- Commit: `feat(table): image row of slots; ad_scoreboard uses it`

### Task 16: `columns="fit"` and slot realignment
- Modify: `src/gslides_mcp/tools/sync.py`
- Behaviour: for a named table (`<name>_table_1`), columns are added or removed at the end, data columns share the width left by the first column, slots `<name>_slot_k` are created (as empty slots) or deleted to match, then every slot is moved onto its column and row from the widths and row heights read back (V5; fallback: minimum row heights). Unnamed tables refuse `columns="fit"` with the fix (`rename_element` / insert with `name`).
- Test: column requests, slot create / delete / move requests.
- Live check V5.
- Commit: `feat(sync): sync_table fits columns and realigns image slots`

### Task 17: Phase 2 release
- Modify: skill (table from a spreadsheet → `sync_table` instead of delete + re-insert; recurring bilan step), `docs/sheets-charts.md`, README, CHANGELOG, skill zip
- Verify: suite; live on the test deck: a table vs N-1 with a total row growing from 4 to 6 rows, a scoreboard going from 3 to 4 ads, style `sheets` against the source.
- Push `main`.
- Commit: `docs: phase 2 of bilan sync`

---

## Phase 3 — the bilan in one call

### Task 18: « Liaisons » tab format
- Create: `docs/bilan-sync.md`
- Content: one « Liaisons » tab per bilan spreadsheet; header `type | élément | source | options`; `type` = `texte`, `tableau`, `image`; `élément` = the deck element id (readable ids from Phase 1; a Drive copy of the deck keeps them, so next month's copy uses the same tab); `source` = named range (preferred) or `'Feuille'!A1:B2`; for `texte` one cell, for `image` one cell holding a URL, an asset name or `drive:<id>` (empty = slot placeholder back); `options` = `key=value` pairs separated by `;` (`style`, `rows`, `columns`, `row_height`, `fit`, `delta`). How to create it with Péri Sheets MCP: `manage_sheet add`, `write_values`, `manage_range` (`named_range` per source, `data_validation one_of_list` on `type`, `protected_range warning_only` on the tab).
- Commit: `docs: bilan sync bindings format`

### Task 19: bindings reader
- Modify: `src/gslides_mcp/tools/sync.py` (or `bindings.py` if it grows)
- Behaviour: reads the « Liaisons » tab through `sheets_source`, parses and validates each row (type, source form, options), keeps row numbers for the report; missing tab → clear error with the format's doc link.
- Test: parsing, validation errors per row, options.
- Commit: `feat(sync): read the Liaisons tab`

### Task 20: `sync_deck`
- Modify: `src/gslides_mcp/tools/sync.py`, `tests/test_annotations.py`
- Behaviour: `sync_deck(presentation, spreadsheet=None, dry_run=False, only=None)`. Spreadsheet: given, or the single spreadsheet behind the deck's linked charts (`list_sheets_charts`), else refused asking for it. Checks every binding before writing (element exists and has the right kind, range readable, image source usable); then tables (`sync_table`), images (`replace_images`), texts (`refill_text` with sign colours), and refreshes linked charts. Report per binding: done / skipped / error with the row number; dry run reports without writing.
- Test: `tests/test_sync_deck.py` — order, inference from charts, dry run, per-binding report, refusal before any write.
- Commit: `feat(sync): sync_deck updates a bilan from its Liaisons tab`

### Task 21: skill
- Modify: `.claude/skills/gslides-prez/SKILL.md` + zip
- Content: cadrage questions only for a bilan / deck meant to be updated — updated regularly? (yes → linked charts, `insert_component(name=…)`, a « Liaisons » tab built with the deck); tables keep the deck's look or the sheet's? rows or columns that vary month to month (ads, campaigns)?; where the ad visuals come from (platform URLs expire: take them into Drive). Build step: name components, create the tab with Péri Sheets MCP (named ranges, validation, protection). Recurring bilan mode: new month = `clone_deck` of last month (ids kept) → write the month's data → `sync_deck(dry_run=True)` → show the report → `sync_deck` → screenshots. Designed-deck mode: `rename_element` to readable ids, then the tab.
- Commit: `skill: bilan sync`

### Task 22: end-to-end and release
- Verify: on the test deck and spreadsheet, a small bilan (KPI texts with variations, table vs N-1 with total, scoreboard with visuals, one linked chart), its « Liaisons » tab, then a new month: data changed with Péri Sheets MCP, `sync_deck` dry run, run, screenshots, second run changes nothing.
- Modify: README, CHANGELOG (0.8.0), `pyproject.toml` / `manifest.json` version, `dist/` bundle, memory note.
- Push `main`.
- Commit: `Release 0.8.0: bilan sync`
