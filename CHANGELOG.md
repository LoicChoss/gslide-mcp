# Changelog

All notable changes to gslide-mcp. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/) (0.x: minor bumps may change tool signatures).

## [Unreleased]

### Added

- **Hosted, multi-user mode** ([docs/hosting.md](docs/hosting.md)): `GSLIDES_MCP_TRANSPORT=http` serves streamable HTTP at `/mcp`; the server runs the OAuth flow itself (Google, Web application client) so a person only adds the URL in Claude and signs in with their Google account. Every call uses that person's token; there is no fallback to a token on disk. `Dockerfile`, CI (tests and image build); Coolify builds and deploys on each push to main.
- Cross-deck copy through `scripts.run` (`GSLIDES_MCP_APPSCRIPT_ID`, script 0.6 `api()`, which also serves `chart_png` for google-sheets-mcp), running as the caller; the hosted server refuses the web app, which runs as its deployer.
- `insert_image_local`: `image_base64`. The assets folder defaults to the team folder (`GSLIDES_MCP_ASSETS_FOLDER` still overrides it). On the hosted server `path` is refused and `export_pres` returns a Google download `url`.

### Changed

- Built on `fastmcp` 3; sync tools run in a thread pool, so each thread keeps its own API clients (httplib2 is not thread-safe) and token.json is read once.

## [0.7.0] — 2026-09-25

### Added

- **Training and audit diagrams** (from the SEO training deck): `cocon` (semantic cocoon: target page, child pages, action nodes; arc or ring), `cycle` (loop of steps, 2 × 2 or ring), `formula` (2 to 5 concept boxes joined by an operator, then the result), `persona_card` (identity, context, brands, gauges, devices, expectations / brakes, tag).
- `draw`: a box narrower than 48 pt or lower than 30 pt (numbered discs, tiny tiles) gets its text in a centred transparent overlay, so Google's fixed 7.2 pt insets no longer push the number off centre; theme role `cyan`.
- `checklist.groups` + `cols`: numbered sections ① ② ③ in columns, compact boxes (publication checklist); `tree` third level (`children[].children`: boxes stacked under each child) for keyword universes with 3 to 5 branches.

## [0.6.0] — 2026-09-25

### Added

- **Native Sheets variants** in the catalogue: `chart_bars`, `chart_grouped`, `chart_stacked`, `chart_line`, `chart_combo`, `donut`, `pie` and `table` carry a variant with a `native` block — the Google Sheets MCP recipe (data rows, `manage_chart add` arguments under `style: periscope`, or `read_range` for a table) and the gslide-mcp call (`insert_sheets_chart`, or `insert_component` with the rows read). The component deck shows them embedded linked from a catalogue spreadsheet.

- **Rework an existing deck on the charter** ([docs/rework-deck.md](docs/rework-deck.md)): `harvest_deck_assets` copies a deck's images and slide thumbnails into a Drive folder (an existing one by id, or « <title> · sources » created in the assets folder; idempotent) and returns stable URLs plus `drive:<id>` asset refs, accepted by every image prop and by `draw`, tint included; `suggest_components` splits a source slide into blocks (tables, rows of figures, side-by-side texts, bullets, images, source notes, arrows) and ranks the charter components for each with reasons, the `use` sentence and the variant titles, plus whole-slide alternatives read from the wording.
- `numbered_list`: without icons the number sits in the disc alone (no duplicate « #n » beside it); the « #n » index and its rule appear only when a picto fills the disc.
- `table`: variation columns (« vs N-1 », « Évol. », « Var. », « Δ », or signed values) are coloured by sign and previous-period columns (« N-1 », « P-1 », « précédent ») are muted automatically, from the header; `delta_cols` / `prev_cols` force or disable (`[]`).
- `inspect_slide` returns the placeholder type, the paragraphs (text, level, bullet), the table cells (`rows`) and the images' temporary URLs.
- `list_layouts` returns the page size, each placeholder's geometry and a `content_area` per layout (body placeholders' box, else the band between title and footer) to position components on a new layout.

## [0.5.0] — 2026-09-25

### Added

