# Components, themes and the `draw` canvas

Google Slides has no design system of its own: no CSS, no component
library, not even a table style. What it has is shapes, lines, text boxes
and tables with explicit properties. This layer turns that into something a
model can use safely:

- **themes** — one JSON file per brand: palette, *roles* (`accent`, `ink`,
  `surface`…), font, *named text styles* (`kpi_value`, `label`…);
- **components** — recipes that draw a KPI, a card, a callout, a table, a
  chart… using only roles and named styles, so a brand change is a theme
  change;
- **`draw`** — the primitive ops every component compiles to, exposed as a
  tool for one-off elements;
- **recipes** — components written as JSON by the model itself and saved
  for reuse.

Everything is one `batchUpdate` per insert, grouped into a single element.

## Tools

| Tool | Does |
|---|---|
| `list_components(theme?)` | Catalogue: every component with `description` (what it draws), `use` (when to pick it and the close alternatives), its props (type, default, choices, required), an example, its source (`builtin` / `recipe`); the available themes; how to add one. |
| `insert_component(presentation, slide, component, props, x_pt, y_pt, width_pt, height_pt?, theme?)` | Renders a component at a position, in one atomic batch, grouped. Returns `group_id` (the element to move/delete), `element_ids`, `height_pt`. |
| `draw(presentation, slide, ops, x_pt, y_pt, theme?, group?)` | Primitive ops on a slide (see below). |
| `save_component(recipe)` | Validates and stores a JSON recipe under `~/.gslides-mcp/components/`; it is listed and insertable right away. |
| `delete_component(name)` | Removes a saved recipe (built-ins can't be deleted). |

The default theme is `periscope`; set `GSLIDES_MCP_THEME` (or the *Theme*
field of the Claude Desktop bundle) to change it.

## Built-in components

Every built-in carries a `use` sentence in the catalogue — the situations
it fits and what tips the choice between neighbours (`stats` vs `kpi_grid`
vs `bigstat`, `process` vs `flowchart` vs `phase_cards`…). The source is
`components/uses.py`; a recipe sets its own `use` key. The tables below
list props; read `list_components()` for the guidance.

| Name | Props | Notes |
|---|---|---|
| `kpi` | `value*`, `label*`, `delta`, `note`, `dark` | Accent bar, big value, label (+ small muted `note`: « Collecte (GA4) »); `delta` colored by its sign (`+` positive, otherwise negative). |
| `kpi_grid` | `items*` `[{value, label, delta, note}]`, `cols`, `rows`, `row_gap`, `dark` | `kpi` repeated in columns; `rows` adds bold row labels on the left (« Marque » / « Hors marque »), one KPI row each. |
| `card` | `variant` (`light` `dark` `mint` `acid` `outline` `plain`), `label`, `big`, `num`, `title`, `body` (markdown), `dot`, `icon`, `icon_color` | The flat card pattern; natural height follows the content. `icon` names a PNG of the assets folder (`bolt`, `people`…) drawn in a white disc, tinted with `icon_color` (default `ink`). |
| `card_grid` | `cards*` (list of `card` props), `cols`, `gap` | Rows of cards with equalised heights — the "three pillars" slide. |
| `callout` | `type` (`info` `idea` `warn` `alert` `dark`), `title`, `body*` (markdown) | Flat box with an accent bar on the left. |
| `badge` | `text*`, `fill`, `color`, `mono` | Small uppercase tag; width follows the text. `mono` = lowercase code-like tag in Roboto Mono, rounded (« signal doux »). |
| `steps` | `items*` (markdown), `dark` | Numbered circles + text. |
| `quote` | `text*` (markdown), `author`, `role`, `dark` | Accent-outlined box, bold italic quote. |
| `table` | `rows*`, `col_w`, `row_h`, `row_heights`, `header`, `total_row`, `align`, `size`, `icons`, `icon_w`, `icon_tint`, `delta_cols`, `header_fill` (`accent` `ink`), `total_fill`, `subs`, `dots`, `zero_cols`, `na_text`, `pill_cols` | Accent or navy header, bold first column (optional muted sub-line via `subs`, colour dot via `dots`), banded rows, thin rules, accent or grey total row. `icons` adds a picto column in front; `delta_cols` colours « vs N-1 » cells by sign; `zero_cols` shows zeros in coral; empty / `-` cells become a muted `–`; `pill_cols` puts a column's values in rounded tags coloured by threshold (`{"7": [{max, color}, …, {color}]}`). |
| `chart_bars` | `labels*`, `values*`, `horizontal`, `unit`, `max`, `show_values`, `color`, `colors`, `y_axis`, `dividers`, `title`, `panel` | Vertical histogram with baseline (optional graduated Y axis with grid, period dividers `[{after, left, right}]`), or horizontal bars on grey tracks. `colors` = one colour per bar (`regie_google`…). Values in French format (`4 000 000 €`). |
| `chart_line` | `labels*`, `series*` `[{name, values, dash, color}]`, `y_max`, `legend`, `legend_pos`, `markers`, `title`, `panel` | Light grid, axis labels, 1.5 pt lines, small markers (`auto`: shown up to 12 points), dashed series, `null` = gap, legend. |
| `donut` | `segments*` `[{label, value, color}]`, `thickness`, `center`, `legend`, `legend_pos` (`right` `bottom` `none`), `labels`, `title`, `panel` | Ring with legend and percentages; `labels` puts the percentages on the segments (from 6 %), text light or dark by luminance. |
| `pie` | `segments*`, `legend` | Full disc (a donut whose thickness is its radius, drawn as two concentric bands). |
| `funnel` | `items*` `[{label, value, sub, color}]`, `pct` (`first` `prev` `both` `none`), `unit`, `label_w`, `value_w`, `bar_h`, `min_frac`, `legend` | Centred bars scaled to the first step, values with French thousands separators, rate pills (accent = vs first step, outlined = vs previous) and their legend. |
| `timeline` | `phases*` `[{date, title, text, color}]` | Horizontal line, one dot per phase, date above, title and text below. |
| `process` | `steps*` `[{label, sub, fill, color, w}]`, `arrow_w` | Boxes separated by → arrows. |
| `hub_spoke` | `center*`, `sats*` `[{label, hl}]`, `hub_w`, `hub_h`, `sat_d` | Accent hub linked to round satellites laid out on an ellipse (`hl` = accent outline). |
| `stack` | `items*` `[{label, sub, fill, color, width}]`, `item_h`, `gap`, `min_ratio` | Centred layers of decreasing width (pyramid / simple funnel). |
| `bigstat` | `value*`, `label*`, `sub`, `color` | One 54 pt figure, centred. |
| `stats` | `items*` `[{value, label, sub}]`, `color` | Row of centred figures, optional caption under each. |
| `pill` | `text*`, `color`, `outline`, `size`, `count` | Capsule, filled or outlined (uppercase), width follows the text; `count` ≥ 2 appends « ×n ». |
| `checklist` | `items*` (text or `{text, done}`), `gap`, `color` | Square boxes; done items are filled with a tick. |
| `chevrons` / `arrows` | `items*`, `size`, `spacing` | One text box, one paragraph per item, › (accent) or → prefix. |
| `compare_bars` | `bars*` `[{label, frac, color}]`, `gap` | Full-width grey tracks with a filled fraction. |
| `effort_matrix` | `bubbles*` `[{n, label, x, y, d, fill, color, above}]`, `x_label`, `y_label` | Two axes, numbered bubbles at fractional positions (y = 1 is top). |
| `bubbles` | `points*` `[{name, x, y, size, color}]`, `x_max`, `y_max`, `x_title` | Bubble chart on a 4×4 grid with axis ticks. |
| `heatmap` | `rows*` (header row, label column, numbers or `null`), `col_w`, `row_h`, `size` | Table whose numeric cells are binned into `heat_1…heat_4`. |

Mockups (tag `mockups`):

| Name | Props | Notes |
|---|---|---|
| `serp` | `title*`, `site`, `url`, `desc`, `rating`, `reviews`, `frame` | A Google result: favicon disc with the initial, site and URL, blue title, 0–5 stars (partial star masked), review count, description. Uses Google's own colours on purpose, not the theme. |
| `browser` | `url`, `image`, `image_aspect`, `screen`, `screen_text` | Flat browser chrome (three theme-coloured dots, URL field) around a screenshot from the assets folder; the frame takes the screenshot's aspect. Without `image`: a coloured screen with centred text. |
| `laptop` | `image`, `image_aspect`, `screen`, `screen_text` | Dark rounded screen on a base. The screenshot is cropped to the 16:10 screen like `object-fit: cover`. |
| `phone` | `image`, `image_aspect`, `screen`, `screen_text`, `notch` | Smartphone frame (9:19.5 screen by default), screenshot cropped to the screen. |

Text and structure (lot 4):

| Name | Props | Notes |
|---|---|---|
| `agenda` | `items*` (text or `{num, title}`), `dark`, `size`, `row_h` | Table of contents: acid chip with the number, section title. `dark=True` on a dark layout. |
| `numbered_list` | `items*` `[{title, sub, icon}]`, `marker` (`circle` `square`), `start`, `card`, `connector`, `gap` | Vertical list: accent disc (picto or number) + `#n` + title/sub, or square chip + uppercase title. Optional light cards and a vertical accent connector. |
| `big_numbers` | `items*` `[{num, title, text}]`, `cols`, `row_gap`, `highlight` | "1 2 3" columns: 54 pt figure, highlighted bold title (line breaks allowed), centred paragraph. |
| `phase_cards` | `phases*` `[{num, title, text, icon, note, deliverables}]`, `cols`, `gap`, `num_size` | Methodology cards: big accent number above an accent-outlined card, picto + note row, "LIVRABLES" list with → bullets. Heights equalised per row. |
| `compare_cards` | `cards*` `[{kind (bad/good/neutral), label, title, text}]`, `cols`, `gap` | Myth vs. answer: ✗ card on `danger_bg`, ✓ card on `surface_dark` with accent label, neutral on `surface`. |
| `before_after` | `before*` / `after*` `{title, items, note}`, `arrow`, `gap` | Two rounded panels (`danger_bg` / `success_bg`) with a caps title, rule-separated lines, italic note, → between them. |
| `stat_pair` | `pairs*` `[{label, before, after}]`, `cols` | Before → after figures: muted before, bold after. |
| `palette` | `swatches*` `[{color, text, name, ratio, sample}]`, `cols`, `sample` | "Aa" swatches with name and contrast ratio (RGAA slides, brand palettes). |

People, logos, KPI cards (assets folder):

| Name | Props | Notes |
|---|---|---|
| `person_card` | `photo`, `name*`, `role`, `bio` (markdown), `contact`, `photo_size`, `layout` (`side` `top`) | Square photo (cover) or initials on `photo_bg`, name, role, bio, contact. |
| `team_grid` | `people*` (person props), `cols`, `gap`, `photo_size`, `layout` | `person_card` in a grid with equalised rows. |
| `logo_grid` | `items*` `[{logo, logo_url, name, title, text}]`, `cols`, `gap`, `dividers`, `highlight`, `tint` | Tools / partners: logo (contain) + name, highlighted title, text, dashed dividers. `tint` recolours white pictos. |
| `logo_wall` | `logos*` (asset names or `{logo, logo_url, name}`), `cols`, `gap`, `logo_h`, `cell_h`, `names`, `dark`, `tint` | Client logo wall, each logo fitted in its cell at its own aspect. |
| `kpi_cards` | `items*` `[{label, value, delta, icon, color}]`, `cols`, `gap`, `card_h`, `icon_tint` | Outlined cards: picto + label, ▲/▼ delta coloured by sign, series dot + value. |

Charts and diagrams (lot 4):

| Name | Props | Notes |
|---|---|---|
| `gauge` | `value*`, `max`, `label`, `text`, `unit`, `color`, `size`, `thickness`, `value_size` | Half ring on a grey track, value in the middle, label below. |
| `target` | `rings*` `[{label, value, color}]`, `max`, `thickness`, `gap`, `center`, `legend` | Concentric rings, each filled to its percentage from 12 o'clock (radial bar chart), legend. |
| `chart_stacked` | `labels*`, `series*` `[{name, values, color}]`, `horizontal`, `max`, `unit`, `show_values`, `legend`, `legend_pos`, `bar_h`, `gap`, `y_axis`, `dividers`, `title`, `panel` | Stacked bars, horizontal (default) or vertical columns with graduated Y axis and period dividers (« ISF | IFI »), totals, legend. |
| `chart_combo` | `labels*`, `bars*` `{name, values, color}`, `line*` `{name, values, color}`, `unit`, `unit2`, `y_max`, `y2_max`, `y_axis`, `show_values` (`auto`), `markers` (`auto`), `legend`, `legend_pos` (`top`), `dividers`, `title`, `panel` | Bars on the left axis + thin line on the right axis, two graduated axes, legend on top. Values and markers are shown automatically up to 12 points (a daily series stays clean); dense category labels are thinned (first and last always shown). |
| `tree` | `root*`, `children*` `[{label, items, fill, hl}]`, `node_h`, `gap_y`, `gap_x` | Two-level sitemap / org chart: accent root, children on a bus, bulleted sub-items under each. |
| `flowchart` | `nodes*` `[{id, label, sub, col, row, fill, color, shape, hl, w}]`, `edges` (`[from, to]` or `{from, to, label, dash, color}`), `cols`, `node_w`, `node_h`, `gap_x`, `gap_y` | Nodes on a grid, elbow connectors with arrowheads (forward, vertical, and backward through a lane under the grid), edge labels. |

Bilan média (reporting régies + GA4; reference: the agency's generated PPTX bilans):

| Name | Props | Notes |
|---|---|---|
| `chart_grouped` | `labels*`, `series*` `[{name, values, color}]`, `category_colors`, `horizontal`, `unit`, `max`, `y_axis`, `show_values` (`auto`), `legend_pos` (`top`), `bar_h`, `title`, `panel` | Bars side by side per category. With `category_colors` (one per category, e.g. `regie_google`) series k is a lighter tint of its category colour: « foncé = N, clair = N-1 ». |
| `mini_charts` | `labels*`, `charts*` `[{title, values, unit, max}]`, `colors`, `cols`, `gap`, `y_axis`, `show_values`, `legend`, `panel` | Small multiples: one mini histogram per indicator (impressions, clics, collecte, ROAS, dépenses), same categories and colours everywhere, one shared legend on top (`legend=false` puts the category labels under each chart). |
| `donut_row` | `items*` `[{title, segments}]`, `colors`, `cols`, `gap`, `labels`, `legend_pos` (`bottom`), `thickness`, `panel` | `donut` repeated with a title each, percentages on the segments, legend below. |
| `analysis_block` | `title` (« Notre analyse : »), `items` or `text` (markdown), `box`, `size` | Bold title then chevron › points (the `chevrons` component) or a paragraph; `box` = accent outline. |
| `source_note` | `text*`, `platform`, `logo`, `align` (`END`), `tint` | « * Sources : … » in small italic (prefix added when missing), platform logo + name underneath. |
| `stat_box` | `boxes*` `[{value, label}]`, `operator` (`=`), `box_w`, `box_h` | Accent-outlined figures joined by an operator, centred as a group. |
| `takeaways` | `items*` (`{title, text}` or text), `highlight`, `gap` | Enseignements / recos: bold (optionally highlighted) title + paragraph per point. |
| `placeholder` | `text*`, `height`, `dash` | Dashed grey frame with a centred message (export pending, capture to drop). |
| `ad_scoreboard` | `ads*` `[{name, image, image_url, values}]`, `metrics*`, `image_h`, `row_h`, `first_col_w`, `name_label`, `image_label`, `top_note`, `size` | Transposed results-per-ad table: dark header with the ad names, « Visuel » row with the thumbnails (contain) or dashed frames, one row per metric, accent first column, italic « Top annonce » note. |
| `gallery` | `images*` (asset, `{asset | url, caption}`, or `null`), `cols`, `gap`, `ratio` (0.62), `captions`, `placeholder_text` | Fixed-ratio image cells with optional captions; `null` draws a dashed « Capture de l'annonce (à déposer) » frame. |
| `media_plan` | `levers*` `[{name, logos, budget, dates}]`, `objective` `{title, items}`, `heading`, `budget_label`, `dates_label`, `split`, `tint` | « Rappel du dispositif »: accent dot, uppercase lever name, régie logos, bold budget and dates; accent « Objectif à atteindre » panel with chevrons on the right. |
| `timeline_arrow` | `events*` `[{date, text, style (filled | outline | dashed), above}]`, `box_w`, `box_h`, `connector`, `alternate` | Thick accent arrow, dated boxes alternating below / above joined by a thin connector. |

Design system (brand, from the Periscope design system v1.0):

| Name | Props | Notes |
|---|---|---|
| `button` | `text*`, `ground` (`white` `dark` `cyan` `yellow`), `variant` (`filled` `outline`), `color`, `size` | Pill button that follows its ground: filled dark on white, outlined white (or `color: accent`) on dark, filled dark on cyan / yellow. |
| `button_row` | `items*` (text or `{text, variant, ground, color}`), `ground`, `variant`, `gap`, `align`, `size` | Primary + secondary CTAs side by side. |
| `hashtags` | `items*`, `dark`, `color`, `size`, `align` | Plain uppercase hashtags, no chip, no fill; accent on a dark ground. |
| `eyebrow` | `text*`, `tracking`, `dark`, `color`, `size`, `align` | Tracked uppercase label (thin spaces between letters: Slides has no letter spacing). |
| `content_card` | `ground`, `eyebrow`, `title*` (markdown), `text` (markdown), `tags`, `cta`, `cta_variant` | Editorial card on one of the grounds: tracked eyebrow, title, text, inline hashtags, pill CTA following the ground. |
| `content_cards` | `cards*` (content_card props), `cols`, `gap` | Row of content cards, heights equalised, CTAs pinned to the bottom. |
| `section_header` | `title*` (markdown, `==…==` highlighted), `eyebrow`, `text`, `tags`, `highlight` (`highlight_alt`), `size`, `dark`, `align` | The signature section opener: eyebrow, yellow-highlighted title, paragraph, hashtags. |
| `client_ticker` | `names*`, `dark`, `separator`, `size`, `pad` | Text-only client band, bold names separated by accent dots on a dark band. |
| `do_dont` | `pairs*` `[{do, dont, do_note, dont_note}]`, `do_label`, `dont_label`, `gap` | ✓ / ✕ pairs of quoted copy with a note, on `success_bg` / `danger_bg`. |

Workshop and restitution blocks (light grounds: transparent or `surface` panels; only headers, tags and tiles carry colour):

| Name | Props | Notes |
|---|---|---|
| `score_matrix` | `rows*` `[{label, sub, values, counts}]`, `columns*`, `thresholds`, `row_title`, `count_label`, `label_ratio`, `tile_h`, `legend` | Families × criteria: rounded tiles coloured by threshold (coral, acid, pale mint, mint by default), big score, « n rép. », threshold legend. |
| `ranked_bars` | `items*` `[{label, value}]`, `top`, `max`, `eyebrow`, `label_ratio`, `bar_h` | Votes / priorities: grey track, accent fill and bold label for the top n, grey fill below, big count on the right. |
| `chip_cloud` | `items*` (text or `{text, count}`), `fill`, `size`, `gap` | Wrapping row of rounded chips with a « ×n » counter. |
| `quadrant_matrix` | `quadrants*` (4 × `{title, sub, items, highlight}`), `x_label`, `y_label`, `eyebrow`, `height` | 2 × 2 grid of titled panels, one highlighted in accent, chevron items, axis labels. |
| `next_steps` | `steps*` `[{title, text, current}]` | Columns with a top rule (accent = current), bold title, text. |
| `board_columns` | `columns*` `[{title, items}]`, `empty_text` | Workshop board: eyebrow per column, numbered cards, italic empty state, equalised column height. |
| `session_plan` | `sections` `[{title, text}]`, `slots` `[{time, label, weight, current}]`, `slot_h` | Section headers with an accent rule, then a proportional time strip (current slot in accent). |
| `attention_points` | `items*` `[{level (critical | warning | good), tag, text}]`, `title`, `note`, `tag_w` | Cards with a level pill on the left (coral with outline, acid, mint) and markdown text with `==highlighted==` figures. |
| `bar_list` | `items*` `[{label, sub, value, value_text, sub_right, state, color, pattern}]`, `states`, `max`, `unit`, `title`, `note`, `value_in_bar`, `label_ratio`, `value_ratio`, `bar_h` | Commented horizontal bars: label + sub on the left, value + sub on the right (or value inside the bar), colour by state, `pattern: stripes` hatching, state legend and scale note. |

Pixel icons: `scripts/make_pixel_icons.py` writes the design-system pixel-art set
(`assets/pixel-icons/px-envelope.png`, `px-heart`, `px-chat`, `px-chart`,
`px-arrow-out`, `px-play`, `px-leaf`, `px-cursor`, `px-spark`, `px-chevron`,
`px-submarine`) as white-on-transparent PNGs; once uploaded to the assets folder
they work like any picto (`card.icon`, `logo_wall`, `draw` image ops, tinted by the
theme). Keep them decorative and between 48 and 120 pt, as the design system says.

Section rhythm (design-system rule, for `build_from_outline` plans): alternate light,
accent, light, dark — never two coloured slides in a row; cyan and yellow never share
a slide.

Chart style (all charts): grid 0.5 pt in `chart_grid`, baseline 1 pt in
`chart_axis`, lines 1.5 pt, markers 4 pt, legend swatches 8 pt. `title`
draws a centred caption above; `panel` wraps the chart in a rounded
`surface` box (the "chart card" of the PPTX bilans). Régie colours are theme
roles: `regie_google`, `regie_bing`, `regie_meta` / `regie_facebook`,
`regie_instagram`, `regie_pinterest`, `regie_linkedin`, `regie_tiktok`,
`regie_ga4` — pass them as `color`, `colors` or `category_colors`.

`*` = required. Series and segments default to the theme's `series_1…6`
roles.

Example — a KPI row then a comparison card, on slide 5 of a deck:

```
insert_component(deck, 5, "kpi_grid", {"items": [
    {"value": "1 625 394", "label": "Impressions", "delta": "-66,57 %"},
    {"value": "12 400", "label": "Sessions", "delta": "+8 %"},
    {"value": "3,2 %", "label": "CTR"}], "cols": 3},
    x_pt=40, y_pt=90, width_pt=640)

insert_component(deck, 5, "card", {"variant": "dark", "num": "01", "title": "Visibilité",
    "body": "- Autorité de domaine\n- **Contenu** evergreen", "dot": True},
    x_pt=40, y_pt=190, width_pt=200)
```

Then `screenshot(deck, 5)` to check the result. Components return their
natural height so the next one can be placed right below.

**Marker highlight.** Every markdown prop accepts `==texte==`: the span gets
the theme's `highlight` role as text background — the marker effect the
Periscope decks use on key phrases. `runs` take a `highlight` key with any
colour, and a text op's `highlight` key changes the colour used by `==…==`
in that box.

## Assets (pictos, logos, screenshots)

`createImage` only accepts URLs, so every picture a component uses lives in
one shared Drive folder: `GSLIDES_MCP_ASSETS_FOLDER` (the *Assets folder*
field of the Claude Desktop bundle; id or URL). Any `image` prop (`icon`,
`image`) and the `asset` key of a `draw` image op take either:

- a **name** — `bolt` finds `bolt.png` in the folder;
- a **local path** — the file is uploaded into the folder the first time
  (shared read-only by link, which Slides needs to fetch it), then reused.

Tinted variants are generated on demand: a card's `icon_color: "accent"`
recolours the picto (alpha kept) and stores `bolt__00f5b4.png` next to the
original, so one white/black picto serves every theme. Resolved ids and
image sizes are cached in `~/.gslides-mcp/assets.json`. `list_assets()` returns the usable names (without extension, tinted
variants hidden); `list_components` also carries the raw file list under
`assets` (or `assets_error` when the folder is not configured).

Shipped pictos in the Periscope folder: `bolt`, `download`, `google`,
`lightbulb`, `megaphone`, `people`, `search`, `share`, `star`, `video`;
demo screenshots `screen-demo` (16:9) and `laptop-demo`. The pictos are
white on transparent: `card.icon` tints them with `icon_color`, and
`logo_grid` / `logo_wall` need `tint: "ink"` to show them on a light
background (real logos are coloured and need no tint).

## Text size floors

A theme may carry `text_rules`: `min_size` for running text, `small_min_size`
for labels, captions, badges, legends and chart values (`small_styles`), and
`exempt_styles` (tables). Periscope: 11 pt / 10 pt, `table_cell` and
`table_header` exempt. The floor applies at render time to every text —
named style, explicit `size`, runs — so `draw` ops and recipes comply too;
the built-in components also declare compliant sizes so their computed
box heights are right.


A text op may carry `small_ok: true`: the size it asks for is kept even under the floor. Components use it only where the block cannot grow (a KPI value in a narrow column shrinks to 16 pt instead of wrapping; a value over a thin bar drops to 9 or 8.5 pt); it is the charter's escape hatch, not a default.

## Themes

`periscope.json` (the Slidev theme tokens) and `default.json` (neutral)
ship with the server; drop `~/.gslides-mcp/themes/<name>.json` to add one,
optionally extending another:

```json
{"extends": "periscope",
 "colors": {"acme_red": "#AA0000"},
 "roles": {"accent": "acme_red"},
 "text_styles": {"label": {"size": 12}}}
```

A theme has four parts:

- `colors` — the palette, token → hex;
- `roles` — what the palette is *for*: `background`, `ink`, `text`,
  `muted`, `accent`, `accent_alt`, `on_accent`, `on_dark`, `surface`,
  `surface_dark`, `rule`, `grid`, `positive`, `negative`, `series_1…6`,
  plus per-component roles (`callout_info_bg`, `step_bg`…);
- `font` — one family for everything (must exist in Google Fonts or the
  deck: Barlow does);
- `text_styles` — named `{size, bold, italic, color}` sets: `title`,
  `body`, `label`, `caption`, `kpi_value`, `card_big`, `table_header`…

Components reference roles and style names only. To recolor every KPI bar,
change `roles.accent`; to shrink every table, change `text_styles.table_cell`.

## `draw` ops

Coordinates in points, relative to the tool's `x_pt`/`y_pt`; colors are
roles, tokens or `#RRGGBB`; `style` names a theme text style.

```
box       x y w h [fill] [line {color, weight}] [shape]  (+ any text key below)
text      x y w h  text | markdown | runs=[[{text, bold, italic, color, size, font, highlight}], …]
          [style] [size] [color] [bold] [italic] [align] [valign] [spacing] [highlight]
          (markdown ==x== → text background in the highlight role)
line      x1 y1 x2 y2 [color] [weight] [dash] [end_arrow] [start_arrow]
          (arrow | open | dot | stealth | none)
polyline  points=[[x, y], …] [color] [weight] [dash] [end_arrow]   arrow on the last segment
arc       cx cy r a0 a1 weight [color]           degrees, 0 = east, clockwise
ring      cx cy r thickness segments=[{value, color}] [start] [span]   span < 360 = gauge
table     x y w rows [col_w] [row_h] [header {fill, color, bold}] [banding]
          [first_col_bold] [align] [borders {color, weight, position} | null]
          [row_fills] [bold_rows] [size]
image     x y w h  drive_file_id | url | asset [tint] [cover] [contain]
```

`asset` is a name in the Drive assets folder or a local path (see
*Assets*); `tint` a role or `#RRGGBB`; `cover: true` crops the source to the
box without distortion (`object-fit: cover`); `contain: true` shrinks and
centres the box to the source's aspect (logos). Both need the source size,
which the resolver knows for assets, not for bare URLs.

`shape` is any Slides predefined type (`RECTANGLE`, `ROUND_RECTANGLE`,
`ELLIPSE`, `STAR_5`, `CHEVRON`, `TRAPEZOID`…).

## Recipes

A recipe is a component with no code — the same ops, templated:

```json
{"name": "pill_row",
 "description": "Rangée de pastilles.",
 "props": {"items": {"type": "list", "description": "Textes.", "required": true},
           "fill":  {"type": "color", "description": "Fond.", "default": "accent"}},
 "height": "16",
 "ops": [
   {"each": "items", "ops": [
     {"op": "box", "x": "i * 70", "y": 0, "w": 64, "h": 16, "fill": "{fill}",
      "text": "{item}", "style": "badge", "align": "CENTER", "valign": "MIDDLE"}]},
   {"op": "text", "x": 0, "y": 20, "w": "w", "h": 12, "text": "{len(items)} pastilles", "style": "caption"}]}
```

- numeric keys (`x`, `y`, `w`, `h`, `x1`…, `r`, `weight`, `size`…) are
  expressions: arithmetic over the props plus `w`, `h` and, inside an `each`
  block, `i`, `n` and the item; `min/max/round/abs/len` only;
- string keys are templates: `{item}`, `{row.name}`, `{len(items)} pastilles`;
- `each` unrolls a list prop; `as` renames the item (`{row.name}`).

`save_component` dry-renders the recipe with sample props and reports the
failing op by index. The intended loop for the model: sketch with `draw`,
screenshot, adjust, then freeze as a recipe.

## What the Slides API imposes

- **No freeform geometry.** Curves are straight `createLine` segments;
  rings and pies are radial spokes, one per degree (a donut or a pie is 360
  lines grouped into one element — count on 3–8 s per chart). Partial
  fills (the SERP's 4.6 stars) are a full shape masked by a white box.
- **Fixed text insets** (~7 pt left/right, ~4 pt top/bottom) that can't be
  changed. Components budget for them; when you `draw` text yourself, add
  8 pt to box heights and expect text to start 7 pt in.
- **No adjust handles** on predefined shapes: a `ROUND_RECTANGLE`'s radius
  or a `TRAPEZOID`'s slant are what Google gives.
- **Line caps are square**, so a very thick arc shows faint oblique seams
  where segments meet.
- **Fonts** are set by name; Barlow renders because Google Fonts has it. A
  font the deck can't resolve silently falls back to Arial.
- **Images are URLs.** No upload in the Slides API: pictos and screenshots
  go through the Drive assets folder, and an image's crop can only be set
  with all four offsets at once.
- **Write quota**: 60 requests per minute per user. Every write here is one
  `batchUpdate`, retried with backoff on 429; building a whole catalogue in
  one go still needs a pause between inserts.