- Catalogue `variants` (`[{title, when, props}]`, exposed by `list_components`): `when` says which situation the setting fits. Declared in `components/variants.py` for 33 components (table, kpi, kpi_grid, card, card_grid, callout, the charts, donuts, funnel, content_card(s), section_header, button_row, numbered_list, pills, score_matrix, bar_list, people…); a component without an entry derives one variant per value of its `choice` props, so future components are catalogued with their modes automatically. The component deck renders one slide per variant.
- `media_plan.objective_eyebrow`; theme token `mint_pale` (#BFF5E6) and roles `heat_1…heat_4` on the charter palette.

### Changed

- **Charter restyle, light grounds and rounded corners**: `card` / `card_grid` (round rectangle, square only for `plain`), `compare_cards` (✗ grey with coral label, ✓ mint, neutral grey), `before_after` (grey / mint panels, no outline), `process` (rounded steps), `media_plan` (objective panel styled like a `content_card`: mint, tracked eyebrow, title, chevrons), `ad_scoreboard` (grey bold label column), `heatmap` (navy header, heat scale surface → pale mint → mint → navy).

## [0.4.1] — 2026-09-25

### Changed

- **Shrink before wrapping**: category labels, legends, KPI labels, ranked / commented bar labels and score-matrix labels reduce their size (down to 8 or 9 pt, `small_ok`) when they cannot fit, before any wrap, thinning or clip (`fit_text_size`, `fit_labels`).

## [0.4.0] — 2026-09-25

### Added

- **Workshop and restitution components** — `score_matrix` (tiles by threshold), `ranked_bars` (votes), `chip_cloud`, `quadrant_matrix` (impact × urgence), `next_steps`, `board_columns`, `session_plan` (sections + proportional time strip), `attention_points` (level pills, highlighted figures), `bar_list` (commented bars, states, hatching). Light grounds only: transparent or `surface`; colour on headers, tags and tiles.
- `table`: `header_fill` (navy header), `total_fill` (grey total), `subs` (muted second line under the name), `dots` (colour dot per row), `zero_cols` (zeros in coral), `na_text` (muted `–` for empty cells), `pill_cols` (values in rounded tags coloured by threshold). `draw` table ops take `cell_runs`.
- `badge.mono` (code-like tag) and `pill.count` (« ×n »).
- Theme roles `accent_dark`, `coral`, `acid` (and `gray_2` in `default`).

## [0.3.1] — 2026-09-24

### Fixed

- `transform_element`: a single `width_pt` or `height_pt` now scales the element uniformly (the aspect is kept: a linked chart or an image is no longer squashed); both together set the aspect.

## [0.3.0] — 2026-09-24

### Added

- **Bilan média components** — `chart_grouped` (N / N-1 side by side, one tint per régie via `category_colors`), `mini_charts` (small multiples), `donut_row`, `analysis_block` (« Notre analyse : » + chevrons), `source_note`, `stat_box`, `takeaways`, `placeholder`, `ad_scoreboard` (transposed results-per-ad table with thumbnails or dashed « à déposer » frames), `gallery`, `media_plan` (« Rappel du dispositif » with régie logos and objective panel), `timeline_arrow` (milestones on a thick arrow).
- `transform_element` resizes too (`width_pt`, `height_pt`, displayed size in points; the scale changes, never the base size), alone or with a move.
- **Native Sheets charts** — `insert_sheets_chart` (linked or snapshot, `createSheetsChart`), `list_sheets_charts`, `refresh_sheets_charts` (`refreshSheetsChart`); `inspect_slide` reports linked charts as `chart`. The chart is built in the spreadsheet by a Sheets MCP; guide and charter contract in `docs/sheets-charts.md`.
- **Design-system components** (Periscope design system v1.0): `button` / `button_row` (pill CTAs that follow their ground), `hashtags` (plain uppercase tags), `eyebrow` (tracked caps), `content_card` / `content_cards` (editorial cards on white / cyan / dark / yellow with CTA), `section_header` (yellow-highlighted title, eyebrow, hashtags), `client_ticker` (text-only client band), `do_dont` (✓ / ✕ copy pairs); `scripts/make_pixel_icons.py` generates the pixel-art icon set as assets.
- **Charter palette only**: the `periscope` theme drops its orange and dark-mint tokens; negative deltas, warnings and Instagram use coral (ACCENT4 of the Slides theme), GA4 the cyan, positive deltas the mint; mint is the Slides theme value `#00F5B5`.
- **Régie colours** as theme roles (`regie_google`, `regie_bing`, `regie_meta`, `regie_facebook`, `regie_instagram`, `regie_pinterest`, `regie_linkedin`, `regie_tiktok`, `regie_ga4`) in `periscope` and `default`; `Theme.tint(color, amount)` and `Theme.is_dark(color)` helpers; `chart_grid` / `chart_axis` roles.
- `kpi.note` (small muted precision after the label, « Collecte (GA4) »); `kpi_grid.rows` (bold row labels on the left: « Marque » / « Hors marque »).
- `table.icons` (picto column in front), `table.delta_cols` (« vs N-1 » cells coloured by sign), `table.row_heights`.
- `chart_bars.colors` (one colour per bar); `donut.labels` (percentages on the segments) and `donut.legend_pos` (`bottom`); `title` and `panel` props on every chart (centred caption, rounded `surface` panel).
- `draw`: `box.line.dash` (dashed outlines), `table.row_heights` (per-row heights).

### Changed

- **Chart style aligned on the PPTX bilans**: grid 0.5 pt (`chart_grid`), baseline 1 pt (`chart_axis`, no ink axis), lines 1.5 pt, markers 4 pt, legend swatches 8 pt; `chart_combo` puts its legend on top (`legend_pos`) and shows values and markers automatically up to 12 points (`show_values` / `markers` = `auto`); dense category labels are thinned so a 31-day axis stays readable. `chart_line` and `chart_stacked` gain `legend_pos`.
- French number formatting keeps up to two decimals (`1,95`, `3,9`) instead of one.
- **Alignment and fit**: a `kpi_grid` shares one geometry across its KPIs (one value size, one label height, one bar height, one delta line) so rows align KPI to KPI; a KPI value shrinks (down to 16 pt) instead of wrapping; chart values over thin bars shrink or step aside (`small_ok` text ops may go under the charter floor when the block cannot grow); dense category labels get two lines; a short plot draws two ticks instead of four.
- `table`: empty cells get a styled space so Google's 18 pt default paragraph no longer stretches the row; the reported height uses the rendered row height (text line + cell padding); with `icons` the label column takes a double share. Components built around a table (`table` with icons, `ad_scoreboard`) are inserted ungrouped: the Slides API cannot group a table.

## [0.2.0] — 2026-09-15

### Added

- **Layouts** — `list_layouts`, `screenshot_layout` (with `annotate=True` to render the placeholder-key map on a temporary slide), `screenshot_layouts`, `create_slide_from_layout`, `build_from_outline`, `relayout_slide` (speaker notes carried over). Layouts are addressed by id or display name (case/accent-insensitive; ambiguous names fail with the candidates listed). Placeholders are filled from markdown in the same `batchUpdate` as `createSlide`, with no `deleteText` on inherited placeholders. `build_from_outline` resolves every name before writing and creates all slides atomically. Guide: `docs/layouts.md`.
- **Raw readers** — `get_presentation` (field-mask passthrough, trimmed to 200 kB by whole slides) and `get_page` (slide / layout / master / notes with `page_kind`; `compact=True` for one line per element).
- Returned slide `index` values are 1-based everywhere (the ref `screenshot` / `delete_slides` take); `insertion_index` arguments stay 0-based like `create_slide`.
- **Speaker notes** — `get_speaker_notes`, `set_speaker_notes` (atomic rewrite; no `deleteText` on an empty notes shape).
- **Tables** — `create_table` (≤ 20×20, optional data, one batch), `edit_table` (insert/delete rows and columns), `set_table_cell` (markdown into a cell).
- **Local images** — `insert_image_local`: magic-byte sniffing (PNG/JPEG/GIF, ≤ 50 MB), temporary Drive upload shared read-only, deleted in a `finally`; a failed cleanup is reported with the file id and its public/private state.
- **Comments** — `manage_comments` over Drive `comments`/`replies` (list, get, create — unanchored by API limitation —, reply/resolve, delete).
- **Escape hatch** — `raw_request`: GET/POST strictly under `https://slides.googleapis.com/v1/presentations/<id>`; schemes, hosts, `//`, `@`, `..`, whitespace and Drive paths are refused so the OAuth token never leaves the Slides host.
- **Components and themes** — `list_components`, `insert_component`, `draw`, `save_component`, `delete_component`. Themes (`gslides_mcp/themes/*.json`, user themes in `~/.gslides-mcp/themes/`) hold palette, roles, font and named text styles; components (`kpi`, `kpi_grid`, `card`, `callout`, `badge`, `pill`, `steps`, `checklist`, `chevrons`, `arrows`, `quote`, `bigstat`, `stats`, `table`, `heatmap`, `chart_bars`, `chart_line`, `pie`, `donut`, `funnel`, `timeline`, `process`, `hub_spoke`, `stack`, `compare_bars`, `effort_matrix`, `bubbles`, `card_grid`, `agenda`, `numbered_list`, `big_numbers`, `phase_cards`, `compare_cards`, `before_after`, `stat_pair`, `palette`, `person_card`, `team_grid`, `logo_grid`, `logo_wall`, `kpi_cards`, `gauge`, `target`, `chart_stacked`, `tree`, `flowchart`, and the mockups `serp`, `browser`, `laptop`, `phone`) reference roles and styles only and render as native shapes in one grouped `batchUpdate`. Rings and pies are drawn as radial spokes (one per degree). Markdown props accept `==texte==` for the marker highlight (theme role `highlight`); `draw` lines take `end_arrow` / `start_arrow`, rings a `span`, images `contain`. `draw` exposes the primitive ops (box, text runs/markdown, line, polyline, arc, ring, table, image); recipes are JSON components with templated ops saved by the model. Guide: `docs/components.md`.
- **Assets folder** — `GSLIDES_MCP_ASSETS_FOLDER` (bundle field *Assets folder*): a shared Drive folder for pictos, logos and screenshots. `card.icon`, `browser.image`, `laptop.image` and the `asset` key of a `draw` image op take a name in the folder or a local path (uploaded once, shared by link); tinted variants (`bolt__002b3c.png`) are generated from the theme role and cached with the file ids and sizes in `~/.gslides-mcp/assets.json`. `browser` follows the screenshot's aspect; `laptop` crops it to its 16:10 screen (`cover`). `list_components` lists the folder.
- `list_components` entries carry a `use` field — when to pick the component and the close alternatives — next to `description` (what it draws); recipes may set their own `use`.
- **Claude Code skill** `gslides-prez` (`.claude/skills/`): gated workflow from a template deck (layouts chosen up front, plan, emptied clone, visual check, skill retrospective) with `periscope.md` reusable material.
- `list_assets` tool: the names usable as `icon` / `image` / `logo` / `photo` and `asset`.
- **Text size floors** in themes (`text_rules`): Periscope enforces 11 pt for running text and 10 pt for labels, captions, badges, legends and chart values, tables exempt; applied to every text at render time, and the built-in components declare compliant sizes.
- Hidden slides: `list_slides` and `inspect_slide` report `hidden: true` for slides skipped in presentation mode; `set_slide_hidden` toggles the flag.
- Charts: `chart_bars` and `chart_stacked` (vertical) gain a graduated Y axis with grid (`y_axis`) and period dividers (`dividers`, « ISF | IFI »); values are formatted the French way (`4 000 000 €`). New `chart_combo`: bars on the left axis + line with markers on the right axis, values on bars and points.
- **MCP annotations** on every tool (`readOnlyHint`, `destructiveHint`, `idempotentHint`), presets in `app.py`.
- **Test suite** (`tests/`): mocked Slides/Drive services with JSON fixtures, one test file per tool family, and an opt-in live round-trip (`GSLIDES_MCP_INTEGRATION_DECK`).
- **Claude Desktop bundle** (`manifest.json`, `.mcpbignore`, `uv.lock`): `server.type: "uv"`, so Claude Desktop provisions Python and dependencies itself. Settings form for the credentials directory, Apps Script URL, logo.dev token, theme and assets folder.
- `CHANGELOG.md` (this file).

### Changed

- `requires-python` is now `>=3.11` (`gslides-api 0.3.6` already required it; 3.10 never worked).
- Apps Script web app v0.4: `copy` accepts a `requestId` and answers replays from cache (6 h) under a script lock. `cross_deck_ping` reports `"0.4"`.
- Cross-deck HTTP client: replays the POST on the intermittent relay 404 from `script.googleusercontent.com` (up to 3 times, backoff) — always for `ping`, for `copy` only when the deployed script is ≥ 0.4.
- `screenshot_range` compositing extracted into a shared helper reused by `screenshot_layouts` (no behavior change).
- README: tool table regrouped (`Layout` = slide layouts, `Element` = element tools), new sections on layouts, tests and the `.mcpb` install.

### Fixed

- The server failed with `invalid_scope: Bad Request` about an hour after start (first token refresh): `gslides-api` rebuilt the credentials from `token.json` with its own scope list, which adds Sheets, never granted. The services are now built from the server's own credentials, refreshed on the granted scopes only.

- Cross-deck copy and ping failed with `appscript HTTP 302:` — the security-review opener refused the redirect every Apps Script POST answers with. The single hop to `script.googleusercontent.com` is now followed as a token-less GET; any other redirect is still refused, and the error names the destination host.

### Known issues

- `gslides-api` installs its own console script named `gslides-mcp`; whichever package installs last wins. The `.mcpb` bundle sidesteps it with `python -m gslides_mcp.server`; a `pip install -e .` also ends up correct because the project installs last. Renaming the entry point is planned for the next minor.

## [0.1.0] — 2026-06-06

Initial release: deck/slide/shape/content/element/QA tools, cross-deck copy via Apps Script, template library workflow.
